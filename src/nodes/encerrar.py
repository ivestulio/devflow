"""No terminal sem dossie: issue bloqueada, rejeitada ou com revisoes esgotadas."""

from src.observability.logging import log
from src.state import MAX_REVISOES, EstadoDevFlow

_logger = log("encerrar")


def encerrar(estado: EstadoDevFlow) -> dict:
    """Registra por que o fluxo terminou sem entregavel."""
    if estado.bloqueado:
        motivo = f"bloqueada pelo guardrail de entrada: {', '.join(estado.violacoes)}"
    elif estado.decisao is not None and estado.decisao.acao == "rejeitar":
        motivo = f"rejeitada por {estado.decisao.revisor}"
        if estado.decisao.comentario:
            motivo += f": {estado.decisao.comentario}"
    else:
        motivo = f"limite de {MAX_REVISOES} revisoes atingido sem aprovacao"

    _logger.info("issue %s encerrada sem dossie - %s", estado.issue.id, motivo)
    return {"encerrado_por": motivo}
