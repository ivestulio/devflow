"""Spans manuais.

O autolog ja cria um span por no. Estes spans acrescentam o que o autolog nao
enxerga: o veredicto do guardrail e o que a poda do RAG manteve ou descartou -
que e como se ve, no trace, o modelo decidindo buscar.

Tudo aqui degrada em silencio: sem MLflow configurado, o agente roda igual.
"""

from contextlib import contextmanager

try:
    import mlflow
    from mlflow.entities import SpanType

    _IMPORTAVEL = True
except Exception:  # pragma: no cover
    _IMPORTAVEL = False

# Ligado por `configurar_mlflow()` quando ha tracking URI. Sem isso, abrir um span
# faria o MLflow criar um `mlruns/` local por conta propria - efeito colateral que
# nao se pede a quem so quer rodar o agente.
_ativo = False


def ativar() -> None:
    global _ativo
    _ativo = _IMPORTAVEL


def _disponivel() -> bool:
    return _IMPORTAVEL and _ativo


class _Recuperacao:
    """Handle devolvido pelo span de recuperacao."""

    def __init__(self, span):
        self._span = span

    def registrar(self, mantidos: list, descartados: list) -> None:
        if self._span is None:
            return
        self._span.set_outputs({"ids": [t["id"] for t in mantidos]})
        self._span.set_attributes(
            {
                "devflow.rag.mantidos": len(mantidos),
                "devflow.rag.descartados": len(descartados),
                "devflow.rag.categorias": sorted({t.get("categoria") or "?" for t in mantidos}),
            }
        )


@contextmanager
def span_recuperacao(tarefa: str, consulta: str):
    """Envolve uma chamada da ferramenta de RAG."""
    if not _disponivel():
        yield _Recuperacao(None)
        return

    try:
        with mlflow.start_span(name=f"rag_{tarefa}", span_type=SpanType.RETRIEVER) as span:
            span.set_inputs({"tarefa": tarefa, "consulta": consulta[:500]})
            yield _Recuperacao(span)
    except Exception:
        yield _Recuperacao(None)


@contextmanager
def span_guardrail(veredicto):
    """Envolve o guardrail de entrada e marca a trace inteira."""
    if not _disponivel():
        yield
        return

    try:
        with mlflow.start_span(name="guardrail_entrada", span_type=SpanType.PARSER) as span:
            tipos = sorted({v.tipo for v in veredicto.violacoes})
            span.set_outputs({"bloqueado": veredicto.bloqueado, "violacoes": veredicto.resumo()})
            span.set_attributes(
                {
                    "devflow.guardrail.bloqueado": veredicto.bloqueado,
                    "devflow.guardrail.tipos": tipos,
                    "devflow.guardrail.total": len(veredicto.violacoes),
                }
            )
            mlflow.update_current_trace(
                tags={
                    "devflow.bloqueado": str(veredicto.bloqueado).lower(),
                    "devflow.ataque": ",".join(tipos) or "nenhum",
                }
            )
            yield
    except Exception:
        yield
