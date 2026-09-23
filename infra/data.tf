# Senha do Postgres.
#
# Tentei usar `ephemeral "random_password"` + `administrator_password_wo` para
# manter a senha fora do state. NAO FUNCIONA aqui, e o `terraform validate`
# pega: o `secret` do azurerm_container_app nao aceita valor efemero, porque
# `secret.value` e apenas (optional, sensitive) - nao existe versao write-only
# neste provider (conferido no schema).
#
# E como a string de conexao COM a senha precisa virar secret do Container App,
# a senha acaba no state de qualquer jeito. Manter o efemero so no servidor
# daria a falsa impressao de protecao. Entao: recurso normal, e o aviso abaixo.
#
# >> O terraform.tfstate guarda esta senha e as chaves de API em TEXTO CLARO.
# >> `sensitive = true` so esconde da saida do terminal; nao criptografa nada.
# >> Trate o arquivo como o .env: fora do git, chmod 600, e rotacione as
# >> chaves ao fim do curso.
#
# A correcao de verdade seria Key Vault: o `secret` do Container App aceita
# `key_vault_secret_id`, e ai so o URI do cofre entra no state. Custa um
# recurso a mais e uma licao inteira de RBAC - fica como proximo passo.
resource "random_password" "pg" {
  length  = 32
  special = false # evita ter de fazer URL-encode na string de conexao
}

resource "azurerm_postgresql_flexible_server" "mlflow" {
  name                = "${var.prefix}-pg-${random_string.suffix.result}"
  resource_group_name = azurerm_resource_group.this.name
  location            = azurerm_resource_group.this.location

  version                       = "16"
  sku_name                      = "B_Standard_B1ms" # ~US$12,41/mes de compute
  storage_mb                    = 32768             # minimo; so escala para cima
  auto_grow_enabled             = false             # sem conta surpresa de storage
  backup_retention_days         = 7
  geo_redundant_backup_enabled  = false
  public_network_access_enabled = true
  zone                          = "1"

  administrator_login    = "mlflowadmin"
  administrator_password = random_password.pg.result

  lifecycle {
    # A Azure pode mover o servidor de zona num failover; nao brigar com isso.
    ignore_changes = [zone]
  }
}

resource "azurerm_postgresql_flexible_server_database" "mlflow" {
  name      = "mlflow"
  server_id = azurerm_postgresql_flexible_server.mlflow.id
  charset   = "UTF8"
  collation = "en_US.utf8"
}

# start == end == 0.0.0.0 e um valor MAGICO que significa "qualquer servico
# Azure". Nao e um CIDR e nao e "qualquer IP".
#
# RISCO NOMEADO: a documentacao da Azure diz que isso permite conexoes de
# "qualquer servico ou recurso Azure, INCLUSIVE de assinaturas de outros
# clientes". O servidor fica a uma senha de distancia de qualquer pessoa com
# uma conta Azure. Para um banco de demonstracao com metadados do MLflow, senha
# gerada de 32 caracteres e `terraform destroy` no fim da aula, e um risco
# aceitavel - mas nao um risco invisivel.
#
# E necessario porque o ACA em plano de consumo sai por IPs compartilhados que
# nao da para fixar de antemao.
resource "azurerm_postgresql_flexible_server_firewall_rule" "azure_services" {
  name             = "allow-azure-services"
  server_id        = azurerm_postgresql_flexible_server.mlflow.id
  start_ip_address = "0.0.0.0"
  end_ip_address   = "0.0.0.0"
}

resource "azurerm_storage_account" "mlflow" {
  name                     = "${replace(var.prefix, "-", "")}st${random_string.suffix.result}"
  resource_group_name      = azurerm_resource_group.this.name
  location                 = azurerm_resource_group.this.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
}

resource "azurerm_storage_container" "artifacts" {
  name = "mlflow-artifacts"

  # azurerm 5.x: e `storage_account_id`, nao mais `storage_account_name`.
  # Praticamente todo exemplo anterior a v5 erra isto.
  storage_account_id    = azurerm_storage_account.mlflow.id
  container_access_type = "private"
}

resource "azurerm_role_assignment" "blob" {
  scope                = azurerm_storage_account.mlflow.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_user_assigned_identity.app.principal_id
  principal_type       = "ServicePrincipal"
}
