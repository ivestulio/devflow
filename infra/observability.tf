resource "azurerm_log_analytics_workspace" "this" {
  name                = "${var.prefix}-logs"
  resource_group_name = azurerm_resource_group.this.name
  location            = azurerm_resource_group.this.location
  sku                 = "PerGB2018"
  retention_in_days   = 30

  # Os primeiros 5 GB/mes sao gratuitos; depois, US$2,30/GB. O teto existe
  # porque um servidor em loop de reload gera volume de log de verdade.
  daily_quota_gb = 0.5
}

resource "azurerm_container_app_environment" "this" {
  name                = "${var.prefix}-env"
  resource_group_name = azurerm_resource_group.this.name
  location            = azurerm_resource_group.this.location

  # `logs_destination` precisa ser explicito: sem ele o provider recusa o
  # log_analytics_workspace_id com "can only be set when logs_destination is
  # set to log-analytics".
  logs_destination           = "log-analytics"
  log_analytics_workspace_id = azurerm_log_analytics_workspace.this.id
}
