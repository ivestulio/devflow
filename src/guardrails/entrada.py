"""Guardrail de entrada: roda antes de gastar qualquer token.

Duas estrategias distintas de proposito, porque os riscos sao diferentes:

- **Segredo e PII sao mascarados** e o fluxo segue. Uma issue com uma chave colada
  por engano continua sendo uma issue legitima; o que nao pode e a chave atravessar
  o agente e acabar no dossie.

- **Injecao bloqueia.** Nao ha como "limpar" uma tentativa de reescrever o
  comportamento do agente: o texto inteiro esta sob suspeita. O grafo encerra sem
  chamar o modelo.
"""

from typing import List, Literal, Tuple

from pydantic import BaseModel, Field

from src.guardrails import padroes
from src.schemas.issue import Issue


class Violacao(BaseModel):
    tipo: Literal["segredo", "injecao", "pii"]
    padrao: str
    campo: str

    def descrever(self) -> str:
        return f"{self.tipo}/{self.padrao} em `{self.campo}`"


class VeredictoEntrada(BaseModel):
    bloqueado: bool = False
    violacoes: List[Violacao] = Field(default_factory=list)
    issue: Issue

    def resumo(self) -> List[str]:
        return [v.descrever() for v in self.violacoes]


def _varrer(texto: str, campo: str) -> Tuple[str, List[Violacao]]:
    """Mascara segredo e PII no texto; so reporta injecao, sem alterar."""
    achados: List[Violacao] = []
    limpo = texto

    for nome, regex in padroes.SEGREDO:
        if regex.search(limpo):
            achados.append(Violacao(tipo="segredo", padrao=nome, campo=campo))
            limpo = regex.sub(padroes.MASCARA["segredo"], limpo)

    for nome, regex in padroes.PII:
        if regex.search(limpo):
            achados.append(Violacao(tipo="pii", padrao=nome, campo=campo))
            limpo = regex.sub(padroes.MASCARA["pii"], limpo)

    # Injecao casa no texto normalizado, mas nao altera o original: se houver,
    # a issue inteira e barrada e o texto limpo nem chega a ser usado.
    normalizado = padroes.normalizar(limpo)
    for nome, regex in padroes.INJECAO:
        if regex.search(normalizado):
            achados.append(Violacao(tipo="injecao", padrao=nome, campo=campo))

    return limpo, achados


def analisar(issue: Issue) -> VeredictoEntrada:
    """Analisa todo campo de texto livre da issue."""
    violacoes: List[Violacao] = []

    titulo, achados = _varrer(issue.titulo, "titulo")
    violacoes += achados

    descricao, achados = _varrer(issue.descricao, "descricao")
    violacoes += achados

    criterios = []
    for i, criterio in enumerate(issue.criterios_aceite, start=1):
        limpo, achados = _varrer(criterio, f"criterios_aceite[{i}]")
        violacoes += achados
        criterios.append(limpo)

    bloqueado = any(v.tipo == "injecao" for v in violacoes)

    return VeredictoEntrada(
        bloqueado=bloqueado,
        violacoes=violacoes,
        issue=issue.model_copy(update={"titulo": titulo, "descricao": descricao, "criterios_aceite": criterios}),
    )
