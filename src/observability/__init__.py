"""Observabilidade do DevFlow.

`configurar()` roda uma vez, no import de `src.graph`. O servidor do LangGraph
importa o modulo do grafo numa thread (nao no event loop), entao a configuracao
do MLflow aqui nao bloqueia o loop.
"""

from src.observability.logging import configurar_logs, log
from src.observability.mlflow_client import configurar_mlflow

_configurado = False


def configurar() -> None:
    global _configurado
    if _configurado:
        return
    configurar_logs()
    configurar_mlflow()
    _configurado = True


__all__ = ["configurar", "log"]
