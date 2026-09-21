"""Prompt da etapa de planejamento."""

from typing import Optional

from src.prompts.base import ENVELOPE, REGRA_CONCISAO, REGRA_FONTES, formatar_issue
from src.schemas.issue import Issue
from src.schemas.triagem import Triagem

SISTEMA_PLANO = f"""Voce e o DevFlow, um agente que transforma uma issue triada em plano tecnico.
O plano deve ser executavel por outra pessoa desenvolvedora sem contexto adicional.
Cada criterio de aceite (CA1, CA2, ...) precisa aparecer em `criterios_atendidos` de
pelo menos um passo - essa cobertura e verificada automaticamente.
Ao propor nome de arquivo, de flag ou de metrica que voce nao viu na base, marque
explicitamente como sugestao a validar e registre a dependencia em `riscos`.

{REGRA_FONTES}

{ENVELOPE}

{REGRA_CONCISAO}"""


def prompt_plano(issue: Issue, triagem: Triagem, feedback: Optional[str] = None) -> str:
    partes = [
        formatar_issue(issue),
        f"TRIAGEM JA FEITA\n{triagem.model_dump_json(indent=2)}",
    ]
    if feedback:
        partes.append(
            f"FEEDBACK A INCORPORAR\n{feedback}\n"
            "Este e um replanejamento: corrija especificamente os pontos acima."
        )
    partes.append(
        "Produza o plano tecnico. IDs de criterio disponiveis: " + ", ".join(issue.ids_criterios())
    )
    return "\n\n".join(partes)
