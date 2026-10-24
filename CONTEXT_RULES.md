# CONTEXT_RULES — TaskAnalyzer

Este arquivo é entregue ao assistente de IA **antes de qualquer geração de código**, em toda sessão
nova, junto com `specs/task_analyzer_spec.md`. Ele só é alterado por decisão humana, via Pull
Request.

## 1. Papel do agente

Você atua como gerador de código sob especificação. A fonte da verdade é
`specs/task_analyzer_spec.md`. Você não decide requisitos; você os implementa.

## 2. Stack obrigatória

- Python 3.11+, apenas biblioteca padrão no código de produção (`src/`).
- `pytest` e `pytest-cov` permitidos exclusivamente em `tests/`.
- Infraestrutura (seções 4.4 e 4.5 da especificação): GitHub Actions em `ubuntu-latest` com
  Python 3.11, e Docker com a imagem base `python:3.11-slim`.

## 3. Diretrizes obrigatórias

- **Linguagem:** Python 3.11 ou superior, usando apenas a biblioteca padrão.
- **Type hints** em todas as funções, métodos e atributos, incluindo retornos e tipos compostos.
- **PEP 8 e código limpo:** nomes descritivos em português para o domínio, linhas de até 100
  caracteres.
- **Single Responsibility (SRP):** cada função com um único propósito; funções curtas e coesas.
- **Docstrings no padrão Google style** para o módulo, as classes, as funções e seus parâmetros.
- **Tratamento de exceções específico**, derivado de `TaskAnalyzerError`, com mensagens claras em
  português citando o `id_tarefa` quando aplicável.
- **Logs estruturados** com o módulo padrão `logging`: `INFO` para início e fim da análise,
  `WARNING` para prioridades sem dados, `ERROR` antes de levantar exceções. Nunca `print`.
- **Estruturas de dados imutáveis** para entrada e saída: `@dataclass(frozen=True)` para `Tarefa`,
  `IndicadorPrioridade` e `RelatorioProdutividade`.
- **Separação entre validação e cálculo:** validar todo o conjunto antes de iniciar qualquer
  cálculo.
- **Determinismo:** a mesma entrada sempre produz a mesma saída, sem dependência de relógio,
  ambiente ou ordem de iteração.

## 4. Proibições

- Não utilizar bibliotecas externas não autorizadas (pandas, numpy, dateutil, pydantic e similares
  estão proibidos no código de produção).
- Não alterar, remover, renomear ou adaptar os cenários de teste nem o arquivo
  `tests/test_harness.py`.
- Não modificar a estrutura de pastas definida na seção 4.1 da especificação.
- Não persistir dados em arquivos, bancos de dados, variáveis globais ou caches.
- Não alterar a assinatura (nome ou parâmetros) da função pública `analisar_tarefas` sem
  autorização explícita.
- Não gerar código sem os testes correspondentes para novas funcionalidades.
- Não inserir código duplicado, morto ou sem necessidade comprovada.
- Não assumir comportamentos não especificados no contrato — em caso de ambiguidade, perguntar
  antes de implementar.
- Não retornar valores fora do contrato definido na seção 1.3.3, nem inventar campos adicionais.
- Não capturar exceções de forma genérica (`except Exception`) nem silenciar erros.
- Não acessar rede, sistema de arquivos, variáveis de ambiente ou o relógio do sistema.
- Não comentar código em excesso — comentários apenas onde a intenção não é evidente pelo nome.

### 4.1 Proibições de infraestrutura

- Não enfraquecer o pipeline nem o contêiner para obter uma execução verde: nada de pular,
  desmarcar ou filtrar testes (`-k`, `--deselect`, `skip`), reduzir a meta de cobertura, usar
  `continue-on-error` ou mascarar falhas com `|| true`.
- Não instalar dependências fora do `requirements.txt`, nem no pipeline nem na imagem.
- Não trocar a imagem base `python:3.11-slim` nem executar o contêiner como root.
- Não ampliar as permissões do workflow além de `contents: read`, nem incluir segredos, tokens ou
  credenciais em qualquer arquivo do repositório.
- Não editar à mão `specs/system_design_document.pdf` nem `specs/requirements.yaml`: ambos são
  regenerados a partir de `specs/task_analyzer_spec.md`.

## 5. Protocolo de dúvida

Em caso de ambiguidade, **PARE e pergunte**. Não preencha lacunas por conta própria.

## 6. Regras de interação (para o humano que conduz a sessão)

1. Fornecer sempre o contexto completo antes da solicitação: este arquivo e
   `specs/task_analyzer_spec.md` em toda sessão nova.
2. Validar se a IA compreendeu o contrato antes de pedir código — pedir que ela resuma as regras
   com as próprias palavras.
3. Solicitar explicações sempre que houver dúvida sobre uma decisão de implementação.
4. Revisar criticamente todo código gerado, linha a linha.
5. Rejeitar qualquer resposta que viole uma proibição da seção 4, ainda que funcione, e pedir nova
   geração citando a regra violada.
6. Trabalhar em incrementos pequenos: uma função ou um cenário por vez, validando com o harness a
   cada passo.
7. Registrar nos commits e Pull Requests quais trechos foram gerados por IA e quais foram escritos
   ou corrigidos manualmente.

## 7. Definição de pronto

Código pronto = todos os testes de `tests/test_harness.py` passando, sem alteração do harness, com
cobertura ≥ 90% e conformidade integral com as seções 3 e 4 deste arquivo.

Infraestrutura pronta = pipeline de CI verde no Pull Request e a mesma suíte aprovada dentro do
contêiner com `docker compose run --rm tests`.
