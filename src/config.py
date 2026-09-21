"""Configuracao lida do .env. Um unico ponto de leitura de ambiente."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Azure OpenAI
    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    azure_openai_api_version: str = "2024-10-21"
    azure_openai_chat_deployment: str = "gpt-4o"

    # Azure AI Search: so consulta, o indice ja existe
    azure_search_endpoint: str = ""
    azure_search_index: str = "devflow-kb"
    azure_search_key: str = ""

    # MLflow
    mlflow_tracking_uri: str = ""
    mlflow_experiment: str = "devflow"


settings = Settings()


class ConfiguracaoAusente(RuntimeError):
    """Falta credencial no .env."""


def exigir(*campos: str) -> None:
    """Confere que os campos estao preenchidos, com erro que diz o que fazer.

    Chamado na criacao dos clientes, NAO no import: o grafo precisa montar sem
    credencial nenhuma (o `langgraph dev` carrega o modulo na subida, e o caminho
    do guardrail de entrada roda sem chamar o modelo).

    Sem isto, uma chave vazia vira `OpenAIError: Missing credentials ... set the
    OPENAI_API_KEY environment variable` - que aponta para a variavel errada,
    porque quem reclama e o SDK da OpenAI por baixo do cliente Azure.
    """
    faltando = [
        campo.upper()
        for campo in campos
        if not getattr(settings, campo, "") or "<" in getattr(settings, campo, "")
    ]
    if not faltando:
        return

    raise ConfiguracaoAusente(
        "Faltam variaveis no .env: " + ", ".join(faltando) + ".\n"
        "Copie o modelo com `cp .env.example .env` e preencha os valores do portal do Azure.\n"
        "Atencao: o DevFlow usa AZURE_OPENAI_API_KEY, nao OPENAI_API_KEY - se o erro "
        "original citou OPENAI_API_KEY, foi o SDK da OpenAI reclamando por baixo do cliente Azure."
    )
