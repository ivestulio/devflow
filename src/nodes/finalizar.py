"""No de fechamento: monta o dossie."""

from src.observability.logging import log
from src.observability.metrics import registrar_qualidade
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

    registrar_qualidade(
        issue=estado.issue,
        plano=estado.plano,
        alertas=estado.alertas,
        fontes=dossie.fontes,
        revisoes=estado.revisoes,
        decisao=decisao.acao,
    )

    _logger.info("dossie de %s gerado com %d fonte(s)", estado.issue.id, len(dossie.fontes))
    return {"dossie": dossie}
