"""Logging estruturado. Um formato so, para o log do agente ser legivel no terminal."""

import logging
import sys

FORMATO = "%(asctime)s %(levelname)-7s %(name)-22s %(message)s"


def configurar_logs(nivel: int = logging.INFO) -> None:
    raiz = logging.getLogger()
    if raiz.handlers:  # o servidor recarrega o modulo; nao empilhar handler
        return
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter(FORMATO, datefmt="%H:%M:%S"))
    raiz.addHandler(handler)
    raiz.setLevel(nivel)
    logging.getLogger("langchain_core.callbacks.manager").addFilter(_SemRuidoDoTracer())


class _SemRuidoDoTracer(logging.Filter):
    """Descarta um aviso barulhento e inofensivo do tracer do MLflow.

    O LangGraph 1.x emite os callbacks `on_interrupt`/`on_resume` a cada pausa
    humana, e o `MlflowLangchainTracer` do MLflow 3.16 ainda nao os implementa -
    entao cada pausa gera dois AttributeError no log. O trace e gravado
    normalmente; e so ruido. Quando o MLflow implementar, este filtro vira inocuo.
    """

    def filter(self, registro: logging.LogRecord) -> bool:
        texto = registro.getMessage()
        return not ("MlflowLangchainTracer" in texto and "on_interrupt" in texto or
                    "MlflowLangchainTracer" in texto and "on_resume" in texto)


def log(nome: str) -> logging.Logger:
    return logging.getLogger(f"devflow.{nome}")
