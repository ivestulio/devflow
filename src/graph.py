"""Grafo do DevFlow.

    issue -> guardrail -+-(bloqueado)-------------------> encerrar -> fim
                        |
                        +-(ok)-> raciocinio -> revisao_humana (pausa)
                                     ^              |
                                     |              +- aprovar  -> finalizar -> fim
                                     +--- revisar --+
                                                    +- rejeitar -> encerrar  -> fim

Todos os imports sao absolutos (`src.x`). O servidor do LangGraph carrega este
arquivo como um modulo sem pacote pai, entao import relativo aqui falharia.

Os nos sao funcoes sincronas de proposito: o LangGraph as roda numa thread,
fora do event loop. Declara-las `async def` mantendo dentro os clientes sincronos
do Azure colocaria I/O bloqueante no loop.
"""

from langgraph.graph import END, START, StateGraph

from src.edges.roteadores import rotear_guardrail, rotear_revisao
from src.nodes.encerrar import encerrar
from src.nodes.finalizar import finalizar
from src.nodes.guardrail import guardrail_entrada
from src.nodes.revisao_humana import revisao_humana
from src.observability import configurar
from src.state import Entrada, EstadoDevFlow
from src.subgraphs.raciocinio import construir_raciocinio

configurar()


def build_graph() -> StateGraph:
    """Monta o grafo sem compilar, para quem quiser escolher o checkpointer."""
    grafo = StateGraph(EstadoDevFlow, input_schema=Entrada)

    grafo.add_node("guardrail", guardrail_entrada)
    grafo.add_node("raciocinio", construir_raciocinio())
    grafo.add_node("revisao_humana", revisao_humana)
    grafo.add_node("finalizar", finalizar)
    grafo.add_node("encerrar", encerrar)

    grafo.add_edge(START, "guardrail")
    grafo.add_conditional_edges("guardrail", rotear_guardrail, ["raciocinio", "encerrar"])
    grafo.add_edge("raciocinio", "revisao_humana")
    grafo.add_conditional_edges("revisao_humana", rotear_revisao, ["finalizar", "raciocinio", "encerrar"])
    grafo.add_edge("finalizar", END)
    grafo.add_edge("encerrar", END)

    return grafo


# Sem checkpointer: o servidor do LangGraph injeta a propria persistencia, e
# passar uma aqui faz `langgraph dev` falhar ao carregar o grafo.
# Fora do servidor, use: build_graph().compile(checkpointer=InMemorySaver())
graph = build_graph().compile(name="devflow")
