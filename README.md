# DevFlow

Agente de triagem e planejamento técnico de issues.

Recebe um chamado escrito por outra pessoa — título, descrição, critérios de aceite — e devolve um
**dossiê** pronto para uma pessoa desenvolvedora executar: classificação (tipo, severidade,
prioridade, esforço), plano passo a passo, e a lista de fontes internas que fundamentam cada decisão.

Projeto-âncora do curso **SkillGo Agentic Engineering**.

## O fluxo

```
issue → guardrail ─┬─(bloqueado)──────────────────────────→ encerrar → fim
                   │
                   └─(ok)→ raciocínio → revisão humana ⏸
                               ▲              │
                               │              ├─ aprovar  → finalizar → fim
                               └── revisar ───┤
                                              └─ rejeitar → encerrar  → fim
```

O nó `raciocínio` é um subgrafo com duas etapas — triagem e planejamento — e, em cada uma, um loop
de ferramenta: **o modelo decide se consulta a base de conhecimento**, com que pergunta e quantas
vezes. Uma issue trivial pode ser classificada sem consulta nenhuma (e o dossiê sai marcado como
"sem fontes").

Na ação `revisar`, o grafo reentra no subgrafo direto no planejamento: a triagem e o contexto já
recuperado são preservados, e o comentário do revisor entra na conversa como feedback.

## Como rodar

**1. Dependências** (requer Python 3.11+; o Python do sistema no macOS é 3.9):

```bash
uv sync
```

**2. Configuração:**

```bash
cp .env.example .env
```

Preencha as chaves do Azure OpenAI e do Azure AI Search. O índice `devflow-kb` já deve existir,
alimentado pelo indexador de blob sobre a pasta `kb/`.

**3. Servidor + LangGraph Studio:**

```bash
uv run langgraph dev
```

O servidor sobe em `http://127.0.0.1:2024` e imprime o link do Studio:

```
https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024
```

O Studio desenha o grafo, mostra o estado a cada nó e oferece o formulário da pausa humana. Clique
em `raciocinio` para expandir o subgrafo e ver o modelo decidindo entre buscar na base e responder.

Há issues prontas para colar em [`exemplos/`](exemplos/) — inclusive uma com injeção, que o
guardrail barra **sem chamar o modelo** e portanto roda sem credencial Azure nenhuma.

Quando o grafo pausa em `revisao_humana`, responda com uma destas ações:

```json
{"acao": "aprovar", "revisor": "ives"}
{"acao": "revisar", "comentario": "detalhar o rollback do passo 2", "revisor": "ives"}
{"acao": "rejeitar", "comentario": "duplicada da ISSUE-1042", "revisor": "ives"}
```

> **Se o Studio mostrar "Failed to initialize Studio":** é bloqueio de conteúdo misto — a página do
> Studio é HTTPS e o servidor local é HTTP. O servidor já envia
> `access-control-allow-private-network: true`, então o Chrome costuma permitir; Safari e navegadores
> mais restritos, não. A saída documentada é `uv run langgraph dev --tunnel`, que publica um túnel
> HTTPS pela Cloudflare — mas note que **o servidor não tem autenticação** (`auth of type=noop`),
> então a URL do túnel dá a qualquer pessoa acesso ao grafo e às suas credenciais Azure. Use só em
> rede confiável e derrube o túnel ao terminar.

### Para demonstrar ao vivo, use `--no-reload`

```bash
uv run langgraph dev --no-reload
```

O watcher do `langgraph dev` vigia também o `.venv/`. Qualquer coisa que reescreva pacotes ali —
um `uv sync`, um `pip install`, um `uv pip install --upgrade` — dispara uma enxurrada de reloads, e
**cada reload cancela a execução em voo** com `CancelledError`. O sintoma no Studio é a thread
travada em `Thread is in a pending state`, com a run reiniciando sem parar.

Se acontecer: cancele a run presa e reinicie sem o watcher.

```bash
curl -s -X POST "http://127.0.0.1:2024/threads/<thread_id>/runs/<run_id>/cancel?action=rollback"
```

Note que `interrupted` **não** é erro: é o estado normal de uma thread parada na revisão humana,
esperando a resposta. Preso mesmo é `busy` sem nenhuma run ativa.

### Mudou o `.env`? Reinicie o servidor

O `langgraph dev` recarrega **código** automaticamente, mas **não** variáveis de ambiente: o `.env` é
lido uma vez na subida do processo. Depois de editar, pare com `Ctrl+C` e suba de novo — sem isso o
agente continua com os valores antigos e o erro não muda, o que confunde bastante.

Mudou só arquivo em `src/`? Não precisa reiniciar, o reload cuida.

No Docker, o `.env` nem entra na imagem (de propósito — segredo não se empacota). Passe na subida:

```bash
docker build -t devflow .
docker run --rm -p 2024:2024 --env-file .env devflow
```

Trocou o `.env`? Basta subir outro contêiner com `docker run` de novo; **não** precisa rebuildar a
imagem, porque as variáveis entram em tempo de execução. Rebuild só quando mudar código ou dependência.

### Erros comuns

**`OpenAIError: Missing credentials ... set the OPENAI_API_KEY environment variable`**

A variável que falta é `AZURE_OPENAI_API_KEY`, não `OPENAI_API_KEY` — quem reclama é o SDK da OpenAI
por baixo do cliente Azure, e ele cita o nome dele. Preencha o `.env`. A partir desta versão o
DevFlow checa antes e devolve uma mensagem dizendo exatamente quais variáveis faltam.

**`ConfiguracaoAusente: Faltam variaveis no .env`**

É a checagem acima. Ela roda na criação dos clientes, não no import — de propósito: o grafo precisa
montar sem credencial para o `langgraph dev` subir, e o caminho do guardrail de entrada roda inteiro
sem chamar o modelo.

**Aviso `nao foi possivel ligar o MLflow`**

`MLFLOW_TRACKING_URI` aponta para um servidor que não está no ar. Deixe a variável vazia ou suba o
servidor. O agente funciona normalmente de qualquer forma.

### Visualizar sem o Studio

[`grafo.mmd`](grafo.mmd) tem o diagrama em Mermaid, gerado do próprio código e renderizável no
GitHub, no VS Code ou em qualquer viewer. Para regerar depois de mexer no grafo:

```bash
uv run python -c "from src.graph import graph; print(graph.get_graph(xray=1).draw_mermaid())" > grafo.mmd
```

**4. Observabilidade** (opcional):

```bash
mlflow server --host 127.0.0.1 --port 5000
```

Cada execução vira um trace com um span por nó, o veredicto do guardrail e o que a poda do RAG
manteve ou descartou.

## Sobre o RAG

O DevFlow **apenas consulta** o índice `devflow-kb` — não cria índice nem calcula embeddings. A
vetorização é feita pelo próprio Azure AI Search (vetorizador integrado, `text-embedding-3-small`,
1536 dimensões), então a consulta é enviada como **texto** via `VectorizableTextQuery`. Por isso não
há deployment de embedding no `.env`.

A recuperação é seletiva em dois sentidos: o modelo escolhe *se* busca, e a busca consulta só as
categorias pertinentes à etapa (`triagem` → política e incidentes; `planejamento` → arquitetura,
testes e runbook), podando trechos muito mais fracos que o melhor de cada categoria.

## Guardrails

**Entrada** (`src/guardrails/entrada.py`), antes de gastar qualquer token:

| Padrão | Ação | Por quê |
|---|---|---|
| Segredo (chaves de API, tokens, chave privada) | mascara e segue | a issue continua legítima; a chave é que não pode atravessar |
| PII (CPF, CNPJ, e-mail, telefone, cartão) | mascara e segue | idem |
| Injeção (ordem direta, falsa mensagem de sistema, falsa autoridade, vazamento) | **bloqueia** | não há como "limpar" uma tentativa de reescrever o comportamento |

**Saída** (`src/guardrails/saida.py`), tudo determinístico: coerência severidade→prioridade,
fontes inventadas, cobertura dos critérios de aceite, e eco do prompt de sistema. Os alertas não
bloqueiam — aparecem para a pessoa revisora no momento de decidir.

## Estrutura

```
src/
├── graph.py              grafo principal
├── state.py              estado + teto de revisões
├── config.py             leitura do .env
├── schemas/              contratos pydantic (Issue, Triagem, Plano, DecisaoHumana, Dossie)
├── guardrails/           padrões, guardrail de entrada e de saída
├── tools/rag.py          RAG seletivo exposto como ferramenta ao modelo
├── services/             cliente do Azure AI Search e do Azure OpenAI
├── prompts/              prompts de triagem e planejamento
├── nodes/                guardrail, revisão humana, finalizar, encerrar
├── edges/                roteadores
├── subgraphs/            raciocínio (triagem ⇄ RAG, planejamento ⇄ RAG)
└── observability/        MLflow, spans, métricas, logging
```

> O pacote de import chama-se `src` (a árvore de pastas é fixa). Todo import no projeto é absoluto:
> `from src.x import y`. O servidor do LangGraph carrega `src/graph.py` como módulo sem pacote pai,
> então import relativo ali falharia.

## Mapa aula → módulo

| Aula | Tema | Onde está |
|---|---|---|
| 01 | RAG, embeddings, Azure AI Search | `services/busca.py` |
| 02 | Contratos, LangGraph, raciocínio, RAG seletivo | `schemas/`, `subgraphs/`, `tools/` |
| 03 | Guardrails, human-in-the-loop | `guardrails/`, `nodes/revisao_humana.py` |
| 04 | LLMOps, MLflow, deploy | `observability/`, `Dockerfile` |
