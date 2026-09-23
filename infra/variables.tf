# --- obrigatorias, sem default -------------------------------------------

variable "subscription_id" {
  type        = string
  description = "az account show --query id -o tsv"
}

variable "allowed_ip_cidr" {
  type        = string
  description = <<-DESC
    Seu IP publico em CIDR, ex.: "203.0.113.42/32".
    Obtenha com: curl -s https://api.ipify.org

    Esta e a UNICA barreira entre a internet e um grafo sem autenticacao.
    Ver a nota de seguranca no app_devflow.tf.
  DESC
}

variable "devflow_api_token" {
  type        = string
  sensitive   = true
  description = <<-DESC
    Token que o agente exige no header Authorization: Bearer <token>.

    Esta e a barreira de verdade. A lista de IPs do Container Apps foi testada
    e NAO e aplicada neste ambiente: requisicoes de IPs fora da regra foram
    atendidas com 200. A protecao agora e de aplicacao, nao de rede.

    Gere com: python3 -c "import secrets; print(secrets.token_urlsafe(32))"
  DESC
}

variable "image_tag" {
  type        = string
  description = "Tag da imagem do AGENTE, construida pelo `az acr build`. Nunca use 'latest'."
}

variable "mlflow_image_tag" {
  type        = string
  description = <<-DESC
    Tag da imagem do MLFLOW. Separada de propósito: as duas imagens tem ciclos
    de vida independentes. Mudar so o codigo do agente nao deveria obrigar a
    reconstruir o MLflow - e usar uma variavel unica faria o Terraform procurar
    uma tag de MLflow que nunca foi construida.
  DESC
}

# --- recursos que JA EXISTEM: entram como valor, nunca como data source ---
# Com variaveis, esses recursos nao entram no grafo do Terraform. Nada no
# terraform.tfstate os referencia, entao da para afirmar com seguranca:
# o `terraform destroy` NAO PODE toca-los, porque o Terraform nunca soube
# que eles existem.

variable "azure_openai_endpoint" {
  type        = string
  description = "Ex.: https://azopenaiaulas.openai.azure.com (recurso existente)"
}

variable "azure_openai_api_key" {
  type      = string
  sensitive = true
}

variable "azure_search_endpoint" {
  type        = string
  description = "Ex.: https://azsearchai.search.windows.net (recurso existente)"
}

variable "azure_search_key" {
  type      = string
  sensitive = true
}

# --- com default ----------------------------------------------------------

variable "prefix" {
  type    = string
  default = "devflow"
}

variable "location" {
  type    = string
  default = "eastus2"
}

variable "azure_openai_api_version" {
  type    = string
  default = "2024-10-21"
}

variable "azure_openai_chat_deployment" {
  type    = string
  default = "gpt-5.4"
}

variable "azure_search_index" {
  type    = string
  default = "devflow-kb"
}

variable "mlflow_public" {
  type        = bool
  default     = false
  description = <<-DESC
    Expor a UI do MLflow ao seu IP. Desligado por padrao.

    Mesmo desligado o tracing FUNCIONA: o agente chama o MLflow pelo nome curto
    dentro do ambiente, e esse trafego nunca sai do ambiente. Este toggle afeta
    somente o acesso do SEU NAVEGADOR a interface.
  DESC
}
