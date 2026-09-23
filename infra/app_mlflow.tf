resource "azurerm_container_app" "mlflow" {
  name                         = "${var.prefix}-mlflow"
  container_app_environment_id = azurerm_container_app_environment.this.id
  resource_group_name          = azurerm_resource_group.this.name
  revision_mode                = "Single"

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.app.id]
  }

  registry {
    server   = azurerm_container_registry.this.login_server
    identity = azurerm_user_assigned_identity.app.id
  }

  ingress {
    # Padrao false => so interno. O agente continua alcancando em
    # http://devflow-mlflow porque trafego dentro do ambiente nunca sai dele.
    # Este toggle afeta apenas o acesso do SEU NAVEGADOR a interface, entao
    # liga-lo ou nao jamais quebra o tracing.
    external_enabled = var.mlflow_public
    target_port      = 5000

    traffic_weight {
      latest_revision = true
      percentage      = 100
    }

    dynamic "ip_security_restriction" {
      for_each = var.mlflow_public ? [1] : []
      content {
        name             = "allow-operator"
        action           = "Allow"
        ip_address_range = var.allowed_ip_cidr
        description      = "O MLflow OSS tambem nao tem autenticacao."
      }
    }
  }

  secret {
    name  = "backend-store-uri"
    value = "postgresql+psycopg2://${azurerm_postgresql_flexible_server.mlflow.administrator_login}:${random_password.pg.result}@${azurerm_postgresql_flexible_server.mlflow.fqdn}:5432/mlflow?sslmode=require"
  }

  template {
    # min_replicas = 1, nao 0. O raciocinio de "tracing e assincrono, cold start
    # nao importa" estava errado na pratica:
    #
    # O agente usa MLFLOW_HTTP_REQUEST_TIMEOUT=5 (curto de proposito, senao o
    # import de src.graph trava ate 14 min quando o MLflow nao responde). Acordar
    # um contêiner escalado a zero leva 10-30s. Resultado: o agente SEMPRE
    # desistia antes de o MLflow subir, e o tracing nunca funcionava - falhando
    # em silencio, porque configurar_mlflow() engole a excecao de proposito.
    #
    # Custa ~US$4/mes manter um replica quente. Um backend de tracing
    # inalcancavel custa mais: observabilidade que nunca registra nada.
    # De volta a zero: com o tracing desligado no agente, nao ha por que
    # manter replica quente pagando ~US$4/mes.
    min_replicas = 0
    max_replicas = 1

    container {
      name  = "mlflow"
      image = "${azurerm_container_registry.this.login_server}/mlflow:${var.mlflow_image_tag}"

      # 0.25/0.5Gi nao bastou: o contêiner subia, imprimia o banner do uvicorn e
      # morria, acumulando restarts com `ready: false`. O MLflow 3.x sobe varios
      # workers e cada um carrega SQLAlchemy, psycopg2 e os SDKs do Azure.
      # Os pares validos no ACA sao 0.25/0.5Gi, 0.5/1.0Gi, 0.75/1.5Gi...
      cpu    = 0.5
      memory = "1.0Gi"

      command = ["mlflow", "server"]
      args = [
        "--host", "0.0.0.0",
        "--port", "5000",
        "--backend-store-uri", "$(BACKEND_STORE_URI)",
        "--artifacts-destination",
        "wasbs://mlflow-artifacts@${azurerm_storage_account.mlflow.name}.blob.core.windows.net",
        # Com --serve-artifacts o servidor do MLflow faz proxy do upload e do
        # download. O agente NUNCA precisa de credencial de storage.
        "--serve-artifacts",
        # Um worker so: o agente e o unico cliente, e cada worker extra custa
        # memoria que ja faltou uma vez.
        "--workers", "1",
        # MLflow 3.x tem um middleware anti-DNS-rebinding. O default cobre 28
        # padroes: localhost, 127.0.0.1 E os intervalos privados (10.*, 172.16-18.*,
        # 192.168.*).
        #
        # ATENCAO: passar --allowed-hosts SUBSTITUI o default inteiro, nao soma.
        # Uma primeira tentativa listou so o hostname e localhost, o que derrubou
        # a cobertura de IP privado - e o health probe do Container Apps chega
        # pelo IP do pod (10.x). Resultado: ActivationFailed, com o servidor
        # rodando normalmente por dentro.
        #
        # Aqui: hostname do servico + os privados que o default trazia.
        "--allowed-hosts", "${var.prefix}-mlflow,${var.prefix}-mlflow:*,localhost,127.0.0.1,0.0.0.0,10.*,172.16.*,172.17.*,172.18.*,192.168.*",
      ]

      env {
        name        = "BACKEND_STORE_URI"
        secret_name = "backend-store-uri"
      }

      # O DefaultAzureCredential usa a identidade gerenciada a partir daqui.
      # Nenhuma chave de storage existe em lugar nenhum, nem no state.
      env {
        name  = "AZURE_CLIENT_ID"
        value = azurerm_user_assigned_identity.app.client_id
      }
    }
  }

  depends_on = [
    azurerm_role_assignment.acr_pull,
    azurerm_role_assignment.blob,
    azurerm_postgresql_flexible_server_database.mlflow,
    azurerm_postgresql_flexible_server_firewall_rule.azure_services,
  ]
}
