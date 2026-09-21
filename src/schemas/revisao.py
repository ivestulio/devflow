"""Contrato da pausa humana."""

from typing import Literal

from pydantic import BaseModel

# Cada acao corresponde a exatamente um caminho no grafo.
PROXIMO_NO = {"aprovar": "finalizar", "revisar": "planejar", "rejeitar": "encerrar"}


class DecisaoHumana(BaseModel):
    """O que a pessoa revisora respondeu quando o grafo pausou."""

    acao: Literal["aprovar", "revisar", "rejeitar"]
    comentario: str = ""
    revisor: str = "humano"
