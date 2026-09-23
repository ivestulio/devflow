"""No de fechamento: monta o dossie."""

from src.observability.logging import log
from src.schemas.dossie import Dossie
from src.schemas.revisao import DecisaoHumana
from src.state import EstadoDevFlow

_logger = log("dossie")


def finalizar(estado: EstadoDevFlow) -> dict:
    """Junta issue, triagem, plano e decisao no entregavel final."""
    decisao = estado.decisao or DecisaoHumana(acao="aprovar", revisor="sistema")

    dossie = Dossie.montar(
        issue=estado.issue,
        triagem=estado.triagem,
        plano=estado.plano,
        decisao=decisao,
        contexto=estado.contexto,
        alertas=estado.alertas,
        revisoes=estado.revisoes,
    )

    _logger.info("dossie de %s gerado com %d fonte(s)", estado.issue.id, len(dossie.fontes))
    return {"dossie": dossie}
