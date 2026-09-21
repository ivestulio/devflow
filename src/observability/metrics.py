"""Metricas de qualidade da execucao.

Vao como TAGS da trace, nao por `mlflow.log_metric`. O motivo e concreto: isto e um
servidor de vida longa, nao um job em lote. Nao ha "run" que faca sentido abrir e
fechar por issue, e `log_metric` escreve num Run, nao no span - o numero nao
apareceria junto do trace que ele descreve.

Para agregar depois: `mlflow.search_traces(filter_string="tags.\\"devflow.bloqueado\\" = 'true'")`.
"""

from typing import List, Optional

from src.schemas.issue import Issue
from src.schemas.plano import Plano

try:
    import mlflow

    _IMPORTAVEL = True
except Exception:  # pragma: no cover
    _IMPORTAVEL = False

from src.observability.tracing import _disponivel


def cobertura_criterios(plano: Optional[Plano], issue: Issue) -> float:
    """Fracao dos criterios de aceite cobertos por algum passo do plano."""
    esperados = set(issue.ids_criterios())
    if not esperados or plano is None:
        return 0.0
    cobertos = {ca for passo in plano.passos for ca in passo.criterios_atendidos}
    return len(cobertos & esperados) / len(esperados)


def registrar_qualidade(
    *,
    issue: Issue,
    plano: Optional[Plano],
    alertas: List[str],
    fontes: List[str],
    revisoes: int,
    decisao: str,
) -> None:
    """Marca a trace com o resultado da execucao."""
    if not _disponivel():
        return
    try:
        mlflow.update_current_trace(
            tags={
                "devflow.issue": issue.id,
                "devflow.decisao": decisao,
                "devflow.revisoes": str(revisoes),
                "devflow.alertas": str(len(alertas)),
                "devflow.fontes": str(len(fontes)),
                "devflow.cobertura_ca": f"{cobertura_criterios(plano, issue):.2f}",
            }
        )
    except Exception:
        pass
