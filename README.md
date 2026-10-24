# sdd-task-analyzer

[![CI](https://github.com/antoniovna/task-analyzer-ceub/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/antoniovna/task-analyzer-ceub/actions/workflows/ci.yml)

Módulo **TaskAnalyzer** — análise de tarefas e produtividade desenvolvida com
**Spec-Driven Development (SDD)** e **AI Harness**, entregue com pipeline de CI/CD, containerização
e governança ética de IA.

> Bootcamp III — Ciência da Computação (CEUB) · Antônio Vinicius Nunes de Alencar
> Status: **Fase 3 concluída** (`v2.0-fase3`) — 55/55 testes aprovados · cobertura de 100% em `src/` · CI verde no GitHub Actions e no contêiner

## Sobre o projeto

O TaskAnalyzer recebe uma lista de tarefas já registradas por um sistema externo e devolve um
relatório consolidado de métricas: totais, tempo médio de conclusão, taxa de atraso e indicadores
agrupados por prioridade. É um módulo **puramente analítico e sem estado** — não cria, não edita e
não persiste tarefas.

A fonte da verdade é a especificação em [`specs/task_analyzer_spec.md`](specs/task_analyzer_spec.md)
(v2.0). O código em `src/` é gerado por um assistente de IA, guiado por
[`CONTEXT_RULES.md`](CONTEXT_RULES.md), e só é aceito depois de passar pelo Test Harness, pelo
pipeline de CI e pela homologação humana registrada em Pull Request.

## Estrutura do repositório

```
sdd-task-analyzer/
├── .github/
│   └── workflows/
│       └── ci.yml                     # Pipeline de CI (GitHub Actions)
├── Dockerfile                         # Empacotamento: python:3.11-slim, usuário não-root
├── docker-compose.yml                 # Orquestração: docker compose run --rm tests
├── .dockerignore
├── README.md                          # Este arquivo
├── CONTEXT_RULES.md                   # Regras de governança para o agente de IA
├── .gitignore
├── requirements.txt                   # Dependências autorizadas (pytest, pytest-cov)
├── specs/
│   ├── task_analyzer_spec.md          # Contrato SDD (fonte da verdade)
│   ├── system_design_document.pdf     # Derivado da spec, para leitura e entrega
│   └── requirements.yaml              # Derivado da spec, legível por máquina
├── tests/
│   └── test_harness.py                # Test Harness (pytest) — escrito antes do código
└── src/
    └── task_analyzer.py               # Código gerado por IA e homologado por humano
```

| Zona | Artefatos | Quem altera |
|------|-----------|-------------|
| Contrato e governança | `specs/`, `CONTEXT_RULES.md` | Somente humano, via Pull Request |
| Validação independente | `tests/` | Somente humano; a IA não pode tocar no harness |
| Código gerado | `src/` | IA gera, humano homologa |
| Infraestrutura | `.github/`, `Dockerfile`, `docker-compose.yml` | IA gera sob as proibições da seção 4.1 do CONTEXT_RULES; humano homologa |

## Fluxo SDD adotado

```
specs/ + CONTEXT_RULES.md ──► Assistente de IA ──► src/task_analyzer.py
                                     ▲                       │
                                     │                       ▼
             reprovado (motivo no PR)│        CI: tests/test_harness.py
                                     │        (Python 3.11 + contêiner)
                                     │                       │
                                     └──── Pull Request + homologação humana
```

1. Toda sessão com a IA começa reenviando `CONTEXT_RULES.md` e a especificação.
2. Os testes existem antes do código. Se um teste falha, o código muda — nunca o teste.
3. Todo Pull Request para `develop` ou `main` dispara o pipeline; um build vermelho reprova o PR.
4. Nenhum artefato entra em `main` sem revisão humana registrada em Pull Request (ata de
   homologação com os 5 passos da spec, seção 4.3).

## Como executar

### Com Docker (recomendado)

Pré-requisito: Docker com o plugin Compose. Nenhuma instalação de Python é necessária.

```bash
git clone https://github.com/antoniovna/task-analyzer-ceub.git
cd task-analyzer-ceub
docker compose run --rm tests
```

Um único comando constrói a imagem `python:3.11-slim`, instala as dependências do
`requirements.txt` e executa a suíte inteira com cobertura, como usuário não-root. O resultado é
idêntico ao do pipeline de CI. Sem o Compose:

```bash
docker build -t task-analyzer .
docker run --rm task-analyzer
```

### Localmente

Pré-requisito: Python 3.11 ou superior.

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

pip install -r requirements.txt
python -m pytest tests/test_harness.py -v --cov=src --cov-report=term-missing
```

Meta de cobertura: **≥ 90%** de linhas em `src/`.

Use `python -m pytest` (e não apenas `pytest`): a forma com `-m` coloca a raiz do repositório no
`sys.path`, o que permite `from src.task_analyzer import ...`. O pipeline e a imagem Docker rodam
`pytest` direto e, por isso, definem `PYTHONPATH` na raiz (spec, seção 4.4) — sem alterar o
harness nem adicionar arquivos de configuração.

Se aparecer `unrecognized arguments: --cov=src`, o ambiente virtual não está ativo: o comando está
usando um Python sem o `pytest-cov`. Ative a `.venv` e rode novamente.

## Integração contínua

O workflow [`.github/workflows/ci.yml`](.github/workflows/ci.yml) roda em todo `push` e
`pull_request` nas branches `main` e `develop`, com dois jobs:

| Job | O que faz |
|-----|-----------|
| `Test Harness (Python 3.11)` | `ubuntu-latest` + Python 3.11 → `pip install -r requirements.txt` → `pytest tests/test_harness.py -v` com `--cov-fail-under=90` |
| `Test Harness no contêiner (python:3.11-slim)` | `docker compose build tests` → `docker compose run --rm tests` |

O build só fica verde com **todos os testes aprovados e cobertura ≥ 90%** nos dois ambientes.
O workflow tem permissão somente de leitura (`contents: read`) e não usa segredos. As proibições
que impedem "consertar" o pipeline enfraquecendo-o — pular testes, baixar a meta de cobertura,
`continue-on-error`, `|| true` — estão na seção 4.1 do [`CONTEXT_RULES.md`](CONTEXT_RULES.md).

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

## Decisão de contrato: especificação × enunciados

Os enunciados das Fases 2 e 3 usam nomes e comportamentos genéricos que divergem da especificação
da Fase 1 (o da Fase 3 cita, por exemplo, `TaskValidationError` para datas inválidas). Como no SDD
a especificação é a fonte da verdade, e o `CONTEXT_RULES.md` proíbe alterar a assinatura pública e
os cenários de aceite sem nova versão da spec, este projeto segue
`specs/task_analyzer_spec.md`. A v2.0 mudou apenas o contrato do repositório (infraestrutura), não
o do módulo. Correspondência:

| Enunciado | Este projeto (spec) | Fundamento |
|-----------|---------------------|------------|
| `analyze_tasks` | `analisar_tarefas` | §1.3.1 — nomes do domínio em português |
| `TaskValidationError` | `TaskAnalyzerError` (base) + 6 exceções específicas | §1.5 — `except TaskAnalyzerError` captura todas |
| Datas inconsistentes → `TaskValidationError` | `DataInconsistenteError` | RN-07 |
| `total_pendentes` | `total_em_aberto` | §1.3.3 |
| `tempo_medio_conclusao_horas` | `tempo_medio_conclusao_min` | §1.3.3 e RN-02 (horas = minutos ÷ 60) |
| Lista vazia → `0.0`, sem exceção | `ListaDeTarefasVaziaError` | RN-06 e RN-10 — falha explícita |
| Apenas pendentes → `0.0`, sem exceção | `SemTarefasConcluidasError` | RN-06 — exceção específica e tratada, nunca `ZeroDivisionError` |
| Prioridade sem concluídas → `0.0` | `None` | §1.3.3 — `0.0` confundiria "sem dados" com "instantâneo" |
| `specs/system_design_document.pdf`, `specs/requirements.yaml` | Derivados de `task_analyzer_spec.md` | Spec v2.0 — uma única fonte da verdade, sem documentos divergentes |

O requisito de fundo dos enunciados — nenhuma divisão por zero e nenhuma exceção não tratada — é
atendido: toda falha é uma exceção específica do módulo, derivada de `TaskAnalyzerError`.

## Resultados

### Fase 3 — DevOps e governança (`v2.0-fase3`)

| Verificação | Resultado |
|-------------|-----------|
| Pipeline no GitHub Actions (Python 3.11.17, ubuntu-latest) | 55/55 aprovados · cobertura 100% |
| Suíte no contêiner `python:3.11-slim` (CI e local) | 55/55 aprovados · cobertura 100% · usuário `uid=1000` |
| `docker compose run --rm tests` local | 55 passed · exit code 0 |
| Teste negativo (cálculo adulterado em contêiner descartável) | 9 falhas · exit code 1 — o build reprova de fato |
| Arquivos de `src/` e `tests/` alterados na fase | Nenhum |

### Fase 2 — Implementação (`v1.0-fase2`)

| Verificação | Resultado |
|-------------|-----------|
| Test Harness (`tests/test_harness.py`) | 55/55 testes aprovados |
| Cobertura de linhas em `src/` | 100% (meta: ≥ 90%) |
| Cenário 1 — métricas de referência | 502,50 min · 50,00% de atraso · indicadores por prioridade conforme a spec |
| Cenário 2 — variações 2.a a 2.e | Exceções específicas, derivadas de `TaskAnalyzerError` |
| Casos de borda 3.a a 3.f | Aprovados |
| Teste manual de borda | 100 mil tarefas em 4 fusos e status mistos, em ~0,5 s; mesmo relatório com a ordem invertida |

### Histórico de Pull Requests

| PR | Branch → destino | Conteúdo |
|----|------------------|----------|
| #1 | `feature/sdd-specification` → `develop` | Especificação SDD, CONTEXT_RULES e decisão de contrato |
| #2 | `feature/test-harness` → `develop` | Test Harness escrito antes do código (fase vermelha) |
| #3 | `feature/task-analyzer-impl` → `develop` | Implementação gerada por IA em 4 incrementos |
| #4 | `feature/release-docs` → `develop` | README da release |
| #5 | `develop` → `main` | Release `v1.0-fase2` |
| #6 | `feature/spec-v2` → `develop` | Spec v2.0, governança de infraestrutura e derivados da spec |
| #7 | `feature/ci-pipeline` → `develop` | Pipeline de CI no GitHub Actions |
| #8 | `feature/docker` → `develop` | Dockerfile, docker-compose e job de contêiner no CI |
| #9 | `feature/release-docs-fase3` → `develop` | README da release |
| #10 | `develop` → `main` | Release `v2.0-fase3` |

Cada PR traz o que foi gerado por IA (com os prompts), as decisões submetidas à revisão humana, o
resultado dos testes, o checklist do CONTEXT_RULES e a ata de homologação.

## Versionamento

Git Flow simplificado:

- `main` — sempre estável; recebe apenas releases vindas de `develop`.
- `develop` — integração do trabalho aprovado.
- `feature/*` — um incremento por branch (ex.: `feature/spec-v2`, `feature/ci-pipeline`,
  `feature/docker`).

Merge somente por Pull Request com CI verde e revisão humana registrada. Commits seguem o padrão
`tipo: descrição` (`feat`, `fix`, `test`, `docs`, `refactor`, `chore`, `ci`, `build`), e o corpo
registra o que foi gerado por IA e o que foi corrigido manualmente. Entregas são marcadas com tags
(`v1.0-fase2`, `v2.0-fase3`).
