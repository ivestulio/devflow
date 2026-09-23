FROM python:3.12-slim

# Versao fixa: `:latest` aqui tornaria ate a ferramenta nao-reprodutivel.
COPY --from=ghcr.io/astral-sh/uv:0.9.29 /uv /usr/local/bin/uv

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1

WORKDIR /app

# --- camada 1: so dependencias, direto do lockfile -------------------------
# `--locked` falha se o uv.lock estiver desatualizado, em vez de re-resolver
# em silencio. `--no-install-project` pula o pacote local, entao esta camada
# fica em cache ate pyproject.toml ou uv.lock mudarem de verdade.
#
# O grupo `dev` entra por padrao, e e ele que traz o langgraph-cli[inmem] e o
# langgraph-api>=1.11 - o piso que o Studio exige para mostrar traces.
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-install-project

# --- camada 2: o codigo ----------------------------------------------------
# So agora `src/` existe. Instalar o projeto antes disto falharia: o
# hatchling empacota `packages = ["src"]` e o diretorio ainda nao estaria la.
COPY langgraph.json ./
COPY src/ ./src/
COPY kb/ ./kb/
RUN uv sync --locked

ENV PATH="/app/.venv/bin:$PATH"

# Nao rodar como root. O ACA nao exige, mas nao custa nada.
RUN useradd --create-home --uid 10001 devflow && chown -R devflow:devflow /app
USER devflow

EXPOSE 2024

# --no-reload: o watcher e inutil num contêiner imutavel e ativamente nocivo -
#   um reload CANCELA execucoes em voo, e com o servidor in-memory isso destroi
#   toda thread pausada em interrupt().
#
# NAO existe .env nesta imagem, de proposito. O langgraph.json aponta para
#   ./.env; o python-dotenv devolve {} para arquivo ausente, e os valores reais
#   chegam como variaveis de ambiente do Container App.
CMD ["langgraph", "dev", \
     "--host", "0.0.0.0", \
     "--port", "2024", \
     "--no-reload", \
     "--no-browser"]
