terraform {
  # 1.11+ e exigido pelos argumentos write-only (administrator_password_wo)
  required_version = ">= 1.11.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 5.6"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.9"
    }
  }
}

provider "azurerm" {
  subscription_id = var.subscription_id

  # O azurerm 5.0 mudou este padrao de "legacy" para "none". Numa assinatura
  # nova isso significa que Microsoft.App, ContainerRegistry e DBforPostgreSQL
  # nunca sao registrados, e o apply falha com MissingSubscriptionRegistration.
  # Esta linha e a causa mais provavel de erro na primeira execucao de um aluno.
  # ATENCAO: "core" NAO cobre tudo. Nesta stack faltaram, e foi preciso
  # registrar na mao antes do apply:
  #   az provider register --namespace Microsoft.DBforPostgreSQL --wait
  #   az provider register --namespace Microsoft.App --wait
  # O sintoma e um 409 MissingSubscriptionRegistration no meio do apply.
  resource_provider_registrations = "core"

  features {}
}

# --- Sobre o estado -------------------------------------------------------
# O state fica LOCAL de proposito. Um backend remoto no Azure Storage seria
# melhor pratica, mas cria um problema de ovo e galinha (o storage teria de
# existir antes do `terraform init`) e deixa um recurso que o `terraform
# destroy` NAO remove - encerrar a aula mandando o aluno apagar coisa na mao
# ensina exatamente o habito errado.
#
# O risco do state local e perde-lo e orfanar recursos. A mitigacao e
# estrutural: tudo vive num unico resource group, entao
#   az group delete --name <rg> --yes --no-wait
# e um teardown completo que funciona mesmo sem state nenhum.
#
# Quando uma segunda pessoa ou um CI mexer nesta stack, o state local deixa de
# servir. Faca o bootstrap com o az CLI (NAO com Terraform) e descomente:
#
#   backend "azurerm" {
#     resource_group_name  = "rg-tfstate"
#     storage_account_name = "<conta>"
#     container_name       = "tfstate"
#     key                  = "devflow.tfstate"
#     use_azuread_auth     = true
#   }
