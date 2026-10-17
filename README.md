# sdd-task-analyzer

Módulo **TaskAnalyzer** — análise de tarefas e produtividade desenvolvida com
**Spec-Driven Development (SDD)** e **AI Harness**.

> Bootcamp III — Ciência da Computação (CEUB) · Antônio Vinicius Nunes de Alencar
> Status: **Fase 2 concluída** (`v1.0-fase2`) — 55/55 testes aprovados · cobertura de 100% em `src/`

## Sobre o projeto

O TaskAnalyzer recebe uma lista de tarefas já registradas por um sistema externo e devolve um
relatório consolidado de métricas: totais, tempo médio de conclusão, taxa de atraso e indicadores
agrupados por prioridade. É um módulo **puramente analítico e sem estado** — não cria, não edita e
não persiste tarefas.

A fonte da verdade é a especificação em [`specs/task_analyzer_spec.md`](specs/task_analyzer_spec.md).
O código em `src/` é gerado por um assistente de IA, guiado por
[`CONTEXT_RULES.md`](CONTEXT_RULES.md), e só é aceito depois de passar pelo Test Harness e pela
homologação humana registrada em Pull Request.

## Estrutura do repositório

```
sdd-task-analyzer/
├── README.md                  # Este arquivo
├── CONTEXT_RULES.md           # Regras de governança para o agente de IA
├── .gitignore
├── requirements.txt           # Dependências autorizadas (pytest, pytest-cov)
├── specs/
│   └── task_analyzer_spec.md  # Contrato SDD (fonte da verdade)
├── tests/
│   └── test_harness.py        # Test Harness (pytest) — escrito antes do código
└── src/
    └── task_analyzer.py       # Código gerado por IA e homologado por humano
```

| Zona | Artefatos | Quem altera |
|------|-----------|-------------|
| Contrato e governança | `specs/`, `CONTEXT_RULES.md` | Somente humano, via Pull Request |
| Validação independente | `tests/` | Somente humano; a IA não pode tocar no harness |
| Código gerado | `src/` | IA gera, humano homologa |

## Fluxo SDD adotado

```
specs/ + CONTEXT_RULES.md ──► Assistente de IA ──► src/task_analyzer.py
                                     ▲                       │
                                     │                       ▼
             reprovado (motivo no PR)│              tests/test_harness.py
                                     │                       │
                                     └──── Pull Request + homologação humana
```

1. Toda sessão com a IA começa reenviando `CONTEXT_RULES.md` e a especificação.
2. Os testes existem antes do código. Se um teste falha, o código muda — nunca o teste.
3. Nenhum artefato entra em `main` sem revisão humana registrada em Pull Request.

## Decisão de contrato: especificação × enunciado da Fase 2

O enunciado da Fase 2 usa nomes e comportamentos genéricos que divergem da especificação da Fase 1.
Como no SDD a especificação é a fonte da verdade, e o `CONTEXT_RULES.md` proíbe alterar a
assinatura pública e os cenários de aceite sem nova versão da spec, este projeto segue
`specs/task_analyzer_spec.md` (v1.0). Correspondência:

| Enunciado da Fase 2 | Este projeto (spec v1.0) | Fundamento |
|---------------------|--------------------------|------------|
| `analyze_tasks` | `analisar_tarefas` | §1.3.1 — nomes do domínio em português |
| `TaskValidationError` | `TaskAnalyzerError` (base) + 6 exceções específicas | §1.5 — `except TaskAnalyzerError` captura todas |
| Datas inconsistentes → `TaskValidationError` | `DataInconsistenteError` | RN-07 |
| `total_pendentes` | `total_em_aberto` | §1.3.3 |
| `tempo_medio_conclusao_horas` | `tempo_medio_conclusao_min` | §1.3.3 e RN-02 (horas = minutos ÷ 60) |
| Lista vazia → `0.0`, sem exceção | `ListaDeTarefasVaziaError` | RN-06 e RN-10 — falha explícita |
| Apenas pendentes → `0.0`, sem exceção | `SemTarefasConcluidasError` | RN-06 — exceção específica e tratada, nunca `ZeroDivisionError` |
| Prioridade sem concluídas → `0.0` | `None` | §1.3.3 — `0.0` confundiria "sem dados" com "instantâneo" |

O requisito de fundo do enunciado — nenhuma divisão por zero e nenhuma exceção não tratada — é
atendido: toda falha é uma exceção específica do módulo, derivada de `TaskAnalyzerError`.

## Como executar

Pré-requisito: Python 3.11 ou superior.

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

pip install -r requirements.txt
python -m pytest --cov=src --cov-report=term-missing
```

Meta de cobertura: **≥ 90%** de linhas em `src/`.

Use `python -m pytest` (e não apenas `pytest`): a forma com `-m` coloca a raiz do repositório no
`sys.path`, o que permite `from src.task_analyzer import ...` sem arquivos de configuração extras
fora da árvore fixa do projeto.

Se aparecer `unrecognized arguments: --cov=src`, o ambiente virtual não está ativo: o comando está
usando um Python sem o `pytest-cov`. Ative a `.venv` e rode novamente.

## Exemplo de uso

```python
from datetime import datetime, timezone

from src.task_analyzer import Tarefa, TaskAnalyzerError, analisar_tarefas

utc = timezone.utc
tarefas = [
    Tarefa(
        id_tarefa=1, titulo="Corrigir bug de login", prioridade="alta", status="concluida",
        data_criacao=datetime(2026, 3, 2, 9, tzinfo=utc),
        prazo=datetime(2026, 3, 2, 18, tzinfo=utc),
        data_conclusao=datetime(2026, 3, 2, 12, tzinfo=utc),
    ),
    Tarefa(
        id_tarefa=2, titulo="Refatorar serviço de e-mail", prioridade="media", status="pendente",
        data_criacao=datetime(2026, 3, 3, 9, tzinfo=utc),
        prazo=datetime(2026, 3, 5, 18, tzinfo=utc),
        data_conclusao=None,
    ),
]

try:
    relatorio = analisar_tarefas(tarefas)
except TaskAnalyzerError as erro:
    print(f"Entrada rejeitada: {erro}")
else:
    print(relatorio.tempo_medio_conclusao_min)  # 180.0
    print(relatorio.indicadores_por_prioridade["media"].tempo_medio_conclusao_min)  # None
```

## Resultados da Fase 2

| Verificação | Resultado |
|-------------|-----------|
| Test Harness (`tests/test_harness.py`) | 55/55 testes aprovados |
| Cobertura de linhas em `src/` | 100% (meta: ≥ 90%) |
| Cenário 1 — métricas de referência | 502,50 min · 50,00% de atraso · indicadores por prioridade conforme a spec |
| Cenário 2 — variações 2.a a 2.e | Exceções específicas, derivadas de `TaskAnalyzerError` |
| Casos de borda 3.a a 3.f | Aprovados |
| Teste manual de borda | 100 mil tarefas em 4 fusos e status mistos, em ~0,5 s; mesmo relatório com a ordem invertida |

Histórico de Pull Requests da fase:

| PR | Branch → destino | Conteúdo |
|----|------------------|----------|
| #1 | `feature/sdd-specification` → `develop` | Especificação SDD, CONTEXT_RULES e decisão de contrato |
| #2 | `feature/test-harness` → `develop` | Test Harness escrito antes do código (fase vermelha) |
| #3 | `feature/task-analyzer-impl` → `develop` | Implementação gerada por IA em 4 incrementos |
| #4 | `feature/release-docs` → `develop` | README da release |
| #5 | `develop` → `main` | Release `v1.0-fase2` |

## Versionamento

Git Flow simplificado:

- `main` — sempre estável; recebe apenas releases vindas de `develop`.
- `develop` — integração do trabalho aprovado.
- `feature/*` — um incremento por branch (ex.: `feature/sdd-specification`,
  `feature/test-harness`, `feature/task-analyzer-impl`).

Commits seguem o padrão `tipo: descrição` (`feat`, `fix`, `test`, `docs`, `refactor`, `chore`), e o
corpo registra o que foi gerado por IA e o que foi corrigido manualmente. Entregas são marcadas com
tags (`v1.0-fase2`, `v2.0-fase3`).
