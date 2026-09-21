"""Decisoes de caminho do grafo principal."""

from typing import Literal

from src.schemas.revisao import PROXIMO_NO
from src.state import MAX_REVISOES, EstadoDevFlow

# `revisar` volta ao subgrafo de raciocinio, que por sua vez entra direto em
# `planejar`. Do ponto de vista do grafo de cima, o destino e o subgrafo.
DESTINOS = {"finalizar": "finalizar", "planejar": "raciocinio", "encerrar": "encerrar"}


def rotear_guardrail(estado: EstadoDevFlow) -> Literal["raciocinio", "encerrar"]:
    """Injecao encerra o fluxo sem chamar o modelo."""
    return "encerrar" if estado.bloqueado else "raciocinio"


def rotear_revisao(estado: EstadoDevFlow) -> Literal["finalizar", "raciocinio", "encerrar"]:
    """Aplica a decisao humana, respeitando o teto de revisoes.

    O teto e indispensavel: o limite de recursao do LangGraph e reconcedido por
    inteiro a cada retomada, entao ele nunca limita um loop no ritmo de uma pessoa.
    """
    if estado.decisao is None:
        return "encerrar"

    if estado.decisao.acao == "revisar" and estado.revisoes >= MAX_REVISOES:
        return "encerrar"

    return DESTINOS[PROXIMO_NO[estado.decisao.acao]]
