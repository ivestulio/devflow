"""No de guardrail de entrada."""

from src.guardrails.entrada import analisar
from src.observability.logging import log
from src.state import EstadoDevFlow

_logger = log("guardrail")


def guardrail_entrada(estado: EstadoDevFlow) -> dict:
    """Mascara segredo e PII, bloqueia injecao. Roda antes de qualquer token.

    Sem span manual de proposito: o autolog do MLflow ja cria um span por no e
    grava o retorno abaixo como saida dele, entao `bloqueado` e `violacoes` ja
    aparecem no trace. Um `mlflow.start_span` aqui dentro criaria um trace SOLTO,
    porque o LangGraph roda o no numa thread e o contexto do span nao atravessa.
    """
    veredicto = analisar(estado.issue)

    if veredicto.bloqueado:
        _logger.warning("issue %s bloqueada: %s", estado.issue.id, veredicto.resumo())
    elif veredicto.violacoes:
        _logger.info("issue %s sanitizada: %s", estado.issue.id, veredicto.resumo())

    return {
        "issue": veredicto.issue,
        "bloqueado": veredicto.bloqueado,
        "violacoes": veredicto.resumo(),
    }
