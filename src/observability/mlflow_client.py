"""Conexao com o MLflow.

`mlflow.langchain.autolog()` ja cobre o LangGraph: nao existe um
`mlflow.langgraph.autolog()`, a integracao e a mesma e cada no do grafo vira um span.
"""

import mlflow

from src.config import settings
from src.observability.logging import log
from src.observability.tracing import ativar

_logger = log("mlflow")


def configurar_mlflow() -> None:
    """Liga o tracing. Silencioso se o MLflow nao estiver configurado."""
    if not settings.mlflow_tracking_uri:
        _logger.info("MLFLOW_TRACKING_URI vazio: seguindo sem tracing")
        return

    try:
        mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
        mlflow.set_experiment(settings.mlflow_experiment)
        mlflow.langchain.autolog()
        ativar()
        _logger.info("tracing ativo em %s (experimento: %s)", settings.mlflow_tracking_uri, settings.mlflow_experiment)
    except Exception as erro:  # observabilidade nunca derruba o agente
        _logger.warning("nao foi possivel ligar o MLflow: %s", erro)
