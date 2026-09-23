# Os arquivos `.tf`, um a um

Guia dos nove arquivos Terraform que provisionam o DevFlow na Azure. Cada seção diz **o que o
arquivo cria**, **por que está escrito daquele jeito**, e — quando houver — **que erro real levou
àquela linha**.

Quase todos os comentários no código nasceram de algo que quebrou durante o deploy. Eles estão lá
porque a informação só existe depois do erro.

## Visão geral

| Arquivo | Linhas | Papel |
|---|---:|---|
| [`versions.tf`](versions.tf) | 55 | versões, provider, nota sobre o state |
| [`variables.tf`](variables.tf) | 111 | todas as entradas |
| [`main.tf`](main.tf) | 25 | resource group, identidade, sufixo aleatório |
| [`registry.tf`](registry.tf) | 17 | ACR e permissão de pull |
| [`observability.tf`](observability.tf) | 23 | Log Analytics e ambiente do Container Apps |
| [`data.tf`](data.tf) | 97 | Postgres, storage e permissão de blob |
| [`app_devflow.tf`](app_devflow.tf) | 235 | o agente |
| [`app_mlflow.tf`](app_mlflow.tf) | 121 | o MLflow |
| [`outputs.tf`](outputs.tf) | 31 | URLs e nomes que você vai precisar |

A ordem acima é a de leitura recomendada: cada arquivo depende dos anteriores.

---

## `versions.tf`

Fixa o Terraform em `>= 1.11` e o provider `azurerm` em `~> 5.6`.

**`resource_provider_registrations = "core"`** é a linha que mais causa erro em assinatura nova — e
não resolve sozinha. O `core` **não cobre tudo**: nesta stack faltaram dois namespaces, e o apply
morreu no meio com `409 MissingSubscriptionRegistration`. Registre antes:

```bash
az provider register --namespace Microsoft.DBforPostgreSQL --wait
az provider register --namespace Microsoft.App --wait
```

O arquivo também explica **por que o state é local**. Um backend remoto no Azure Storage é melhor
prática, mas cria o problema do ovo e da galinha (o storage precisaria existir antes do `init`) e
deixa um recurso que o `terraform destroy` não remove — ensinar a terminar a aula apagando coisa na
mão é o hábito errado. A mitigação do state local é estrutural: **tudo vive num resource group só**,
então `az group delete` é um teardown completo que funciona sem state nenhum.

## `variables.tf`

Quinze variáveis, divididas em três grupos.

**Obrigatórias:** `subscription_id`, `allowed_ip_cidr`, `devflow_api_token`, `image_tag`,
`mlflow_image_tag`.

**Recursos que já existem:** `azure_openai_endpoint`, `azure_search_endpoint` e as respectivas
chaves. Entram como **valor**, nunca como `data source` — e essa escolha tem consequência prática:
como o Terraform nunca ouve falar do `azopenaiaulas` e do `azsearchai`, nada no `tfstate` os
referencia, e dá para afirmar com certeza que **`terraform destroy` não pode tocá-los**. Um `data
source` tornaria isso uma questão de confiança em vez de uma garantia estrutural.

**`image_tag` e `mlflow_image_tag` são separadas** porque as duas imagens têm ciclos de vida
independentes. Uma variável única fazia o Terraform procurar uma tag de MLflow que nunca tinha sido
construída, sempre que só o agente mudava.

## `main.tf`

Três recursos, e o terceiro é o mais sutil.

`random_string.suffix` dá unicidade global aos nomes que precisam (ACR, Postgres, Storage) — sem
ele, dois alunos rodando o mesmo código colidem.

**`azurerm_user_assigned_identity`, não system-assigned.** Com system-assigned o principal só passa
a existir quando o Container App é criado, mas a permissão `AcrPull` precisa já estar valendo no
primeiro pull da imagem. Isso é circular, e se manifesta como uma falha no primeiro apply que
"magicamente" some no segundo. A user-assigned nasce antes, recebe o papel, e é usada pelos dois apps.

## `registry.tf`

ACR no SKU **Basic** (~US$5/mês, 10 GB inclusos) e o `AcrPull` para a identidade.

`admin_enabled = false` — já é o padrão no azurerm 5.x, mas está explícito porque o admin user é uma
credencial estática compartilhada e há muito material antigo ensinando a ligá-lo.

## `observability.tf`

Log Analytics com cota de 0,5 GB/dia, e o ambiente do Container Apps.

**`logs_destination = "log-analytics"` precisa ser explícito.** Sem ele o provider recusa o
`log_analytics_workspace_id` com *"can only be set when logs_destination is set to log-analytics"*.

A cota existe porque um servidor em loop de reload gera volume de log de verdade — e isso aconteceu
nesta sessão.

## `data.tf`

Postgres (backend do MLflow), storage para artefatos, e o `Storage Blob Data Contributor`.

**A senha é um `random_password` comum, e isso é uma escolha explicada no código.** Tentei usar
`ephemeral` + `administrator_password_wo` para mantê-la fora do state. Não funciona: o `terraform
validate` recusa, porque o `secret` do Container App não aceita valor efêmero (`secret.value` é só
`optional, sensitive`, sem versão write-only neste provider). E como a string de conexão com a senha
precisa virar secret do app, ela cai no state de qualquer jeito — manter o efêmero só no servidor
daria falsa impressão de proteção.

> **O `terraform.tfstate` guarda a senha do Postgres e as chaves de API em TEXTO CLARO.**
> `sensitive = true` só esconde da saída do terminal; não criptografa nada. O arquivo está no
> `.gitignore` e com `chmod 600`. Rotacione as chaves ao fim do curso.

**A regra de firewall `0.0.0.0` → `0.0.0.0`** é um valor mágico que significa "qualquer serviço
Azure" — e a documentação da Microsoft é explícita de que isso inclui **assinaturas de outros
clientes**. É um risco aceito e nomeado: banco de demonstração, senha de 32 caracteres, `destroy` no
fim da aula. É necessário porque o ACA em plano de consumo sai por IPs compartilhados que não dá
para fixar de antemão.

`azurerm_storage_container` usa **`storage_account_id`**, não `storage_account_name` — mudou no
azurerm 5.x, e praticamente todo exemplo anterior à v5 erra isso.

## `app_devflow.tf`

O maior arquivo, e o que concentra as decisões de segurança.

### A nota de segurança no topo

O `langgraph dev` sobe com `LANGGRAPH_AUTH_TYPE=noop` — sem autenticação. Pior: o
`CORS_ALLOW_ORIGINS` do `langgraph-api` também tem default `"*"` com `allow_methods ["*"]`. Ambos
verificados no código-fonte instalado.

A combinação significa que, com ingress público e sem proteção, **qualquer página que você visite
pode fazer o seu navegador disparar execuções no grafo** e gastar sua cota do Azure OpenAI, sem
nunca precisar descobrir a URL.

### `ip_security_restriction` — está lá, mas NÃO confie

Foi a primeira defesa tentada. **Não funciona neste ambiente.** Testei de um IP externo e recebi
`200` em `/ok`, `/info` e `/docs`, com a regra confirmada no recurso e configurada também pelo
`az containerapp ingress access-restriction set`. A documentação diz que um cliente bloqueado
receberia `RBAC: Access Denied`; nunca apareceu.

O bloco continua no arquivo como defesa em profundidade, com o aviso ao lado. **Um controle que
falha em silêncio é pior que nenhum**, porque dá falsa sensação de proteção.

A proteção real é o token, em [`../src/auth.py`](../src/auth.py).

### `CORS_ALLOW_ORIGINS`

Fixado em `https://smith.langchain.com` — fecha o default `"*"`, de graça.

### `min_replicas = 1` é corretude, não conforto

O fluxo tem revisão humana via `interrupt()`, que estaciona a thread **na memória**. Se a revisão
escalar a zero durante a pausa — e uma pessoa lendo um plano passa fácil dos 300s de cooldown
padrão — toda thread pausada evapora e o resume falha. Os ~US$4/mês compram human-in-the-loop
funcionando.

### `MLFLOW_HTTP_REQUEST_TIMEOUT`

O `configurar()` do agente roda no **import** de `src.graph` e chama `mlflow.set_experiment()`, que
faz HTTP. Os defaults do cliente MLflow são `timeout=120s` e `max_retries=7`: com o MLflow fora do
ar, isso bloqueia o import por **até 14 minutos**, o startup probe falha, e o contêiner entra em
loop de restart. O `try/except` que degrada o tracing nunca chegava a ser alcançado.

### `startup_probe` separado do `liveness_probe`

O boot carrega o grafo inteiro, com os imports pesados do LangChain. O startup probe dá até 5
minutos antes de declarar o contêiner morto; o liveness cuida do regime permanente.

## `app_mlflow.tf`

Ingress **interno** por padrão (`mlflow_public = false`). O agente alcança pelo FQDN interno, e esse
tráfego nunca sai do ambiente — então o toggle afeta só o acesso do **seu navegador** à UI, e ligá-lo
ou não jamais quebra o tracing.

### `--allowed-hosts` substitui o default, não soma

Esta linha custou duas rodadas de depuração. O MLflow 3.x tem um middleware anti-DNS-rebinding cujo
default cobre **28 padrões**: localhost, 127.0.0.1 **e os intervalos privados** (`10.*`, `172.16-18.*`,
`192.168.*`).

Passar `--allowed-hosts` **substitui esse default inteiro**. Uma primeira versão listou só o
hostname e localhost, o que derrubou a cobertura de IP privado — e o health probe do Container Apps
chega pelo IP do pod (`10.x`). Resultado: `ActivationFailed`, com o servidor rodando normalmente por
dentro e nenhum erro no log.

### Recursos: 0,5 CPU / 1,0 GiB

0,25/0,5 GiB não bastou: o contêiner subia, imprimia o banner do uvicorn e morria, acumulando
restarts com `ready: false` e sem erro no log — assinatura de OOM. O MLflow 3.x sobe vários workers,
cada um carregando SQLAlchemy, psycopg2 e os SDKs do Azure. Os pares válidos no ACA são 0.25/0.5Gi,
0.5/1.0Gi, 0.75/1.5Gi.

`--workers 1` pelo mesmo motivo: o agente é o único cliente.

### `--serve-artifacts`

O servidor do MLflow faz proxy do upload e do download dos artefatos, então **o agente nunca precisa
de credencial de storage**. Só o contêiner do MLflow toca o blob, usando a identidade gerenciada via
`AZURE_CLIENT_ID` — nenhuma chave de storage existe em lugar nenhum, nem no state.

## `outputs.tf`

Seis saídas. A que importa entender é o **`try()`**.

`devflow_url` referencia `ingress[0].fqdn`, que fica **null** quando o ingress está desabilitado. Sem
o `try`, um `az containerapp ingress disable` — útil como mitigação de emergência, e usado nesta
sessão — deixa o output inválido e **aborta qualquer apply seguinte**, inclusive o que reabilitaria
o ingress.

A regra que fica: **output não pode ser o que trava a recuperação.**

---

## Scripts que acompanham

### `carregar-env.sh`

Lê o `.env` da raiz e exporta as variáveis como `TF_VAR_*`, sem deixar arquivo no disco.

Não usa `set -a; source .env` de propósito: o `.env` pode ter espaço depois do `=` (`VAR= valor`), e
em shell isso significa "execute `valor` com VAR vazia" — foi o que derrubou a primeira tentativa de
deploy, com `command not found: gpt-5.4`. O `dotenv` lê corretamente e o `shlex.quote` protege
caracteres especiais das chaves.

### `token-producao.sh`

O token de produção fica **fora do `.env`**, e a razão é concreta.

O `.env` é o ambiente **local**, onde o token deve ficar **vazio** — é isso que permite o LangGraph
Studio conectar, porque autorização customizada também se aplica a ele e não há forma documentada de
mandar header customizado pela UI.

Mas o `carregar-env.sh` lia o token justamente do `.env`. Depois de esvaziá-lo, um `terraform apply`
mandaria token vazio para a Azure — **abrindo o endpoint**, já que o `auth.py` agora falha aberto.

A separação existe para não repetir isso. O `carregar-env.sh` avisa alto se a variável estiver vazia.

> O `auth.py` **não falha fechado**: sem `DEVFLOW_API_TOKEN` ele libera. Foi uma escolha consciente
> para não inutilizar o Studio, e o custo está registrado no topo do módulo. O servidor grita no log
> a cada subida sem token. Se você vir esse aviso num servidor exposto, é incidente.

---

## Operação

```bash
source infra/token-producao.sh && source infra/carregar-env.sh
cd infra && terraform apply -var="image_tag=<tag>" -var="mlflow_image_tag=<tag>"
```

**Religue o Postgres antes de qualquer apply.** Um servidor parado recusa a leitura do recurso
`database` e o plan falha com `ServerStoppedError`. A ordem é **aplicar → parar**, nunca o contrário.

```bash
az postgres flexible-server start -n <pg> -g rg-devflow   # antes do apply
az postgres flexible-server stop  -n <pg> -g rg-devflow   # depois, economiza ~US$12/mês
```

Atenção: a Azure **reinicia o servidor sozinho após 7 dias** parado.

Teardown:

```bash
terraform destroy
# se o state se perder:
az group delete --name rg-devflow --yes --no-wait
```
