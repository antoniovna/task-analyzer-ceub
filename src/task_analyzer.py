"""Módulo TaskAnalyzer: métricas de produtividade a partir de um conjunto de tarefas.

Implementa o contrato de ``specs/task_analyzer_spec.md`` (v1.0). O módulo é puramente analítico
e sem estado: valida as tarefas recebidas, calcula as métricas e devolve um relatório imutável.
A única função pública é ``analisar_tarefas``; as auxiliares de validação e cálculo são privadas.
"""

import logging
import math
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Final, NoReturn

_logger: Final = logging.getLogger(__name__)

_PRIORIDADES: Final = ("baixa", "media", "alta")
_STATUS_VALIDOS: Final = ("concluida", "pendente", "cancelada")
_STATUS_CONCLUIDA: Final = "concluida"
_STATUS_PENDENTE: Final = "pendente"
_TAMANHO_MAXIMO_TITULO: Final = 200
_CASAS_DECIMAIS: Final = 2
_SEGUNDOS_POR_MINUTO: Final = 60.0
_PERCENTUAL: Final = 100.0
_CAMPOS_OBRIGATORIOS: Final[dict[str, type]] = {
    "titulo": str,
    "prioridade": str,
    "status": str,
    "data_criacao": datetime,
    "prazo": datetime,
}
_DATAS_OPCIONAIS: Final = ("data_inicio", "data_conclusao")


class TaskAnalyzerError(Exception):
    """Base de todas as exceções do módulo TaskAnalyzer."""


class ListaDeTarefasVaziaError(TaskAnalyzerError):
    """A lista recebida não contém nenhuma tarefa."""


class ContratoDeEntradaError(TaskAnalyzerError):
    """Campo obrigatório ausente, com tipo incorreto ou fora das restrições de formato."""


class ValorDeDominioInvalidoError(TaskAnalyzerError):
    """Prioridade ou status fora do domínio permitido."""


class DataInconsistenteError(TaskAnalyzerError):
    """Violação das regras de consistência temporal (RN-07) ou de status e datas (RN-08)."""


class IdentificadorDuplicadoError(TaskAnalyzerError):
    """Dois ou mais registros com o mesmo ``id_tarefa`` no conjunto (RN-09)."""


class SemTarefasConcluidasError(TaskAnalyzerError):
    """Nenhuma tarefa do conjunto está concluída; as métricas gerais são indefinidas (RN-06)."""


@dataclass(frozen=True, kw_only=True)
class Tarefa:
    """Tarefa registrada por um sistema externo (spec, seção 1.3.2).

    Attributes:
        id_tarefa: Identificador único e positivo.
        titulo: Texto não vazio de até 200 caracteres; não participa dos cálculos.
        prioridade: ``"baixa"``, ``"media"`` ou ``"alta"``.
        status: ``"concluida"``, ``"pendente"`` ou ``"cancelada"``.
        data_criacao: Momento de criação; referência inicial da duração.
        data_inicio: Início da execução, opcional; não é usado nos cálculos desta versão.
        prazo: Prazo acordado; deve ser posterior a ``data_criacao``.
        data_conclusao: Obrigatória se ``status == "concluida"``; ``None`` nos demais status.
    """

    id_tarefa: int
    titulo: str
    prioridade: str
    status: str
    data_criacao: datetime
    data_inicio: datetime | None = None
    prazo: datetime
    data_conclusao: datetime | None


@dataclass(frozen=True, kw_only=True)
class IndicadorPrioridade:
    """Métricas de uma prioridade (spec, seção 1.3.3).

    Attributes:
        total_tarefas: Tarefas da prioridade, em qualquer status.
        total_concluidas: Tarefas concluídas da prioridade.
        tempo_medio_conclusao_min: Média de duração em minutos; ``None`` sem concluídas.
        taxa_atraso_percentual: Percentual de concluídas após o prazo; ``None`` sem concluídas.
    """

    total_tarefas: int
    total_concluidas: int
    tempo_medio_conclusao_min: float | None
    taxa_atraso_percentual: float | None


@dataclass(frozen=True, kw_only=True)
class RelatorioProdutividade:
    """Relatório consolidado devolvido por ``analisar_tarefas`` (spec, seção 1.3.3).

    Attributes:
        total_tarefas: Quantidade total de tarefas recebidas.
        total_concluidas: Tarefas com status ``"concluida"``.
        total_em_aberto: Tarefas com status ``"pendente"``; canceladas não entram.
        tempo_medio_conclusao_min: Média de duração das concluídas, em minutos.
        taxa_atraso_percentual: Percentual de concluídas após o prazo.
        indicadores_por_prioridade: Chaves fixas ``"baixa"``, ``"media"`` e ``"alta"``.
    """

    total_tarefas: int
    total_concluidas: int
    total_em_aberto: int
    tempo_medio_conclusao_min: float
    taxa_atraso_percentual: float
    indicadores_por_prioridade: dict[str, IndicadorPrioridade]


def _falhar(erro: TaskAnalyzerError) -> NoReturn:
    """Registra o erro em log e o levanta (RN-10).

    Args:
        erro: Exceção do módulo, já com a mensagem final.

    Raises:
        TaskAnalyzerError: Sempre; a própria exceção recebida.
    """
    _logger.error("analise_interrompida | erro=%s | mensagem=%s", type(erro).__name__, erro)
    raise erro


def _para_utc(data: datetime) -> datetime:
    """Devolve uma cópia da data em UTC; datas sem fuso são consideradas UTC (RN-04).

    Args:
        data: Data com ou sem informação de fuso.

    Returns:
        Data equivalente com ``tzinfo`` UTC.
    """
    if data.utcoffset() is None:
        return data.replace(tzinfo=timezone.utc)
    return data.astimezone(timezone.utc)


def _formatar_data(data: datetime) -> str:
    """Formata a data em UTC para mensagens de erro, no padrão ``2026-03-01T08:00Z``.

    Args:
        data: Data com ou sem informação de fuso.

    Returns:
        Texto ISO 8601 resumido, em UTC.
    """
    return _para_utc(data).strftime("%Y-%m-%dT%H:%MZ")


def _validar_conjunto(tarefas: Sequence[Tarefa]) -> None:
    """Valida o conjunto inteiro antes de qualquer cálculo.

    Args:
        tarefas: Tarefas recebidas por ``analisar_tarefas``.

    Raises:
        ListaDeTarefasVaziaError: Se a lista estiver vazia.
        TaskAnalyzerError: Subclasse correspondente à primeira violação encontrada.
    """
    if not tarefas:
        _falhar(ListaDeTarefasVaziaError("A lista de tarefas está vazia; não há o que analisar."))
    for tarefa in tarefas:
        _validar_tarefa(tarefa)
    _validar_unicidade(tarefas)


def _validar_tarefa(tarefa: Tarefa) -> None:
    """Aplica à tarefa as verificações de tipo, formato, domínio e datas, nessa ordem.

    Args:
        tarefa: Tarefa a validar.

    Raises:
        TaskAnalyzerError: Subclasse correspondente à primeira violação encontrada.
    """
    _validar_tipos(tarefa)
    _validar_formato(tarefa)
    _validar_dominio(tarefa)
    _validar_status_e_conclusao(tarefa)
    _validar_cronologia(tarefa)


def _validar_tipos(tarefa: Tarefa) -> None:
    """Verifica presença e tipo de cada campo (spec, seção 1.3.2).

    Args:
        tarefa: Tarefa a validar.

    Raises:
        ContratoDeEntradaError: Se um campo obrigatório estiver ausente ou com tipo incorreto.
    """
    id_tarefa = tarefa.id_tarefa
    if isinstance(id_tarefa, bool) or not isinstance(id_tarefa, int):
        _falhar(
            ContratoDeEntradaError(
                f"id_tarefa deve ser int; recebido {type(id_tarefa).__name__} ({id_tarefa!r})."
            )
        )
    for campo, tipo in _CAMPOS_OBRIGATORIOS.items():
        valor = getattr(tarefa, campo)
        if valor is None:
            _falhar(
                ContratoDeEntradaError(f"Tarefa {id_tarefa}: campo obrigatório {campo} ausente.")
            )
        if not isinstance(valor, tipo):
            _falhar(
                ContratoDeEntradaError(
                    f"Tarefa {id_tarefa}: {campo} deve ser {tipo.__name__}; "
                    f"recebido {type(valor).__name__}."
                )
            )
    for campo in _DATAS_OPCIONAIS:
        valor = getattr(tarefa, campo)
        if valor is not None and not isinstance(valor, datetime):
            _falhar(
                ContratoDeEntradaError(
                    f"Tarefa {id_tarefa}: {campo} deve ser datetime ou None; "
                    f"recebido {type(valor).__name__}."
                )
            )


def _validar_formato(tarefa: Tarefa) -> None:
    """Verifica as restrições de formato de ``id_tarefa`` e ``titulo`` (spec, seção 1.3.2).

    Args:
        tarefa: Tarefa com tipos já validados.

    Raises:
        ContratoDeEntradaError: Se o id não for positivo ou o título for vazio ou longo demais.
    """
    if tarefa.id_tarefa <= 0:
        _falhar(
            ContratoDeEntradaError(
                f"Tarefa {tarefa.id_tarefa}: id_tarefa deve ser positivo (> 0)."
            )
        )
    if not tarefa.titulo.strip():
        _falhar(
            ContratoDeEntradaError(
                f"Tarefa {tarefa.id_tarefa}: titulo vazio após remoção de espaços."
            )
        )
    if len(tarefa.titulo) > _TAMANHO_MAXIMO_TITULO:
        _falhar(
            ContratoDeEntradaError(
                f"Tarefa {tarefa.id_tarefa}: titulo com {len(tarefa.titulo)} caracteres "
                f"excede o máximo de {_TAMANHO_MAXIMO_TITULO}."
            )
        )


def _validar_dominio(tarefa: Tarefa) -> None:
    """Verifica se prioridade e status pertencem aos domínios fechados (spec, seção 1.3.2).

    Args:
        tarefa: Tarefa com tipos já validados.

    Raises:
        ValorDeDominioInvalidoError: Se prioridade ou status estiverem fora do domínio.
    """
    for campo, dominio in (("prioridade", _PRIORIDADES), ("status", _STATUS_VALIDOS)):
        valor = getattr(tarefa, campo)
        if valor not in dominio:
            _falhar(
                ValorDeDominioInvalidoError(
                    f"Tarefa {tarefa.id_tarefa}: {campo} '{valor}' fora do domínio "
                    f"permitido ({', '.join(dominio)})."
                )
            )


def _validar_status_e_conclusao(tarefa: Tarefa) -> None:
    """Verifica a coerência entre status e ``data_conclusao`` (RN-08).

    Args:
        tarefa: Tarefa com domínio já validado.

    Raises:
        DataInconsistenteError: Se o status e a presença de ``data_conclusao`` divergirem.
    """
    concluida = tarefa.status == _STATUS_CONCLUIDA
    if concluida and tarefa.data_conclusao is None:
        _falhar(
            DataInconsistenteError(
                f"Tarefa {tarefa.id_tarefa}: status '{tarefa.status}' exige "
                "data_conclusao preenchida (RN-08)."
            )
        )
    if not concluida and tarefa.data_conclusao is not None:
        _falhar(
            DataInconsistenteError(
                f"Tarefa {tarefa.id_tarefa}: status '{tarefa.status}' exige "
                "data_conclusao nula (RN-08)."
            )
        )


def _validar_cronologia(tarefa: Tarefa) -> None:
    """Verifica a ordem temporal das datas, comparadas em UTC (RN-04 e RN-07).

    Args:
        tarefa: Tarefa com tipos já validados.

    Raises:
        DataInconsistenteError: Se o prazo não for posterior à criação, ou se
            ``data_inicio`` ou ``data_conclusao`` forem anteriores à criação.
    """
    criacao = _para_utc(tarefa.data_criacao)
    if _para_utc(tarefa.prazo) <= criacao:
        _falhar(
            DataInconsistenteError(
                f"Tarefa {tarefa.id_tarefa}: prazo ({_formatar_data(tarefa.prazo)}) deve ser "
                f"posterior à data_criacao ({_formatar_data(criacao)}) (RN-07)."
            )
        )
    for campo in _DATAS_OPCIONAIS:
        data = getattr(tarefa, campo)
        if data is not None and _para_utc(data) < criacao:
            _falhar(
                DataInconsistenteError(
                    f"Tarefa {tarefa.id_tarefa}: {campo} ({_formatar_data(data)}) anterior à "
                    f"data_criacao ({_formatar_data(criacao)}) (RN-07)."
                )
            )


def _validar_unicidade(tarefas: Sequence[Tarefa]) -> None:
    """Verifica se não há ``id_tarefa`` repetido no conjunto (RN-09).

    Args:
        tarefas: Tarefas já validadas individualmente.

    Raises:
        IdentificadorDuplicadoError: No primeiro id repetido encontrado.
    """
    vistos: set[int] = set()
    for tarefa in tarefas:
        if tarefa.id_tarefa in vistos:
            _falhar(
                IdentificadorDuplicadoError(
                    f"Tarefa {tarefa.id_tarefa}: id_tarefa repetido no conjunto (RN-09)."
                )
            )
        vistos.add(tarefa.id_tarefa)


@dataclass(frozen=True, kw_only=True)
class _Conclusao:
    """Medidas internas de uma tarefa concluída, já normalizadas para UTC.

    Attributes:
        duracao_min: ``data_conclusao − data_criacao``, em minutos (RN-02).
        atrasada: ``True`` se ``data_conclusao > prazo`` (RN-03).
    """

    duracao_min: float
    atrasada: bool


def _medir_conclusao(tarefa: Tarefa, data_conclusao: datetime) -> _Conclusao:
    """Calcula duração e atraso de uma tarefa concluída sem alterar a original (RN-12).

    Args:
        tarefa: Tarefa concluída e validada.
        data_conclusao: Data de conclusão da tarefa.

    Returns:
        Medidas da conclusão, comparadas em UTC.
    """
    criacao = _para_utc(tarefa.data_criacao)
    conclusao = _para_utc(data_conclusao)
    return _Conclusao(
        duracao_min=(conclusao - criacao).total_seconds() / _SEGUNDOS_POR_MINUTO,
        atrasada=conclusao > _para_utc(tarefa.prazo),
    )


def _medir_conclusoes(tarefas: Sequence[Tarefa]) -> list[_Conclusao]:
    """Mede apenas as tarefas concluídas; pendentes e canceladas ficam de fora (RN-01).

    Args:
        tarefas: Tarefas validadas.

    Returns:
        Uma medida por tarefa concluída, na ordem de entrada.
    """
    # RN-08 já garante data_conclusao nas concluídas; a segunda condição só estreita o tipo.
    return [
        _medir_conclusao(tarefa, tarefa.data_conclusao)
        for tarefa in tarefas
        if tarefa.status == _STATUS_CONCLUIDA and tarefa.data_conclusao is not None
    ]


def _tempo_medio_min(conclusoes: Sequence[_Conclusao]) -> float | None:
    """Calcula a média de duração em minutos, arredondada só no resultado (RN-05).

    Args:
        conclusoes: Medidas das tarefas concluídas.

    Returns:
        Média com 2 casas decimais, ou ``None`` se não houver conclusões (RN-06).
    """
    if not conclusoes:
        return None
    media = math.fsum(conclusao.duracao_min for conclusao in conclusoes) / len(conclusoes)
    return round(media, _CASAS_DECIMAIS)


def _taxa_atraso_percentual(conclusoes: Sequence[_Conclusao]) -> float | None:
    """Calcula o percentual de conclusões após o prazo (RN-03).

    Args:
        conclusoes: Medidas das tarefas concluídas.

    Returns:
        Percentual com 2 casas decimais, ou ``None`` se não houver conclusões (RN-06).
    """
    if not conclusoes:
        return None
    atrasadas = sum(1 for conclusao in conclusoes if conclusao.atrasada)
    return round(_PERCENTUAL * atrasadas / len(conclusoes), _CASAS_DECIMAIS)


def _contar_status(tarefas: Sequence[Tarefa], status: str) -> int:
    """Conta as tarefas com o status informado.

    Args:
        tarefas: Tarefas validadas.
        status: Valor do domínio de status.

    Returns:
        Quantidade de tarefas com esse status.
    """
    return sum(1 for tarefa in tarefas if tarefa.status == status)


def _indicador_da_prioridade(prioridade: str, tarefas: Sequence[Tarefa]) -> IndicadorPrioridade:
    """Calcula os indicadores de uma prioridade; registra WARNING se não houver concluídas.

    Args:
        prioridade: Prioridade sendo calculada, usada apenas no log.
        tarefas: Tarefas dessa prioridade.

    Returns:
        Indicador com métricas ``None`` quando não há conclusões (seção 1.3.3).
    """
    conclusoes = _medir_conclusoes(tarefas)
    if not conclusoes:
        _logger.warning(
            "prioridade_sem_dados | prioridade=%s | total_tarefas=%d", prioridade, len(tarefas)
        )
    return IndicadorPrioridade(
        total_tarefas=len(tarefas),
        total_concluidas=len(conclusoes),
        tempo_medio_conclusao_min=_tempo_medio_min(conclusoes),
        taxa_atraso_percentual=_taxa_atraso_percentual(conclusoes),
    )


def _indicadores_por_prioridade(tarefas: Sequence[Tarefa]) -> dict[str, IndicadorPrioridade]:
    """Agrupa as tarefas por prioridade, sempre com as três chaves fixas (RN-11).

    Args:
        tarefas: Tarefas validadas.

    Returns:
        Dicionário com as chaves ``"baixa"``, ``"media"`` e ``"alta"``, nessa ordem.
    """
    return {
        prioridade: _indicador_da_prioridade(
            prioridade, [tarefa for tarefa in tarefas if tarefa.prioridade == prioridade]
        )
        for prioridade in _PRIORIDADES
    }

def analisar_tarefas(tarefas: list[Tarefa]) -> RelatorioProdutividade:
    """Calcula métricas de produtividade a partir de uma lista de tarefas.

    Args:
        tarefas: Lista de objetos Tarefa previamente validados quanto ao tipo.

    Returns:
        RelatorioProdutividade com as métricas gerais e por prioridade.

    Raises:
        ListaDeTarefasVaziaError: Se a lista recebida estiver vazia.
        ContratoDeEntradaError: Se algum campo obrigatório estiver ausente ou com tipo incorreto.
        ValorDeDominioInvalidoError: Se prioridade ou status estiverem fora do domínio permitido.
        DataInconsistenteError: Se houver inconsistência entre as datas de uma tarefa.
        IdentificadorDuplicadoError: Se houver id_tarefa repetido no conjunto.
        SemTarefasConcluidasError: Se nenhuma tarefa do conjunto estiver concluída.
    """
    _logger.info("analise_iniciada | total_tarefas=%d", len(tarefas))
    _validar_conjunto(tarefas)

    conclusoes = _medir_conclusoes(tarefas)
    tempo_medio = _tempo_medio_min(conclusoes)
    taxa_atraso = _taxa_atraso_percentual(conclusoes)
    if tempo_medio is None or taxa_atraso is None:
        _falhar(
            SemTarefasConcluidasError(
                "Nenhuma tarefa concluída no conjunto; tempo médio e taxa de atraso "
                "não podem ser calculados (RN-06)."
            )
        )

    relatorio = RelatorioProdutividade(
        total_tarefas=len(tarefas),
        total_concluidas=len(conclusoes),
        total_em_aberto=_contar_status(tarefas, _STATUS_PENDENTE),
        tempo_medio_conclusao_min=tempo_medio,
        taxa_atraso_percentual=taxa_atraso,
        indicadores_por_prioridade=_indicadores_por_prioridade(tarefas),
    )
    _logger.info(
        "analise_concluida | total_tarefas=%d | total_concluidas=%d",
        relatorio.total_tarefas,
        relatorio.total_concluidas,
    )
    return relatorio