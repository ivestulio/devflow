"""Autenticacao por token.

Por que existe
--------------
O `langgraph dev` sobe com LANGGRAPH_AUTH_TYPE=noop - sem autenticacao nenhuma.
No deploy isso significa que quem alcancar a URL executa o grafo e gasta a cota
do Azure OpenAI de quem publicou.

A primeira defesa tentada foi de rede (lista de IPs no ingress do Container
Apps). Ela NAO FUNCIONOU: requisicoes de IPs fora da lista continuaram sendo
atendidas com 200, mesmo com a regra confirmada no recurso e configurada tambem
pelo `az containerapp ingress access-restriction set`. Controle de plataforma
que falha em silencio e pior que nenhum.

Esta e a defesa de aplicacao: nao depende da plataforma.

Sem token configurado, o servidor LIBERA - e isso e um risco
---------------------------------------------------------------
`DEVFLOW_API_TOKEN` vazio significa "modo local, sem autenticacao". Foi uma
escolha consciente, e ela tem um custo que precisa estar a vista:

  ESTE MODULO NAO FALHA FECHADO. Esquecer a variavel em producao deixa o
  endpoint aberto, exatamente o cenario que ele existe para evitar.

A alternativa (recusar tudo com 503 quando a variavel falta) e mais segura, mas
quebra o LangGraph Studio: a documentacao diz que autorizacao customizada
"also applies to interactions made from Studio", e nao ha forma documentada de
mandar um header customizado pela UI. Com o Studio inutilizado, perde-se metade
do valor didatico do projeto.

A mitigacao e o aviso no log a cada subida sem token. Se voce ver essa linha num
servidor exposto, e um incidente.
"""

import logging
import os
import secrets

from langgraph_sdk import Auth

auth = Auth()

_logger = logging.getLogger("devflow.auth")


def _token_esperado() -> str:
    return os.environ.get("DEVFLOW_API_TOKEN", "").strip()


if not _token_esperado():
    _logger.warning(
        "=" * 70 + "\n"
        "DEVFLOW_API_TOKEN VAZIO - servidor SEM AUTENTICACAO.\n"
        "Aceitavel em desenvolvimento local (e o que permite o Studio conectar).\n"
        "Num servidor exposto, isto e uma porta aberta: qualquer pessoa com a URL\n"
        "executa o grafo e gasta a cota do modelo.\n" + "=" * 70
    )


@auth.authenticate
async def autenticar(authorization: str | None) -> dict:
    esperado = _token_esperado()

    # Sem token configurado: modo local. Ver o aviso acima.
    if not esperado:
        return {"identity": "local"}

    recebido = (authorization or "").removeprefix("Bearer ").strip()

    # compare_digest evita vazar o token por diferenca de tempo de resposta
    if not recebido or not secrets.compare_digest(recebido, esperado):
        raise Auth.exceptions.HTTPException(status_code=401, detail="token invalido ou ausente")

    return {"identity": "operador"}
