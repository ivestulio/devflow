FROM python:3.12-slim

# uv: mesmo gerenciador usado no desenvolvimento
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Dependencias primeiro: camada reaproveitada quando so o codigo muda
COPY pyproject.toml ./
RUN uv pip install --system --no-cache .

COPY langgraph.json ./
COPY src/ ./src/
COPY kb/ ./kb/

RUN uv pip install --system --no-cache "langgraph-cli[inmem]>=0.4"

EXPOSE 2024

# --host 0.0.0.0 para o servidor responder fora do contêiner
CMD ["langgraph", "dev", "--host", "0.0.0.0", "--port", "2024", "--no-browser"]
