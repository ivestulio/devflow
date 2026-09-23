"""Conexao com o MLflow.

`mlflow.langchain.autolog()` ja cobre o LangGraph: nao existe um
`mlflow.langgraph.autolog()`, a integracao e a mesma e cada no do grafo vira um span,
com o retorno do no gravado como saida do span.

Nao ha span manual no projeto, e isso e deliberado. O LangGraph roda cada no
sincrono numa thread, e o contexto de span do OpenTelemetry e thread-local: um
`mlflow.start_span()` dentro de um no NAO aninha sob o trace da execucao - vira um
trace solto e separado, poluindo a lista. O mesmo vale para
`mlflow.update_current_trace()`. Como o autolog ja grava o retorno de cada no, a
informacao que importa ja esta no trace; o que nao cabe no retorno vira log.
"""

import mlflow

from src.config import settings
from src.observability.logging import log

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
        _logger.info("tracing ativo em %s (experimento: %s)", settings.mlflow_tracking_uri, settings.mlflow_experiment)
    except Exception as erro:  # observabilidade nunca derruba o agente
        _logger.warning("nao foi possivel ligar o MLflow: %s", erro)
