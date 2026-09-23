#!/usr/bin/env bash
# Carrega as variaveis do .env da raiz para TF_VAR_*, sem deixar arquivo no disco.
#
# Use com `source`, nao execute:      source infra/carregar-env.sh
#
# Por que nao `set -a; source .env`: o .env pode ter espaco depois do `=`
# ("VAR= valor"), e em shell isso vira "execute `valor` com VAR vazia". O
# dotenv le corretamente e o shlex.quote protege caracteres especiais das
# chaves. Este arquivo NAO contem segredo nenhum - ele so os transporta.

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/.." && pwd)"

eval "$("$RAIZ/.venv/bin/python" - <<'PY' 2>/dev/null
from dotenv import dotenv_values
import shlex, pathlib
v = dotenv_values(pathlib.Path(__file__).parent / ".env") if False else dotenv_values(".env")
mapa = {
    "AZURE_OPENAI_API_KEY": "azure_openai_api_key",
    "AZURE_SEARCH_KEY": "azure_search_key",
    "AZURE_OPENAI_ENDPOINT": "azure_openai_endpoint",
    "AZURE_SEARCH_ENDPOINT": "azure_search_endpoint",
    "AZURE_OPENAI_CHAT_DEPLOYMENT": "azure_openai_chat_deployment",
    "AZURE_SEARCH_INDEX": "azure_search_index",
}
for chave, tf in mapa.items():
    valor = (v.get(chave) or "").strip()
    if valor:
        print(f"export TF_VAR_{tf}={shlex.quote(valor)}")
PY
)"

export TF_VAR_subscription_id="$(az account show --query id -o tsv)"
export TF_VAR_allowed_ip_cidr="$(curl -s -m 8 https://api.ipify.org)/32"
# O token de producao NAO vem do .env: la ele fica vazio, para o Studio local
# conectar. Vem de token-producao.sh (gitignored). Se nao existir, o apply
# mandaria token vazio e ABRIRIA o endpoint - por isso o aviso alto abaixo.
if [ -z "${TF_VAR_devflow_api_token:-}" ] && [ -f "$RAIZ/infra/token-producao.sh" ]; then
  source "$RAIZ/infra/token-producao.sh"
fi
if [ -z "${TF_VAR_devflow_api_token:-}" ]; then
  echo "AVISO: TF_VAR_devflow_api_token vazio - um apply agora deixaria o endpoint SEM AUTENTICACAO." >&2
fi

echo "assinatura : $(az account show --query name -o tsv)"
echo "IP liberado: $TF_VAR_allowed_ip_cidr"
echo "TF_VARs    : $(env | grep -c '^TF_VAR_')"
