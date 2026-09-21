"""Cliente do modelo. Unico ponto do projeto que sabe qual e o provedor."""

from functools import lru_cache

from langchain_openai import AzureChatOpenAI

from src.config import exigir, settings


@lru_cache(maxsize=1)
def modelo() -> AzureChatOpenAI:
    """O modelo de raciocinio, criado uma vez e reaproveitado."""
    exigir("azure_openai_endpoint", "azure_openai_api_key", "azure_openai_chat_deployment")
    return AzureChatOpenAI(
        azure_endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_api_key,
        api_version=settings.azure_openai_api_version,
        azure_deployment=settings.azure_openai_chat_deployment,
        temperature=0,
    )


def modelo_com_ferramentas(ferramentas: list):
    """Modelo que pode PEDIR uma ferramenta. E aqui que o RAG vira escolha do LLM."""
    return modelo().bind_tools(ferramentas)


def modelo_estruturado(schema):
    """Modelo obrigado a responder no formato do contrato."""
    return modelo().with_structured_output(schema)
