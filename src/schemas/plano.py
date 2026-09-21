"""Contrato de saida da etapa de planejamento."""

from typing import List

from pydantic import BaseModel, Field


class PassoPlano(BaseModel):
    """Uma etapa do plano, executavel por uma pessoa desenvolvedora."""

    ordem: int = Field(description="Posicao do passo na sequencia de execucao, comecando em 1")
    titulo: str = Field(description="Acao do passo em ate 8 palavras, comecando por verbo")
    detalhe: str = Field(description="O que fazer e onde (arquivo, modulo ou servico), em 1 ou 2 frases")
    criterios_atendidos: List[str] = Field(
        default_factory=list,
        description="IDs dos criterios de aceite cobertos por este passo, ex.: ['CA1','CA3']",
    )


class Plano(BaseModel):
    """Plano tecnico de resolucao da issue."""

    resumo: str = Field(description="A estrategia da correcao em no maximo 2 frases")
    passos: List[PassoPlano] = Field(min_length=1, description="Etapas em ordem de execucao")
    testes: List[str] = Field(
        min_length=1,
        description="Cenarios de teste automatizado a escrever, um por item, com entrada e resultado esperado",
    )
    riscos: List[str] = Field(
        default_factory=list,
        description="O que pode dar errado ao aplicar o plano e dependencias ainda nao confirmadas",
    )
    fontes: List[str] = Field(
        default_factory=list,
        description="IDs dos trechos do contexto usados no plano, ex.: arquitetura-checkout#3",
    )
