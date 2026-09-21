"""Guardrail de saida: confere o que o modelo devolveu.

Tudo aqui e deterministico - teoria de conjuntos e comparacao de tabela, sem
segundo LLM julgando o primeiro. Os alertas nao bloqueiam: viram a lista que a
pessoa revisora enxerga no momento de decidir aprovar ou pedir revisao.
"""

from typing import List, Optional

from src.schemas.issue import Issue
from src.schemas.plano import Plano
from src.schemas.triagem import PRIORIDADE_ESPERADA, Triagem

# Trechos do prompt de sistema que nao aparecem numa justificativa legitima.
# Se o modelo os ecoa, alguem conseguiu extrair a instrucao interna.
MARCAS_DO_SISTEMA = [
    "voce e o devflow",
    "classifique a issue usando exclusivamente",
    "o plano deve ser executavel",
    "em `fontes`, liste os ids",
]


def vazou(texto: str) -> bool:
    """Detecta eco do prompt de sistema na resposta do modelo."""
    baixo = texto.lower()
    return any(marca in baixo for marca in MARCAS_DO_SISTEMA)


def conferir_triagem(triagem: Triagem, contexto: List[dict]) -> List[str]:
    """Coerencia da classificacao e aterramento das citacoes."""
    alertas: List[str] = []
    ids = {t["id"] for t in contexto}

    esperada = PRIORIDADE_ESPERADA[triagem.severidade]
    if triagem.prioridade != esperada:
        alertas.append(
            f"prioridade incoerente: severidade `{triagem.severidade}` pede `{esperada}`, "
            f"veio `{triagem.prioridade}`"
        )

    inventadas = [f for f in triagem.fontes if f not in ids]
    if inventadas:
        alertas.append(f"triagem cita fonte inexistente: {', '.join(inventadas)}")

    if not triagem.fontes:
        alertas.append("triagem sem fontes: o modelo classificou sem consultar a base")

    if vazou(triagem.justificativa):
        alertas.append("a justificativa ecoa o prompt de sistema (possivel vazamento)")

    return alertas


def conferir_plano(plano: Plano, issue: Issue, contexto: List[dict]) -> List[str]:
    """Cobertura dos criterios de aceite e aterramento das citacoes."""
    alertas: List[str] = []
    ids = {t["id"] for t in contexto}

    esperados = set(issue.ids_criterios())
    cobertos = {ca for passo in plano.passos for ca in passo.criterios_atendidos}

    faltando = sorted(esperados - cobertos)
    if faltando:
        alertas.append(f"criterios de aceite sem passo que os cubra: {', '.join(faltando)}")

    fantasmas = sorted(cobertos - esperados)
    if fantasmas:
        alertas.append(f"o plano cita criterio que a issue nao tem: {', '.join(fantasmas)}")

    inventadas = [f for f in plano.fontes if f not in ids]
    if inventadas:
        alertas.append(f"plano cita fonte inexistente: {', '.join(inventadas)}")

    if not plano.fontes:
        alertas.append("plano sem fontes: o modelo planejou sem consultar a base")

    return alertas


def conferir(
    issue: Issue,
    contexto: List[dict],
    triagem: Optional[Triagem],
    plano: Optional[Plano],
) -> List[str]:
    """Roda tudo que ja e possivel conferir com o que existe no estado."""
    alertas: List[str] = []
    if triagem is not None:
        alertas += conferir_triagem(triagem, contexto)
    if plano is not None:
        alertas += conferir_plano(plano, issue, contexto)
    return alertas
