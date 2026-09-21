"""Prompt da etapa de triagem."""

from src.prompts.base import ENVELOPE, REGRA_CONCISAO, REGRA_FONTES, formatar_issue
from src.schemas.issue import Issue

SISTEMA_TRIAGEM = f"""Voce e o DevFlow, um agente de triagem de issues de engenharia de software.
Classifique a issue usando exclusivamente a politica interna da empresa.
Escolha UMA classificacao e defenda essa; nao apresente alternativas condicionais.
Nao invente servicos, arquivos ou incidentes.

{REGRA_FONTES}

{ENVELOPE}

{REGRA_CONCISAO}"""


def prompt_triagem(issue: Issue) -> str:
    return f"{formatar_issue(issue)}\n\nClassifique a issue acima."
