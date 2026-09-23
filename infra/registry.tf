resource "azurerm_container_registry" "this" {
  name                = "${replace(var.prefix, "-", "")}acr${random_string.suffix.result}"
  resource_group_name = azurerm_resource_group.this.name
  location            = azurerm_resource_group.this.location
  sku                 = "Basic" # ~US$5/mes, 10 GB inclusos. Standard nao e necessario aqui.

  # Ja e o padrao no azurerm 5.x. Explicito porque o admin user e uma credencial
  # estatica compartilhada, e ha muito material antigo ensinando a liga-lo.
  admin_enabled = false
}

resource "azurerm_role_assignment" "acr_pull" {
  scope                = azurerm_container_registry.this.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_user_assigned_identity.app.principal_id
  principal_type       = "ServicePrincipal"
}
