# sdd-task-analyzer

Módulo **TaskAnalyzer** — análise de tarefas e produtividade desenvolvida com
**Spec-Driven Development (SDD)** e **AI Harness**.

> Bootcamp III — Ciência da Computação (CEUB) · Antônio Vinicius Nunes de Alencar
> Status: **Fase 2 — em andamento** (implementação via IA + Test Harness)

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

## Versionamento

Git Flow simplificado:

- `main` — sempre estável; recebe apenas releases vindas de `develop`.
- `develop` — integração do trabalho aprovado.
- `feature/*` — um incremento por branch (ex.: `feature/sdd-specification`,
  `feature/test-harness`, `feature/task-analyzer-impl`).

Commits seguem o padrão `tipo: descrição` (`feat`, `fix`, `test`, `docs`, `refactor`, `chore`), e o
corpo registra o que foi gerado por IA e o que foi corrigido manualmente. Entregas são marcadas com
tags (`v1.0-fase2`, `v2.0-fase3`).
