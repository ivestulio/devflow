"""RAG seletivo, exposto ao modelo como ferramenta.

"Seletivo" aqui tem dois sentidos, e os dois importam:

1. **O modelo escolhe**. A busca nao e um no fixo no caminho: e uma ferramenta que o
   LLM pede quando julga precisar, com a consulta que ele mesmo formula. Uma issue
   trivial pode ser classificada sem consulta nenhuma.

2. **A recuperacao poda**. Dentro da ferramenta, so as categorias pertinentes a etapa
   sao consultadas, e trechos muito mais fracos que o melhor da categoria sao
   descartados.
"""

from typing import List, Literal, Tuple

from langchain_core.tools import tool

from src.services.busca import BuscaAzure

# Que parte da base interessa a cada etapa. Evita trazer runbook de deploy para
# uma decisao de severidade, e politica de severidade para um plano de execucao.
INTENCAO = {
    "triagem": ["politica", "incidentes"],
    "planejamento": ["arquitetura", "testes", "runbook"],
}

K_POR_CATEGORIA = 3

# Corte relativo ao melhor trecho de cada categoria. 0.95 descarta quase tudo,
# 0.80 quase nada; 0.9 e o ponto calibrado no lab.
FRACAO = 0.9

_busca: BuscaAzure | None = None


def _cliente() -> BuscaAzure:
    """Instancia preguicosa: importar este modulo nao deve exigir credencial."""
    global _busca
    if _busca is None:
        _busca = BuscaAzure()
    return _busca


def recuperar_seletivo(
    consulta: str,
    tarefa: Literal["triagem", "planejamento"],
) -> Tuple[List[dict], List[dict]]:
    """Recupera por categoria e poda por razao de score.

    Devolve (mantidos, descartados). O melhor trecho de cada categoria e sempre
    mantido, mesmo que a categoria inteira seja fraca: o corte compara trechos
    entre si, nao contra um limiar absoluto.
    """
    mantidos: List[dict] = []
    descartados: List[dict] = []

    for categoria in INTENCAO[tarefa]:
        achados = _cliente().buscar(
            consulta,
            k=K_POR_CATEGORIA,
            filtro=f"categoria eq '{categoria}'",
            modo="vetor",
        )
        if not achados:
            continue

        corte = achados[0]["score"] * FRACAO
        mantidos.append(achados[0])
        for trecho in achados[1:]:
            (mantidos if trecho["score"] >= corte else descartados).append(trecho)

    return mantidos, descartados


@tool
def buscar_base_de_conhecimento(
    consulta: str,
    tarefa: Literal["triagem", "planejamento"],
) -> str:
    """Consulta a base de conhecimento interna de engenharia da Loja Aurora.

    Use esta ferramenta sempre que precisar de uma regra, um numero ou um nome que
    nao esteja na propria issue. E o UNICO jeito de obter fontes citaveis: qualquer
    afirmacao sobre politica, arquitetura ou historico precisa vir daqui.

    A base contem:
      - politica de engenharia: definicao de pronto, escalas de severidade,
        prioridade e esforco, regras para mudanca em preco;
      - arquitetura do checkout: servicos, maquina de estados do carrinho,
        aplicacao de cupons, idempotencia de cotacao;
      - padroes de teste: piramide adotada, testes de regressao de preco,
        cenarios minimos para cupom;
      - runbook de pagamentos: janelas de deploy, feature flags, metricas;
      - historico de incidentes: causas raiz de falhas anteriores.

    Args:
        consulta: o que voce quer saber, em linguagem natural. Seja especifico -
            a busca e semantica, entao "regra de unicidade de cupom no recalculo"
            recupera melhor que "cupom".
        tarefa: "triagem" consulta politica e incidentes; "planejamento" consulta
            arquitetura, testes e runbook.

    Returns:
        Os trechos recuperados, cada um com o seu ID entre colchetes. Cite esses
        IDs no campo `fontes` da sua resposta.
    """
    mantidos, _ = recuperar_seletivo(consulta, tarefa)
    if not mantidos:
        return "Nenhum trecho relevante encontrado na base para esta consulta."
    return formatar_contexto(mantidos)


def formatar_contexto(trechos: List[dict]) -> str:
    """Formata trechos para o modelo, com o ID visivel para citacao."""
    blocos = [f"[{t['id']}] ({t['titulo']})\n{t['texto']}" for t in trechos]
    return "\n\n".join(blocos)


def juntar_sem_duplicar(atual: List[dict], novos: List[dict]) -> List[dict]:
    """Acumula trechos preservando a ordem e sem repetir id.

    Necessario porque `contexto` nao tem reducer no estado: a juncao e explicita
    aqui em vez de implicita no canal, justamente para nao duplicar quando o
    subgrafo e reentrado pela acao `revisar`.
    """
    vistos = {t["id"]: t for t in atual}
    for t in novos:
        vistos.setdefault(t["id"], t)
    return list(vistos.values())
