"""Subgrafo de raciocinio: triagem e planejamento, cada um com seu loop de RAG.

Como o modelo escolhe buscar
----------------------------
Em cada etapa o modelo recebe DUAS ferramentas: a busca na base e o proprio
contrato de saida (`Triagem` ou `Plano`). Com `tool_choice="any"` ele e obrigado a
chamar uma das duas - ou busca mais contexto, ou entrega a resposta final. O loop
termina quando ele escolhe responder. Nao ha aresta fixa mandando buscar: a decisao
e dele, e por isso uma issue trivial pode ser classificada sem consulta nenhuma.

Reentrada pela acao `revisar`
-----------------------------
Subgrafo so pode ser entrado pelo inicio, mas `revisar` precisa voltar direto a
`planejar`. A aresta condicional a partir do START resolve: se ja existe plano e ha
feedback, a entrada pula a triagem. Triagem e contexto ficam preservados.
"""

from typing import Literal

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import END, START, StateGraph

from src.guardrails.saida import conferir_plano, conferir_triagem
from src.observability.logging import log
from src.prompts.plano import SISTEMA_PLANO, prompt_plano
from src.prompts.triagem import SISTEMA_TRIAGEM, prompt_triagem
from src.schemas.plano import Plano
from src.schemas.triagem import Triagem
from src.services.llm import modelo
from src.state import EstadoDevFlow
from src.tools.rag import (
    buscar_base_de_conhecimento,
    formatar_contexto,
    juntar_sem_duplicar,
    recuperar_seletivo,
)

BUSCA = "buscar_base_de_conhecimento"


# --- entrada condicional -----------------------------------------------------

def entrada(estado: EstadoDevFlow) -> Literal["triar", "planejar"]:
    """Na revisao, entra direto no planejamento e preserva a triagem.

    A condicao olha a TRIAGEM, nao o plano: o no de revisao invalida o plano para
    forcar o replanejamento, entao `plano is None` nao distingue primeira passada
    de revisao. A triagem, essa sim, so existe depois da primeira passada.
    """
    return "planejar" if estado.triagem is not None else "triar"


# --- etapa de triagem --------------------------------------------------------

def _fechar_chamadas(resposta) -> list:
    """Responde TODA tool_call da resposta com uma ToolMessage.

    A API exige que toda `tool_call` tenha uma mensagem respondendo ao seu
    `tool_call_id` - inclusive a que entrega a resposta final (`Triagem`/`Plano`),
    que nao passa pelo no de busca. Sem isto o historico fica com um tool_call em
    aberto, e o replanejamento da acao `revisar` reenvia esse historico e leva 400:
    "An assistant message with 'tool_calls' must be followed by tool messages".
    """
    return [ToolMessage(content="ok", tool_call_id=c["id"]) for c in resposta.tool_calls]


def triar(estado: EstadoDevFlow) -> dict:
    novas = []
    if not estado.msgs_triagem:
        novas = [
            SystemMessage(content=SISTEMA_TRIAGEM),
            HumanMessage(content=prompt_triagem(estado.issue)),
        ]

    conversa = list(estado.msgs_triagem) + novas
    resposta = modelo().bind_tools([buscar_base_de_conhecimento, Triagem], tool_choice="any").invoke(conversa)

    saida = {}
    mensagens = novas + [resposta]

    for chamada in resposta.tool_calls:
        if chamada["name"] == "Triagem":
            triagem = Triagem.model_validate(chamada["args"])
            saida["triagem"] = triagem
            saida["alertas"] = conferir_triagem(triagem, estado.contexto)

    if "triagem" in saida:
        mensagens += _fechar_chamadas(resposta)

    saida["msgs_triagem"] = mensagens
    return saida


def rag_triagem(estado: EstadoDevFlow) -> dict:
    return _executar_busca(estado, estado.msgs_triagem, "triagem", "msgs_triagem")


def decidir_triagem(estado: EstadoDevFlow) -> Literal["rag_triagem", "planejar"]:
    return "planejar" if estado.triagem is not None else "rag_triagem"


# --- etapa de planejamento ---------------------------------------------------

def planejar(estado: EstadoDevFlow) -> dict:
    novas = []
    if not estado.msgs_plano:
        novas = [
            SystemMessage(content=SISTEMA_PLANO),
            HumanMessage(content=prompt_plano(estado.issue, estado.triagem, estado.feedback or None)),
        ]

    conversa = list(estado.msgs_plano) + novas
    resposta = modelo().bind_tools([buscar_base_de_conhecimento, Plano], tool_choice="any").invoke(conversa)

    saida = {}
    mensagens = novas + [resposta]

    for chamada in resposta.tool_calls:
        if chamada["name"] == "Plano":
            plano = Plano.model_validate(chamada["args"])
            saida["plano"] = plano
            # Os alertas da rodada sao recalculados do zero: numa revisao, o que
            # foi corrigido precisa sumir da lista, nao se somar a ela.
            saida["alertas"] = conferir_triagem(estado.triagem, estado.contexto) + conferir_plano(
                plano, estado.issue, estado.contexto
            )

    if "plano" in saida:
        mensagens += _fechar_chamadas(resposta)

    saida["msgs_plano"] = mensagens
    return saida


def rag_plano(estado: EstadoDevFlow) -> dict:
    return _executar_busca(estado, estado.msgs_plano, "planejamento", "msgs_plano")


def decidir_plano(estado: EstadoDevFlow) -> Literal["rag_plano", "__end__"]:
    return END if estado.plano is not None else "rag_plano"


# --- execucao da ferramenta --------------------------------------------------

def _executar_busca(estado: EstadoDevFlow, mensagens: list, tarefa: str, canal: str) -> dict:
    """Roda a busca que o modelo pediu e devolve o resultado como ToolMessage."""
    ultima = mensagens[-1]
    contexto = list(estado.contexto)
    respostas = []

    for chamada in ultima.tool_calls:
        if chamada["name"] != BUSCA:
            continue

        consulta = chamada["args"]["consulta"]
        mantidos, descartados = recuperar_seletivo(consulta, chamada["args"].get("tarefa", tarefa))
        # Log em vez de span do MLflow: o no roda em thread, e um span aberto aqui
        # viraria um trace solto. O `contexto` devolvido ja entra no trace pelo autolog.
        log("rag").info(
            "%s: %r -> %d mantido(s), %d podado(s)", tarefa, consulta[:60], len(mantidos), len(descartados)
        )

        contexto = juntar_sem_duplicar(contexto, mantidos)
        texto = formatar_contexto(mantidos) if mantidos else "Nenhum trecho relevante encontrado."
        respostas.append(ToolMessage(content=texto, tool_call_id=chamada["id"]))

    return {canal: respostas, "contexto": contexto}


# --- montagem ----------------------------------------------------------------

def construir_raciocinio():
    grafo = StateGraph(EstadoDevFlow)

    grafo.add_node("triar", triar)
    grafo.add_node("rag_triagem", rag_triagem)
    grafo.add_node("planejar", planejar)
    grafo.add_node("rag_plano", rag_plano)

    grafo.add_conditional_edges(START, entrada, ["triar", "planejar"])
    grafo.add_conditional_edges("triar", decidir_triagem, ["rag_triagem", "planejar"])
    grafo.add_edge("rag_triagem", "triar")
    grafo.add_conditional_edges("planejar", decidir_plano, ["rag_plano", END])
    grafo.add_edge("rag_plano", "planejar")

    return grafo.compile()
