"""Módulo TaskAnalyzer: métricas de produtividade a partir de um conjunto de tarefas.

Implementa o contrato de ``specs/task_analyzer_spec.md`` (v1.0). O módulo é puramente analítico
e sem estado: valida as tarefas recebidas, calcula as métricas e devolve um relatório imutável.
A única função pública é ``analisar_tarefas``; as auxiliares de validação e cálculo são privadas.
"""

from dataclasses import dataclass
from datetime import datetime


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
