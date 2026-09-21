"""Estado do grafo.

Duas decisoes aqui nao sao obvias e foram tomadas a partir de teste, nao de intuicao:

1. `contexto` NAO tem reducer. Com `operator.add`, a reentrada no subgrafo pela acao
   `revisar` reconcatenava a lista e as fontes do dossie saiam duplicadas. A juncao
   com dedupe acontece dentro do no de ferramenta.

2. As mensagens ficam em DOIS canais, um por etapa. Com uma lista so, o planejamento
   herdaria toda a conversa da triagem: tokens desperdicados e risco de eco. Limpar a
   lista no meio exigiria `RemoveMessage`, complexidade sem retorno.
"""

from typing import Annotated, List, Optional

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field

from src.schemas.dossie import Dossie
from src.schemas.issue import Issue
from src.schemas.plano import Plano
from src.schemas.revisao import DecisaoHumana
from src.schemas.triagem import Triagem

# Teto de idas e voltas na revisao. Necessario: o limite de recursao do LangGraph e
# 10007 e e reconcedido por inteiro a cada retomada humana, entao ele nunca limita
# um loop no ritmo de uma pessoa. Sem este teto, `revisar` gira para sempre.
MAX_REVISOES = 3


class Entrada(BaseModel):
    """Schema de entrada do grafo: e so isto que o Studio pede."""

    issue: Issue


class EstadoDevFlow(BaseModel):
    """Estado completo, carregado de no em no."""

    issue: Issue

    # guardrail de entrada
    bloqueado: bool = False
    violacoes: List[str] = Field(default_factory=list)

    # contexto recuperado pela ferramenta de RAG (sem reducer, ver nota acima)
    contexto: List[dict] = Field(default_factory=list)

    # raciocinio
    msgs_triagem: Annotated[List[AnyMessage], add_messages] = Field(default_factory=list)
    msgs_plano: Annotated[List[AnyMessage], add_messages] = Field(default_factory=list)
    triagem: Optional[Triagem] = None
    plano: Optional[Plano] = None

    # verificacoes do guardrail de saida, mostradas na pausa humana
    alertas: List[str] = Field(default_factory=list)

    # revisao humana
    decisao: Optional[DecisaoHumana] = None
    feedback: str = ""
    revisoes: int = 0

    # saida
    dossie: Optional[Dossie] = None
    encerrado_por: str = ""
