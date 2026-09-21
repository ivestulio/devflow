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


def log(nome: str) -> logging.Logger:
    return logging.getLogger(f"devflow.{nome}")
