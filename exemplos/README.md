# Exemplos para testar no Studio

Cole o conteudo de um arquivo no campo de entrada do LangGraph Studio e execute.

| Arquivo | O que exercita | Precisa de credencial Azure? |
|---|---|---|
| `01-cupom-duplicado.json` | Caminho completo: o modelo consulta a base, classifica, planeja e pausa para revisao | sim |
| `02-typo-trivial.json` | RAG seletivo na pratica: issue simples demais para justificar busca, dossie sai com alerta de fontes vazias | sim |
| `03-injecao-bloqueada.json` | Guardrail de entrada barra a injecao e encerra **sem chamar o modelo** | **nao** |
| `04-segredo-e-pii.json` | Chave de API, e-mail, CPF e telefone mascarados; o fluxo segue | sim (mas o mascaramento ja e visivel no estado do no `guardrail`) |

## Respondendo a pausa

Quando o grafo pausa em `revisao_humana`, responda com uma destas acoes:

```json
{"acao": "aprovar", "revisor": "ives"}
```

```json
{"acao": "revisar", "comentario": "detalhar o rollback do passo 2", "revisor": "ives"}
```

```json
{"acao": "rejeitar", "comentario": "duplicada da ISSUE-1042", "revisor": "ives"}
```

`revisar` volta so ao planejamento, preservando triagem e contexto, e pausa de novo.
Depois de 3 revisoes o fluxo encerra sem dossie.
