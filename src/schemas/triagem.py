"""Contrato de saida da etapa de triagem."""

from typing import List, Literal

from pydantic import BaseModel, Field

# A politica de engenharia amarra severidade a prioridade. Checado deterministicamente
# depois, porque e regra de negocio, nao opiniao do modelo.
PRIORIDADE_ESPERADA = {"critica": "P0", "alta": "P1", "media": "P2", "baixa": "P3"}


class Triagem(BaseModel):
    """Classificacao da issue segundo a politica de engenharia."""

    tipo: Literal["bug", "feature", "debito_tecnico", "documentacao", "suporte"] = Field(
        description="Natureza da issue: bug = comportamento incorreto de algo que ja existe; "
                    "feature = capacidade nova; debito_tecnico = melhoria interna sem mudanca visivel; "
                    "documentacao = so texto; suporte = duvida ou pedido operacional"
    )
    severidade: Literal["baixa", "media", "alta", "critica"] = Field(
        description="Gravidade do impacto, conforme a classificacao de severidade da politica no contexto"
    )
    prioridade: Literal["P0", "P1", "P2", "P3"] = Field(
        description="Urgencia de atendimento; deve seguir a correspondencia severidade -> prioridade da politica"
    )
    componentes: List[str] = Field(
        description="Servicos ou modulos afetados, usando os nomes que aparecem no contexto, ex.: pricing-service"
    )
    esforco: Literal["XS", "S", "M", "L", "XL"] = Field(
        description="Tamanho estimado do trabalho, conforme a escala de esforco da politica"
    )
    justificativa: str = Field(
        description="Por que essa classificacao, em ate 5 frases, citando a regra da politica que a sustenta"
    )
    fontes: List[str] = Field(
        default_factory=list,
        description="IDs dos trechos do contexto usados na classificacao, ex.: politica-de-engenharia#2",
    )
