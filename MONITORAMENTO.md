# Monitoramento com MLflow

Como a observabilidade do DevFlow está implementada, o que ela captura e por que foi feita assim.

Todos os números e estruturas deste documento vieram de traces reais do experimento `devflow` —
não são exemplos inventados.

## Resumo

A implementação inteira cabe em **uma chamada**:

```python
mlflow.langchain.autolog()
```

Não existe `mlflow.langgraph.autolog()`. A integração do LangChain já cobre o LangGraph: cada nó do
grafo vira um span, e o **retorno do nó é gravado como saída do span**. É daí que vem praticamente
tudo o que você vê no trace.

Três arquivos, nenhum deles grande:

| Arquivo | Papel |
|---|---|
| [`src/observability/__init__.py`](src/observability/__init__.py) | `configurar()` — roda uma vez, no import de `src/graph.py` |
| [`src/observability/mlflow_client.py`](src/observability/mlflow_client.py) | conecta, escolhe o experimento, liga o autolog |
| [`src/observability/logging.py`](src/observability/logging.py) | log estruturado e um filtro de ruído |

## Como ligar

```bash
uv run mlflow server --host 127.0.0.1 --port 5001 --backend-store-uri sqlite:///mlflow.db
```

No `.env`:

```
MLFLOW_TRACKING_URI=http://127.0.0.1:5001
MLFLOW_EXPERIMENT=devflow
```

Reinicie o `langgraph dev` — o `.env` só é lido na subida do processo. Confirme no log:

```
tracing ativo em http://127.0.0.1:5001 (experimento: devflow)
```

Se o tracing não estiver configurado, o agente diz `MLFLOW_TRACKING_URI vazio: seguindo sem tracing`
e **continua funcionando**. A conexão é embrulhada em `try/except`: observabilidade fora do ar nunca
derruba o agente.

> Use a porta **5001**. No macOS a 5000 é ocupada pelo AirPlay Receiver, que responde `403` a tudo —
> o `curl` parece funcionar e o MLflow falha. Confira com `lsof -nP -iTCP:5000 -sTCP:LISTEN`.

## O que um trace contém

Um trace real de uma issue completa: **22 spans, 31,2 s**.

```
devflow                                   31258ms
├── guardrail                                 1ms
│   └── rotear_guardrail                      0ms
├── raciocinio                             31238ms
│   └── LangGraph                          31237ms
│       ├── __start__                          1ms
│       │   └── entrada                        0ms
│       ├── triar                           3922ms
│       │   ├── AzureChatOpenAI  [CHAT_MODEL] 3887ms
│       │   └── decidir_triagem                0ms
│       ├── rag_triagem                     2659ms   ← o modelo pediu a busca
│       ├── triar                           4048ms   ← e voltou para classificar
│       │   ├── AzureChatOpenAI  [CHAT_MODEL] 4042ms
│       │   └── decidir_triagem                1ms
│       ├── planejar                        3867ms
│       │   ├── AzureChatOpenAI  [CHAT_MODEL] 3864ms
│       │   └── decidir_plano                  0ms
│       ├── rag_plano                       2854ms   ← pediu de novo, agora para planejar
│       └── planejar                       13874ms
│           ├── AzureChatOpenAI [CHAT_MODEL] 13868ms
│           └── decidir_plano                  0ms
└── revisao_humana                              4ms
```

**A árvore conta a história do RAG seletivo.** `triar` aparece duas vezes com `rag_triagem` no meio:
na primeira o modelo decidiu buscar, na segunda classificou com o que recebeu. O mesmo em
`planejar`. Se o modelo tivesse respondido de primeira, o nó apareceria **uma vez só** — e é assim
que se enxerga, no trace, a escolha dele.

Note também que `revisao_humana` dura 4 ms: o trace fecha quando o grafo pausa. O tempo que a pessoa
leva para decidir não entra na duração.

## Métricas capturadas

### Token e custo

Agregados no nível do trace, sem nenhum código nosso:

```python
trace.info.token_usage
# {'input_tokens': 8283, 'output_tokens': 1649,
#  'total_tokens': 9932, 'cache_read_input_tokens': 1280}
```

Por chamada, no span do modelo:

```python
span.attributes["mlflow.chat.tokenUsage"]
# {'input_tokens': 1167, 'output_tokens': 162, 'total_tokens': 1329, 'cache_read_input_tokens': 0}

span.attributes["mlflow.llm.cost"]
# {'input_cost': 0.0029175, 'output_cost': 0.00243, 'total_cost': 0.0053475}
```

O **custo é calculado pelo MLflow**, a partir do modelo e da contagem de tokens. Não configuramos
tabela de preço.

### Identificação do modelo

```python
span.attributes["mlflow.llm.model"]     # 'gpt-5.4'
span.attributes["mlflow.llm.provider"]  # 'azure'
```

### As ferramentas oferecidas ao modelo

```python
span.attributes["mlflow.chat.tools"]
# buscar_base_de_conhecimento, Triagem
```

Isto é mais útil do que parece: mostra que o modelo recebeu **duas** ferramentas — a busca e o
próprio contrato de saída — que é o mecanismo pelo qual ele escolhe entre buscar mais e responder.

### Latência

Cada span traz início e fim. A árvore acima já é o perfil de desempenho: dá para ver que o segundo
`planejar` levou 13,9 s dos 31,2 s totais.

## Onde caem as checagens de qualidade

As verificações do guardrail de saída ([`src/guardrails/saida.py`](src/guardrails/saida.py)) —
fonte inventada, cobertura de critério de aceite, coerência severidade→prioridade — são calculadas
dentro dos nós de raciocínio e **devolvidas no retorno**. Por isso entram no trace sozinhas.

Comparando os dois spans `triar` do mesmo trace:

```python
# primeira passada: o modelo só pediu a ferramenta
span `triar` outputs: ['msgs_triagem']

# segunda passada: a resposta final, com as checagens
span `triar` outputs: ['triagem', 'alertas', 'msgs_triagem']
   alertas: nenhum
   triagem: alta/P1
   fontes:  ['politica-de-engenharia#2', 'politica-de-engenharia#1', ...]
```

E o span `rag_triagem` grava o contexto recuperado, com os IDs citáveis:

```python
contexto: ['politica-de-engenharia#4', 'politica-de-engenharia#2', 'historico-incidentes#1', ...]
```

Com as fontes citadas num span e as recuperadas em outro, dá para auditar **depois da execução** se
o modelo citou algo que não recebeu.

O guardrail de entrada também aparece sozinho:

```python
span `guardrail` outputs: {'bloqueado': False, 'violacoes': []}
```

## Decisão de projeto: não há span manual

Isto é deliberado, e custou uma descoberta.

A primeira versão abria `mlflow.start_span()` dentro dos nós, para registrar o veredicto do guardrail
e a poda do RAG. **Não funcionou**: cada span virava um *trace separado*, solto na lista, em vez de
aninhar sob a execução.

A causa é o modelo de execução. O LangGraph roda cada nó síncrono **numa thread**, e o contexto de
span do OpenTelemetry é *thread-local* — o contexto do trace-pai não atravessa. `mlflow.start_span()`
sem pai visível abre uma raiz nova. `mlflow.update_current_trace()` tem o mesmo problema: as tags
iam para o trace órfão, não para o da execução.

Testei `mlflow.langchain.autolog(run_tracer_inline=True)`, citado na documentação para contextos
assíncronos. Também não aninha.

A saída foi constatar que **os spans manuais eram redundantes**: o autolog já gravava
`bloqueado` e `violacoes` como saída do span `guardrail`, porque o nó os devolve. Removi
`tracing.py` e `metrics.py`. O que não cabe no retorno do nó — como a contagem de trechos podados
pelo RAG — virou log:

```
devflow.rag  triagem: 'regra de unicidade de cupom' -> 6 mantido(s), 3 podado(s)
```

**A regra prática:** se você quer uma informação no trace, devolva-a no retorno do nó. Não tente
abrir span dentro dele.

## Por que trace e não `mlflow.log_metric`

Não há `mlflow.start_run()` no projeto, e isso também é escolha.

`log_metric` escreve num **Run**, não no span — o número não apareceria junto do trace que o
descreve. E um servidor de vida longa não tem "run" que faça sentido abrir e fechar: um run por
processo empilharia métricas de issues diferentes numa série só, sem como fatiar por issue.

Para agregar, consulte os traces:

```python
import mlflow
mlflow.set_tracking_uri("http://127.0.0.1:5001")

df = mlflow.search_traces(locations=["devflow"], max_results=100)
# colunas: trace_id, state, request_time, execution_duration, request, response, ...
```

## Aviso conhecido

```
MlflowLangchainTracer object has no attribute 'on_interrupt'
```

Incompatibilidade upstream: o LangGraph 1.x emite os callbacks `on_interrupt`/`on_resume` a cada
pausa humana, e o `MlflowLangchainTracer` do MLflow 3.16 ainda não os implementa. **É ruído** — o
trace é gravado normalmente. O projeto filtra a mensagem em
[`src/observability/logging.py`](src/observability/logging.py); quando o MLflow implementar, o filtro
fica inócuo.

## O que não é capturado

- **O tempo da revisão humana.** O trace fecha na pausa. Retomar abre um trace novo.
- **Tags de filtro por atributo de negócio.** Marcar o trace com "foi ataque" exigiria
  `update_current_trace` de dentro do nó, que não funciona pelo motivo acima. Filtre pelos dados dos
  spans.
- **Métricas agregadas prontas.** Não há painel de "ataques bloqueados por semana". Os dados estão
  nos traces; a agregação é consulta.
