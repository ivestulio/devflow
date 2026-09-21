"""No de guardrail de entrada."""

from src.guardrails.entrada import analisar
from src.observability.logging import log
from src.observability.tracing import span_guardrail
from src.state import EstadoDevFlow

_logger = log("guardrail")


def guardrail_entrada(estado: EstadoDevFlow) -> dict:
    """Mascara segredo e PII, bloqueia injecao. Roda antes de qualquer token."""
    veredicto = analisar(estado.issue)

    with span_guardrail(veredicto):
        if veredicto.bloqueado:
            _logger.warning("issue %s bloqueada: %s", estado.issue.id, veredicto.resumo())
        elif veredicto.violacoes:
            _logger.info("issue %s sanitizada: %s", estado.issue.id, veredicto.resumo())

        return {
            "issue": veredicto.issue,
            "bloqueado": veredicto.bloqueado,
            "violacoes": veredicto.resumo(),
        }
