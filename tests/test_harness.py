"""Test Harness do módulo TaskAnalyzer.

Traduz os cenários de aceite de specs/task_analyzer_spec.md (seção 2) em testes automatizados.
Escrito antes da implementação: se um teste falha, o código muda — nunca o teste
(CONTEXT_RULES, seção 4).

Execução, a partir da raiz do repositório:
    python -m pytest --cov=src --cov-report=term-missing
"""

from __future__ import annotations

import dataclasses
import inspect
import logging
from collections.abc import Callable
from datetime import datetime, timedelta, timezone

import pytest

import src.task_analyzer as task_analyzer
from src.task_analyzer import (
    ContratoDeEntradaError,
    DataInconsistenteError,
    IdentificadorDuplicadoError,
    IndicadorPrioridade,
    ListaDeTarefasVaziaError,
    RelatorioProdutividade,
    SemTarefasConcluidasError,
    Tarefa,
    TaskAnalyzerError,
    ValorDeDominioInvalidoError,
    analisar_tarefas,
)

UTC = timezone.utc
FUSO_BRASILIA = timezone(timedelta(hours=-3))
CAMPOS_DE_DATA = ("data_criacao", "data_inicio", "prazo", "data_conclusao")

FabricaDeTarefa = Callable[..., Tarefa]


def _utc(dia: int, mes: int, hora: int, minuto: int = 0) -> datetime:
    """Cria um datetime em UTC no ano de referência da massa de dados (2026)."""
    return datetime(2026, mes, dia, hora, minuto, tzinfo=UTC)


def _converter_datas(tarefa: Tarefa, conversor: Callable[[datetime], datetime]) -> Tarefa:
    """Devolve uma cópia da tarefa com todas as datas presentes transformadas pelo conversor."""
    novas_datas = {
        campo: conversor(getattr(tarefa, campo))
        for campo in CAMPOS_DE_DATA
        if getattr(tarefa, campo) is not None
    }
    return dataclasses.replace(tarefa, **novas_datas)


# --------------------------------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------------------------------


@pytest.fixture
def tarefas_validas() -> list[Tarefa]:
    """Massa de dados de referência do Cenário 1 (spec, seção 2.1)."""
    return [
        Tarefa(
            id_tarefa=1, titulo="Corrigir bug de login", prioridade="alta", status="concluida",
            data_criacao=_utc(2, 3, 9), prazo=_utc(2, 3, 18), data_conclusao=_utc(2, 3, 12),
        ),
        Tarefa(
            id_tarefa=2, titulo="Revisar PR de relatórios", prioridade="alta", status="concluida",
            data_criacao=_utc(2, 3, 10), prazo=_utc(2, 3, 18), data_conclusao=_utc(3, 3, 10),
        ),
        Tarefa(
            id_tarefa=3, titulo="Atualizar documentação da API", prioridade="media",
            status="concluida",
            data_criacao=_utc(1, 3, 8), prazo=_utc(1, 3, 12), data_conclusao=_utc(1, 3, 14),
        ),
        Tarefa(
            id_tarefa=4, titulo="Refatorar serviço de e-mail", prioridade="media",
            status="pendente",
            data_criacao=_utc(3, 3, 9), prazo=_utc(5, 3, 18), data_conclusao=None,
        ),
        Tarefa(
            id_tarefa=5, titulo="Ajustar layout do rodapé", prioridade="baixa", status="concluida",
            data_criacao=_utc(4, 3, 11), prazo=_utc(4, 3, 18), data_conclusao=_utc(4, 3, 11, 30),
        ),
        Tarefa(
            id_tarefa=6, titulo="Migrar banco de testes", prioridade="alta", status="cancelada",
            data_criacao=_utc(27, 2, 8), prazo=_utc(28, 2, 18), data_conclusao=None,
        ),
    ]


@pytest.fixture
def tarefa_base() -> FabricaDeTarefa:
    """Fábrica de tarefas válidas: prioridade média, concluída em 60 min, dentro do prazo.

    Qualquer campo pode ser sobrescrito por argumento nomeado. A tarefa é criada no momento da
    chamada, o que permite construí-la dentro de ``pytest.raises``.
    """

    def _criar(**sobrescritas: object) -> Tarefa:
        campos: dict[str, object] = {
            "id_tarefa": 1,
            "titulo": "Tarefa de teste",
            "prioridade": "media",
            "status": "concluida",
            "data_criacao": _utc(10, 3, 9),
            "prazo": _utc(10, 3, 18),
            "data_conclusao": _utc(10, 3, 10),
        }
        campos.update(sobrescritas)
        return Tarefa(**campos)

    return _criar


@pytest.fixture
def tarefas_sem_concluidas(tarefa_base: FabricaDeTarefa) -> list[Tarefa]:
    """Três tarefas válidas, nenhuma concluída (spec, variação 2.e)."""
    return [
        tarefa_base(id_tarefa=1, status="pendente", data_conclusao=None),
        tarefa_base(id_tarefa=2, status="cancelada", data_conclusao=None),
        tarefa_base(id_tarefa=3, status="pendente", data_conclusao=None, prioridade="alta"),
    ]


# --------------------------------------------------------------------------------------------
# Cenário 1 — Sucesso (spec, seção 2.1)
# --------------------------------------------------------------------------------------------


def test_metricas_gerais_com_tarefas_validas(tarefas_validas: list[Tarefa]) -> None:
    relatorio = analisar_tarefas(tarefas_validas)

    assert isinstance(relatorio, RelatorioProdutividade)
    assert relatorio.total_tarefas == 6
    assert relatorio.total_concluidas == 4
    assert relatorio.total_em_aberto == 1
    assert relatorio.tempo_medio_conclusao_min == 502.50
    assert isinstance(relatorio.tempo_medio_conclusao_min, float)
    assert relatorio.taxa_atraso_percentual == 50.00
    assert isinstance(relatorio.taxa_atraso_percentual, float)


@pytest.mark.parametrize(
    ("prioridade", "esperado"),
    [
        pytest.param(
            "baixa",
            IndicadorPrioridade(
                total_tarefas=1, total_concluidas=1,
                tempo_medio_conclusao_min=30.00, taxa_atraso_percentual=0.00,
            ),
            id="baixa",
        ),
        pytest.param(
            "media",
            IndicadorPrioridade(
                total_tarefas=2, total_concluidas=1,
                tempo_medio_conclusao_min=360.00, taxa_atraso_percentual=100.00,
            ),
            id="media",
        ),
        pytest.param(
            "alta",
            IndicadorPrioridade(
                total_tarefas=3, total_concluidas=2,
                tempo_medio_conclusao_min=810.00, taxa_atraso_percentual=50.00,
            ),
            id="alta",
        ),
    ],
)
def test_indicadores_por_prioridade(
    tarefas_validas: list[Tarefa], prioridade: str, esperado: IndicadorPrioridade
) -> None:
    indicadores = analisar_tarefas(tarefas_validas).indicadores_por_prioridade

    assert set(indicadores) == {"baixa", "media", "alta"}
    indicador = indicadores[prioridade]
    assert isinstance(indicador, IndicadorPrioridade)
    assert indicador.total_tarefas == esperado.total_tarefas
    assert indicador.total_concluidas == esperado.total_concluidas
    assert indicador.tempo_medio_conclusao_min == esperado.tempo_medio_conclusao_min
    assert indicador.taxa_atraso_percentual == esperado.taxa_atraso_percentual


# --------------------------------------------------------------------------------------------
# Cenário 2 — Exceções (spec, seção 2.2)
# --------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("sobrescritas", "campo_citado"),
    [
        pytest.param(
            {"data_conclusao": _utc(10, 3, 8)}, "data_conclusao",
            id="2.a-RN07-conclusao-antes-da-criacao",
        ),
        pytest.param(
            {"data_conclusao": None}, "data_conclusao",
            id="2.b-RN08-concluida-sem-data-de-conclusao",
        ),
        pytest.param(
            {"status": "pendente"}, "data_conclusao",
            id="RN08-pendente-com-data-de-conclusao",
        ),
        pytest.param(
            {"status": "cancelada"}, "data_conclusao",
            id="RN08-cancelada-com-data-de-conclusao",
        ),
        pytest.param(
            {"prazo": _utc(10, 3, 9)}, "prazo",
            id="RN07-prazo-igual-a-criacao",
        ),
        pytest.param(
            {"prazo": _utc(10, 3, 8)}, "prazo",
            id="RN07-prazo-antes-da-criacao",
        ),
        pytest.param(
            {"data_inicio": _utc(10, 3, 8)}, "data_inicio",
            id="RN07-inicio-antes-da-criacao",
        ),
    ],
)
def test_datas_inconsistentes_levantam_erro(
    tarefa_base: FabricaDeTarefa, sobrescritas: dict[str, object], campo_citado: str
) -> None:
    with pytest.raises(DataInconsistenteError, match="Tarefa 42") as erro:
        analisar_tarefas([tarefa_base(id_tarefa=1), tarefa_base(id_tarefa=42, **sobrescritas)])

    assert campo_citado in str(erro.value)


@pytest.mark.parametrize(
    ("sobrescritas", "valor_citado"),
    [
        pytest.param({"prioridade": "urgente"}, "urgente", id="2.c-prioridade-urgente"),
        pytest.param({"prioridade": "Alta"}, "Alta", id="prioridade-com-maiuscula"),
        pytest.param({"prioridade": "média"}, "média", id="prioridade-com-acento"),
        pytest.param(
            {"status": "em_andamento", "data_conclusao": None}, "em_andamento",
            id="status-fora-do-dominio",
        ),
    ],
)
def test_dominio_invalido_levanta_erro(
    tarefa_base: FabricaDeTarefa, sobrescritas: dict[str, object], valor_citado: str
) -> None:
    with pytest.raises(ValorDeDominioInvalidoError, match="Tarefa 42") as erro:
        analisar_tarefas([tarefa_base(id_tarefa=1), tarefa_base(id_tarefa=42, **sobrescritas)])

    assert valor_citado in str(erro.value)


def test_lista_vazia_levanta_erro() -> None:
    with pytest.raises(ListaDeTarefasVaziaError, match="vazia"):
        analisar_tarefas([])


def test_sem_concluidas_nao_divide_por_zero(tarefas_sem_concluidas: list[Tarefa]) -> None:
    with pytest.raises(SemTarefasConcluidasError, match="conclu"):
        analisar_tarefas(tarefas_sem_concluidas)


# --------------------------------------------------------------------------------------------
# Cenários complementares de borda (spec, seção 2.3)
# --------------------------------------------------------------------------------------------


def _caso_3a_conclusao_no_instante_do_prazo(nova_tarefa: FabricaDeTarefa) -> None:
    prazo = _utc(10, 3, 18)

    relatorio = analisar_tarefas([nova_tarefa(prazo=prazo, data_conclusao=prazo)])

    assert relatorio.taxa_atraso_percentual == 0.00


def _caso_3b_prioridade_sem_tarefas(nova_tarefa: FabricaDeTarefa) -> None:
    relatorio = analisar_tarefas(
        [nova_tarefa(id_tarefa=1, prioridade="alta"), nova_tarefa(id_tarefa=2, prioridade="media")]
    )

    baixa = relatorio.indicadores_por_prioridade["baixa"]
    assert baixa.total_tarefas == 0
    assert baixa.total_concluidas == 0
    assert baixa.tempo_medio_conclusao_min is None
    assert baixa.taxa_atraso_percentual is None


def _caso_3c_todas_concluidas_e_atrasadas(nova_tarefa: FabricaDeTarefa) -> None:
    tarefas = [nova_tarefa(id_tarefa=id_, data_conclusao=_utc(11, 3, 9)) for id_ in (1, 2, 3)]

    relatorio = analisar_tarefas(tarefas)

    assert relatorio.taxa_atraso_percentual == 100.00


def _caso_3d_ids_duplicados(nova_tarefa: FabricaDeTarefa) -> None:
    with pytest.raises(IdentificadorDuplicadoError, match="Tarefa 7"):
        analisar_tarefas([nova_tarefa(id_tarefa=7), nova_tarefa(id_tarefa=7, titulo="Outra")])


def _caso_3e_duracao_zero(nova_tarefa: FabricaDeTarefa) -> None:
    criacao = _utc(10, 3, 9)

    relatorio = analisar_tarefas(
        [
            nova_tarefa(id_tarefa=1, data_criacao=criacao, data_conclusao=criacao),
            nova_tarefa(
                id_tarefa=2, data_criacao=criacao, data_conclusao=criacao + timedelta(minutes=60)
            ),
        ]
    )

    assert relatorio.tempo_medio_conclusao_min == 30.00


def _caso_3f_fuso_diferente_de_utc(nova_tarefa: FabricaDeTarefa) -> None:
    em_utc = [
        nova_tarefa(id_tarefa=1, prioridade="alta"),
        nova_tarefa(id_tarefa=2, prioridade="baixa", data_conclusao=_utc(11, 3, 9)),
        nova_tarefa(id_tarefa=3, status="pendente", data_conclusao=None),
    ]
    em_brasilia = [
        _converter_datas(tarefa, lambda data: data.astimezone(FUSO_BRASILIA)) for tarefa in em_utc
    ]

    assert analisar_tarefas(em_brasilia) == analisar_tarefas(em_utc)


@pytest.mark.parametrize(
    "caso",
    [
        pytest.param(_caso_3a_conclusao_no_instante_do_prazo, id="3.a-conclusao-no-prazo"),
        pytest.param(_caso_3b_prioridade_sem_tarefas, id="3.b-prioridade-sem-tarefas"),
        pytest.param(_caso_3c_todas_concluidas_e_atrasadas, id="3.c-todas-atrasadas"),
        pytest.param(_caso_3d_ids_duplicados, id="3.d-ids-duplicados"),
        pytest.param(_caso_3e_duracao_zero, id="3.e-duracao-zero"),
        pytest.param(_caso_3f_fuso_diferente_de_utc, id="3.f-fuso-diferente-de-utc"),
    ],
)
def test_casos_de_borda(
    tarefa_base: FabricaDeTarefa, caso: Callable[[FabricaDeTarefa], None]
) -> None:
    caso(tarefa_base)


# --------------------------------------------------------------------------------------------
# Contrato complementar — regras das seções 1.3, 1.4 e 1.5 sem cenário numerado
# --------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "excecao",
    [
        ListaDeTarefasVaziaError,
        ContratoDeEntradaError,
        ValorDeDominioInvalidoError,
        DataInconsistenteError,
        IdentificadorDuplicadoError,
        SemTarefasConcluidasError,
    ],
)
def test_hierarquia_de_excecoes(excecao: type[Exception]) -> None:
    """Seção 1.5: toda exceção do módulo deriva de TaskAnalyzerError."""
    assert issubclass(excecao, TaskAnalyzerError)
    assert issubclass(TaskAnalyzerError, Exception)


@pytest.mark.parametrize(
    ("sobrescritas", "cita_id"),
    [
        pytest.param({"id_tarefa": "42"}, False, id="id_tarefa-str"),
        pytest.param({"titulo": None}, True, id="titulo-ausente"),
        pytest.param({"prioridade": None}, True, id="prioridade-ausente"),
        pytest.param({"status": 1}, True, id="status-int"),
        pytest.param({"data_criacao": None}, True, id="data_criacao-ausente"),
        pytest.param({"prazo": "2026-03-10T18:00:00Z"}, True, id="prazo-str"),
        pytest.param({"data_conclusao": "2026-03-10T10:00:00Z"}, True, id="data_conclusao-str"),
        pytest.param({"data_inicio": "2026-03-10T09:30:00Z"}, True, id="data_inicio-str"),
    ],
)
def test_contrato_de_entrada_invalido_levanta_erro(
    tarefa_base: FabricaDeTarefa, sobrescritas: dict[str, object], cita_id: bool
) -> None:
    """Seção 1.3.2: campo obrigatório ausente ou com tipo incorreto."""
    with pytest.raises(ContratoDeEntradaError) as erro:
        analisar_tarefas([tarefa_base(**{"id_tarefa": 42, **sobrescritas})])

    if cita_id:
        assert "Tarefa 42" in str(erro.value)


@pytest.mark.parametrize(
    "sobrescritas",
    [
        pytest.param({"id_tarefa": 0}, id="id-zero"),
        pytest.param({"id_tarefa": -5}, id="id-negativo"),
        pytest.param({"titulo": "   "}, id="titulo-so-espacos"),
        pytest.param({"titulo": "x" * 201}, id="titulo-com-201-caracteres"),
    ],
)
def test_restricoes_de_campo_levantam_erro_do_modulo(
    tarefa_base: FabricaDeTarefa, sobrescritas: dict[str, object]
) -> None:
    """Seção 1.3.2 e RN-10. A spec não fixa a subclasse; exige-se a base do módulo."""
    with pytest.raises(TaskAnalyzerError):
        analisar_tarefas([tarefa_base(**sobrescritas)])


def test_titulo_com_200_caracteres_e_aceito(tarefa_base: FabricaDeTarefa) -> None:
    relatorio = analisar_tarefas([tarefa_base(titulo="x" * 200)])

    assert relatorio.total_tarefas == 1


def test_data_inicio_valida_nao_altera_metricas(tarefa_base: FabricaDeTarefa) -> None:
    """Seção 1.3.2: data_inicio é validada, mas não participa dos cálculos desta versão."""
    sem_inicio = analisar_tarefas([tarefa_base()])
    com_inicio = analisar_tarefas([tarefa_base(data_inicio=_utc(10, 3, 9, 30))])

    assert com_inicio == sem_inicio


def test_datas_naive_sao_tratadas_como_utc(tarefas_validas: list[Tarefa]) -> None:
    """RN-04: datas sem fuso são consideradas UTC."""
    naive = [
        _converter_datas(tarefa, lambda data: data.replace(tzinfo=None))
        for tarefa in tarefas_validas
    ]

    assert analisar_tarefas(naive) == analisar_tarefas(tarefas_validas)


@pytest.mark.parametrize(
    "data_criacao",
    [
        pytest.param(datetime(2026, 3, 10, 9, 0), id="criacao-naive"),
        pytest.param(_utc(10, 3, 9), id="criacao-utc"),
    ],
)
def test_fusos_misturados_sao_normalizados_para_utc(
    tarefa_base: FabricaDeTarefa, data_criacao: datetime
) -> None:
    """RN-04: 07:00 em UTC-3 equivale a 10:00 UTC, uma hora após a criação às 09:00 UTC."""
    conclusao = datetime(2026, 3, 10, 7, 0, tzinfo=FUSO_BRASILIA)

    relatorio = analisar_tarefas(
        [tarefa_base(data_criacao=data_criacao, data_conclusao=conclusao)]
    )

    assert relatorio.tempo_medio_conclusao_min == 60.00


def test_entrada_nao_e_modificada(tarefas_validas: list[Tarefa]) -> None:
    """RN-12: a lista recebida e seus objetos permanecem intactos."""
    entrada = list(reversed(tarefas_validas))
    copia = list(entrada)

    analisar_tarefas(entrada)

    assert entrada == copia
    assert all(original is atual for original, atual in zip(copia, entrada, strict=True))


def test_resultado_independe_da_ordem_de_entrada(tarefas_validas: list[Tarefa]) -> None:
    """Determinismo (CONTEXT_RULES, seção 3)."""
    assert analisar_tarefas(list(reversed(tarefas_validas))) == analisar_tarefas(tarefas_validas)


def test_estruturas_de_dados_sao_imutaveis(tarefas_validas: list[Tarefa]) -> None:
    """CONTEXT_RULES, seção 3: dataclasses congeladas para entrada e saída."""
    relatorio = analisar_tarefas(tarefas_validas)

    with pytest.raises(dataclasses.FrozenInstanceError):
        tarefas_validas[0].status = "pendente"  # type: ignore[misc]
    with pytest.raises(dataclasses.FrozenInstanceError):
        relatorio.total_tarefas = 0  # type: ignore[misc]
    with pytest.raises(dataclasses.FrozenInstanceError):
        relatorio.indicadores_por_prioridade["alta"].total_tarefas = 0  # type: ignore[misc]


@pytest.mark.parametrize(
    ("estrutura", "campos_do_contrato"),
    [
        pytest.param(
            Tarefa,
            {
                "id_tarefa", "titulo", "prioridade", "status",
                "data_criacao", "data_inicio", "prazo", "data_conclusao",
            },
            id="Tarefa",
        ),
        pytest.param(
            RelatorioProdutividade,
            {
                "total_tarefas", "total_concluidas", "total_em_aberto",
                "tempo_medio_conclusao_min", "taxa_atraso_percentual",
                "indicadores_por_prioridade",
            },
            id="RelatorioProdutividade",
        ),
        pytest.param(
            IndicadorPrioridade,
            {
                "total_tarefas", "total_concluidas",
                "tempo_medio_conclusao_min", "taxa_atraso_percentual",
            },
            id="IndicadorPrioridade",
        ),
    ],
)
def test_estruturas_tem_exatamente_os_campos_do_contrato(
    estrutura: type, campos_do_contrato: set[str]
) -> None:
    """Seções 1.3.2 e 1.3.3: nenhum campo a mais, nenhum a menos."""
    assert {campo.name for campo in dataclasses.fields(estrutura)} == campos_do_contrato


def test_analisar_tarefas_e_a_unica_funcao_publica() -> None:
    """Seção 1.3.1: auxiliares são privadas, prefixadas com underscore."""
    funcoes_publicas = {
        nome
        for nome, funcao in inspect.getmembers(task_analyzer, inspect.isfunction)
        if funcao.__module__ == task_analyzer.__name__ and not nome.startswith("_")
    }

    assert funcoes_publicas == {"analisar_tarefas"}


def test_logs_de_sucesso_e_prioridade_sem_dados(
    tarefa_base: FabricaDeTarefa, caplog: pytest.LogCaptureFixture
) -> None:
    """CONTEXT_RULES, seção 3: INFO no início e fim; WARNING para prioridade sem dados."""
    caplog.set_level(logging.INFO)

    analisar_tarefas([tarefa_base(prioridade="alta")])

    niveis = {registro.levelno for registro in caplog.records}
    assert logging.INFO in niveis
    assert logging.WARNING in niveis


def test_log_de_erro_antes_de_levantar_excecao(caplog: pytest.LogCaptureFixture) -> None:
    """CONTEXT_RULES, seção 3: ERROR registrado antes de levantar a exceção."""
    caplog.set_level(logging.INFO)

    with pytest.raises(ListaDeTarefasVaziaError):
        analisar_tarefas([])

    assert any(registro.levelno == logging.ERROR for registro in caplog.records)
