"""Contrato de entrada: a issue que chega ao agente."""

from typing import List

from pydantic import BaseModel, Field, field_validator


class Issue(BaseModel):
    """A issue que entra no sistema, escrita por outra pessoa."""

    id: str = Field(description="Identificador unico, ex.: ISSUE-1042")
    projeto: str
    autor: str
    criada_em: str
    labels: List[str] = Field(default_factory=list)
    titulo: str = Field(min_length=5)
    descricao: str = Field(min_length=20)
    criterios_aceite: List[str] = Field(min_length=1)

    @field_validator("criterios_aceite")
    @classmethod
    def _criterios_nao_vazios(cls, valor: List[str]) -> List[str]:
        limpos = [c.strip() for c in valor if c and c.strip()]
        if not limpos:
            raise ValueError("a issue precisa de pelo menos um criterio de aceite")
        return limpos

    def criterios_numerados(self) -> List[str]:
        """Devolve os criterios prefixados com CA1, CA2... para o modelo citar."""
        return [f"CA{i}: {c}" for i, c in enumerate(self.criterios_aceite, start=1)]

    def ids_criterios(self) -> List[str]:
        return [f"CA{i}" for i in range(1, len(self.criterios_aceite) + 1)]
