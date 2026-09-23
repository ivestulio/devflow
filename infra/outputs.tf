output "acr_name" {
  value       = azurerm_container_registry.this.name
  description = "Use no `az acr build --registry`"
}

output "resource_group" {
  value = azurerm_resource_group.this.name
}

# `try` porque o fqdn e null quando o ingress esta desabilitado. Sem isso, um
# `az containerapp ingress disable` (util como mitigacao de emergencia) deixa o
# output invalido e ABORTA qualquer apply seguinte - inclusive o que reabilitaria
# o ingress. Output nao pode ser o que trava a recuperacao.
output "devflow_url" {
  value       = try("https://${azurerm_container_app.devflow.ingress[0].fqdn}", "ingress desabilitado")
  description = "Abra o Studio com ?baseUrl=<esta URL>"
}

output "mlflow_url" {
  value       = var.mlflow_public ? try("https://${azurerm_container_app.mlflow.ingress[0].fqdn}", "sem ingress") : "interno (mlflow_public = false)"
  description = "UI do MLflow, se exposta"
}

output "mlflow_app_name" {
  value = azurerm_container_app.mlflow.name
}

output "postgres_name" {
  value       = azurerm_postgresql_flexible_server.mlflow.name
  description = "Para parar entre aulas: az postgres flexible-server stop -n <este> -g <rg>"
}
