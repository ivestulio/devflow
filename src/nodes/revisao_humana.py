"""No de pausa humana.

`interrupt()` e a PRIMEIRA instrucao do no, de proposito: na retomada o LangGraph
re-executa o no inteiro desde o topo, entao qualquer coisa acima da pausa rodaria
duas vezes. Com a chamada na primeira linha, a re-execucao e comprovadamente livre
de efeito colateral.
"""

from typing import Any

from langchain_core.messages import HumanMessage
from langgraph.types import interrupt

from src.observability.logging import log
from src.schemas.revisao import DecisaoHumana
from src.state import MAX_REVISOES, EstadoDevFlow

_logger = log("revisao")


def revisao_humana(estado: EstadoDevFlow) -> dict:
    resposta = interrupt(
        {
            "instrucao": "Revise a triagem e o plano e responda com uma das acoes.",
            "acoes": ["aprovar", "revisar", "rejeitar"],
            "issue": {"id": estado.issue.id, "titulo": estado.issue.titulo},
            "triagem": estado.triagem.model_dump() if estado.triagem else None,
            "plano": estado.plano.model_dump() if estado.plano else None,
            "fontes_consultadas": [t["id"] for t in estado.contexto],
            "alertas": estado.alertas,
            "rodada": f"{estado.revisoes + 1} de {MAX_REVISOES}",
        }
    )

    decisao = _normalizar(resposta)
    _logger.info("issue %s: revisor respondeu `%s`", estado.issue.id, decisao.acao)

    if decisao.acao != "revisar":
        return {"decisao": decisao, "feedback": ""}

    # Numa revisao o plano e invalidado para forcar o replanejamento, e o feedback
    # entra como mensagem na conversa ja existente - o modelo enxerga o proprio
    # plano anterior e o que foi pedido. Nao da para "limpar" `msgs_plano`: o
    # reducer `add_messages` acumula, devolver [] nao apaga nada.
    return {
        "decisao": decisao,
        "feedback": decisao.comentario,
        "revisoes": estado.revisoes + 1,
        "plano": None,
        "msgs_plano": [
            HumanMessage(
                content=(
                    f"FEEDBACK A INCORPORAR\n{decisao.comentario}\n"
                    "Este e um replanejamento: corrija especificamente os pontos acima "
                    "e devolva o plano completo."
                )
            )
        ],
    }


def _normalizar(resposta: Any) -> DecisaoHumana:
    """Converte a resposta do revisor em contrato, sem nunca levantar.

    O contrato barra o erro humano classico (`aprovado` em vez de `aprovar`). Mas
    barrar nao pode significar travar a thread: quando o payload vem torto, cai em
    `revisar` com o texto original registrado, e a pessoa corrige na proxima pausa.
    """
    if isinstance(resposta, str):
        resposta = {"acao": resposta.strip().lower()}

    try:
        return DecisaoHumana.model_validate(resposta)
    except Exception:
        _logger.warning("payload de revisao invalido, tratado como `revisar`: %r", resposta)
        return DecisaoHumana(
            acao="revisar",
            comentario=f"resposta invalida do revisor, tratada como revisao: {resposta!r}",
            revisor="sistema",
        )
