# ---------------------------------------------------------------------------
# NOTA DE SEGURANCA - leia antes de mexer no ingress
#
# O `langgraph dev` sobe com LANGGRAPH_AUTH_TYPE=noop: SEM autenticacao
# nenhuma. Pior: o CORS_ALLOW_ORIGINS do langgraph-api tambem tem default "*",
# com allow_methods ["*"]. Verificado no codigo-fonte instalado.
#
# A combinacao significa que, com ingress publico e sem restricao, qualquer
# pagina web que voce visite pode fazer o SEU navegador disparar uma execucao
# no grafo e gastar sua cota do Azure OpenAI - sem nunca precisar descobrir a
# URL. E materialmente pior do que "alguem precisa achar o endereco".
#
# A defesa REAL e o token (src/auth.py + bloco `auth` no langgraph.json):
# o servidor recusa toda rota de dados sem Authorization: Bearer <token>.
# As rotas /ok, /info e /docs continuam abertas - e necessario, senao o health
# probe do Container Apps nao consegue verificar o contêiner.
#
# A lista de IPs abaixo fica como defesa em profundidade, mas NAO CONFIE NELA:
# testada neste ambiente, requisicoes de IPs fora da regra foram atendidas com
# 200, em /ok, /info e /docs, com a regra confirmada no recurso e tambem
# configurada via `az containerapp ingress access-restriction set`. A
# documentacao diz que um cliente bloqueado receberia "RBAC: Access Denied";
# nunca apareceu. Controle que falha em silencio e pior que nenhum.
#
# CORS_ALLOW_ORIGINS fixo fecha o default "*", de graca.
#
# O teto financeiro de verdade, porem, e a cota TPM do deployment gpt-5.4 no
# AI Foundry. Ela fica fora do Terraform (recurso preexistente). Reduza-a
# antes de expor qualquer coisa.
#
# A correcao definitiva e de aplicacao, nao de infra: um bloco `auth` no
# langgraph.json com um handler @auth.authenticate checando um bearer token.
# ~10 linhas de Python que desligam o noop de vez.
# ---------------------------------------------------------------------------

resource "azurerm_container_app" "devflow" {
  name                         = "${var.prefix}-agent"
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
    # O ACA termina TLS: a URL sai em https://, o que de quebra resolve o
    # bloqueio de conteudo misto que impedia o Studio de falar com o servidor
    # local em http://127.0.0.1:2024.
    external_enabled = true
    target_port      = 2024
    transport        = "auto"

    # Obrigatorio mesmo em revision_mode = "Single". Omitir da o erro
    # "At least 1 traffic_weight blocks are required".
    traffic_weight {
      latest_revision = true
      percentage      = 100
    }

    # O bloco e SINGULAR: ip_security_restriction, nao ..._restrictions.
    # Regras Allow e Deny nao podem ser misturadas: com uma regra Allow, todo
    # o resto e implicitamente negado.
    ip_security_restriction {
      name             = "allow-operator"
      action           = "Allow"
      ip_address_range = var.allowed_ip_cidr
      description      = "langgraph dev nao tem auth; so este IP alcanca."
    }
  }

  secret {
    name  = "azure-openai-api-key"
    value = var.azure_openai_api_key
  }

  secret {
    name  = "azure-search-key"
    value = var.azure_search_key
  }

  secret {
    name  = "devflow-api-token"
    value = var.devflow_api_token
  }

  template {
    # min_replicas = 1 aqui e CORRETUDE, nao conforto.
    #
    # O fluxo tem revisao humana via interrupt(), que estaciona a thread na
    # MEMORIA (servidor in-memory, decisao aceita). Se a revisao escalar a zero
    # durante a pausa - e uma pessoa lendo um plano passa facil dos 300s de
    # cooldown padrao - toda thread pausada evapora e o resume falha.
    # Os ~US$4/mes compram human-in-the-loop funcionando.
    min_replicas = 1
    max_replicas = 1

    container {
      name = "devflow"
      # Tag unica por build. Com `:latest` o template nao muda, o Terraform nao
      # cria revisao nova, e a imagem nova simplesmente nao entra no ar.
      image  = "${azurerm_container_registry.this.login_server}/devflow:${var.image_tag}"
      cpu    = 0.25
      memory = "0.5Gi"

      # Fecha o default "*" do CORS. O Studio e a unica origem de navegador que
      # legitimamente chama este servidor. Sem barra no final.
      env {
        name  = "CORS_ALLOW_ORIGINS"
        value = "https://smith.langchain.com"
      }

      # HTTPS e FQDN interno COMPLETO. Duas correcoes que custaram varias rodadas:
      #
      # 1. O nome curto (`http://devflow-mlflow`) nao resolve. O endereco e
      #    <app>.internal.<dominio-do-ambiente>.
      # 2. O ingress interno do ACA tem allowInsecure=false, entao `http://`
      #    e redirecionado para HTTPS - e o log do cliente denunciava isso
      #    dizendo HTTPSConnectionPool para uma URI escrita como http.
      #
      #
      # `http://devflow-mlflow` nao resolveu: o agente acumulou ReadTimeoutError
      # por varias rodadas mesmo com o MLflow saudavel. O endereco que funciona e
      # <app>.internal.<dominio-do-ambiente>, e o proprio recurso ja o expoe -
      # referenciar e melhor que montar a string na mao.
      #
      # O trafego continua sem sair do ambiente (o ingress do MLflow e interno),
      # entao nada disso passa por internet nem exige exposicao publica.
      env {
        name = "MLFLOW_TRACKING_URI"
        # VAZIO de proposito: o tracing nao funcionou neste ambiente.
        #
        # Tres causas foram encontradas e corrigidas (memoria do contêiner, nome
        # curto que nao resolve, http redirecionado para https), e mesmo assim o
        # cliente do MLflow continua estourando o timeout contra o ingress
        # interno. Com a variavel vazia o agente pula o tracing de forma limpa -
        # sem retries, sem ruido no log e com boot mais rapido - em vez de
        # tentar e falhar a cada subida.
        #
        # Para retomar a investigacao: repor o FQDN abaixo e subir
        # MLFLOW_HTTP_REQUEST_TIMEOUT.
        #   value = "https://${azurerm_container_app.mlflow.ingress[0].fqdn}"
        value = ""
      }
      env {
        name  = "MLFLOW_EXPERIMENT"
        value = "devflow"
      }
      env {
        name  = "MLFLOW_ENABLE_ASYNC_TRACE_LOGGING"
        value = "true"
      }

      # CRITICO para o boot. `configurar()` roda no import de src.graph e chama
      # mlflow.set_experiment(), que faz HTTP. Os defaults do cliente MLflow sao
      # timeout=120s e max_retries=7: com o MLflow fora do ar isso bloqueia o
      # import por ATE 14 MINUTOS, o startup probe falha e o contêiner entra em
      # loop de restart (ActivationFailed). O try/except que degrada o tracing
      # nunca chegava a ser alcancado.
      # 15s, nao 5s: o handshake TLS com o ingress interno nao cabia em 5s.
      # Continua curto o bastante para nao repetir o travamento de 14 minutos
      # (que vinha do default 120s x 7 retries), agora que o MLflow tem replica
      # quente (min_replicas = 1) e responde rapido.
      env {
        name  = "MLFLOW_HTTP_REQUEST_TIMEOUT"
        value = "15"
      }
      env {
        name  = "MLFLOW_HTTP_REQUEST_MAX_RETRIES"
        value = "1"
      }

      env {
        name        = "AZURE_OPENAI_API_KEY"
        secret_name = "azure-openai-api-key"
      }
      env {
        name        = "AZURE_SEARCH_KEY"
        secret_name = "azure-search-key"
      }

      # Sem esta variavel o agente recusa TUDO com 503 (falha fechada).
      env {
        name        = "DEVFLOW_API_TOKEN"
        secret_name = "devflow-api-token"
      }

      env {
        name  = "AZURE_OPENAI_ENDPOINT"
        value = var.azure_openai_endpoint
      }
      env {
        name  = "AZURE_OPENAI_API_VERSION"
        value = var.azure_openai_api_version
      }
      env {
        name  = "AZURE_OPENAI_CHAT_DEPLOYMENT"
        value = var.azure_openai_chat_deployment
      }
      env {
        name  = "AZURE_SEARCH_ENDPOINT"
        value = var.azure_search_endpoint
      }
      env {
        name  = "AZURE_SEARCH_INDEX"
        value = var.azure_search_index
      }

      # O boot carrega o grafo inteiro (imports pesados do langchain). Da folga
      # antes de declarar o contêiner morto.
      startup_probe {
        transport               = "HTTP"
        port                    = 2024
        path                    = "/ok"
        initial_delay           = 10
        interval_seconds        = 10
        failure_count_threshold = 30 # ate 5 min para subir
      }

      liveness_probe {
        transport = "HTTP"
        port      = 2024
        path      = "/ok" # rota meta do langgraph-api, nao colidivel com o grafo
      }
    }
  }

  depends_on = [azurerm_role_assignment.acr_pull]
}
