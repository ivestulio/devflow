# Sufixo para os nomes que precisam ser globalmente unicos (ACR, Postgres,
# Storage). Sem isso, dois alunos rodando o mesmo codigo colidem.
resource "random_string" "suffix" {
  length  = 6
  special = false
  upper   = false
}

resource "azurerm_resource_group" "this" {
  name     = "rg-${var.prefix}"
  location = var.location
}

# Identidade USER-assigned, nao system-assigned.
#
# Com system-assigned o principal so passa a existir quando o Container App e
# criado - mas a permissao AcrPull precisa ja estar valendo no primeiro pull da
# imagem. Isso e circular, e se manifesta como uma falha no primeiro apply que
# "magicamente" some no segundo. A user-assigned e criada antes, recebe o papel,
# e e referenciada pelos dois apps.
resource "azurerm_user_assigned_identity" "app" {
  name                = "${var.prefix}-id"
  resource_group_name = azurerm_resource_group.this.name
  location            = azurerm_resource_group.this.location
}
