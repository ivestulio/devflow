# Infraestrutura — DevFlow na Azure

Terraform que provisiona o DevFlow em Azure Container Apps, com MLflow ao lado.

> Explicação arquivo por arquivo dos `.tf`, com o motivo de cada decisão:
> [INFRAESTRUTURA.md](INFRAESTRUTURA.md)

## O que é criado

```
rg-devflow  (East US)
├── Container Registry (Basic)          imagens devflow e mlflow
├── Log Analytics (cota 0,5 GB/dia)     logs dos contêineres
├── Container Apps Environment
│   ├── devflow-agent    langgraph dev, porta 2024, ingress HTTPS + lista de IPs
│   └── devflow-mlflow   mlflow server, porta 5000, interno por padrão
├── PostgreSQL Flexible B1ms            backend do MLflow
├── Storage Account                     artefatos do MLflow
└── Managed Identity                    AcrPull + Storage Blob Data Contributor
```

**Custo estimado: ~US$26/mês** com o ambiente ocioso. O Postgres é 62% disso.

## O que NÃO é gerenciado

`azopenaiaulas` (Azure OpenAI, East US) e `azsearchai` (AI Search, Central US) já existiam,
no resource group `aulas`. Entram como **variáveis**, não como `data source` — então não estão no
grafo do Terraform, e o `terraform destroy` **não pode** tocá-los. Essa é a garantia.

## Rodar

```bash
# da raiz do repositório
source infra/carregar-env.sh     # lê o .env e exporta TF_VAR_*, sem deixar arquivo

cd infra
terraform init

# fase 1: registry (só na primeira vez)
terraform apply -var="image_tag=bootstrap" \
  -target=azurerm_resource_group.this -target=azurerm_container_registry.this

# imagens: build no servidor, em amd64
cd .. && TAG=$(git rev-parse --short HEAD)-$(date +%H%M)
az acr build --registry $(terraform -chdir=infra output -raw acr_name) --image "devflow:$TAG" --file Dockerfile .
az acr build --registry $(terraform -chdir=infra output -raw acr_name) --image "mlflow:$TAG"  --file Dockerfile.mlflow .

# fase 2: o resto
cd infra && terraform apply -var="image_tag=$TAG"
```

Deploys seguintes são só `az acr build` + `terraform apply -var image_tag=...`. A fase 1 acontece
uma vez na vida.

### Por que build no servidor

`az acr build` compila em `linux/amd64` na Azure. Um `docker build` num Mac Apple Silicon produz
`arm64`, que sobe no registry sem reclamar e depois falha no Container Apps com
`exec format error` — um erro que parece problema de infraestrutura e custa uma hora.

Bônus: o `az acr build` exclui `.venv` e `.git` do contexto por conta própria, então não sobem
734 MB pela rede.

## Segurança — leia antes de expor

O `langgraph dev` sobe com `LANGGRAPH_AUTH_TYPE=noop`: **sem autenticação**. E o
`CORS_ALLOW_ORIGINS` do langgraph-api também tem default `"*"`, com `allow_methods ["*"]`.
Ambos verificados no código-fonte.

A combinação é pior do que "alguém precisa descobrir a URL": com CORS aberto, **qualquer página que
você visite pode fazer o seu navegador disparar execuções no grafo** e gastar sua cota do Azure
OpenAI, sem nunca precisar saber o endereço.

Duas defesas, as duas necessárias:

1. **`ip_security_restriction`** — barra na borda, antes do contêiner. Só o IP em
   `allowed_ip_cidr` passa. O Studio funciona porque quem chama a API é o **seu navegador**.
2. **`CORS_ALLOW_ORIGINS=https://smith.langchain.com`** — fecha o `"*"`, de graça.

**O teto financeiro de verdade é a cota TPM do deployment `gpt-5.4`**, hoje em 150K. Ela fica fora
do Terraform (recurso preexistente). Se o endpoint vazar, é ela que limita o estrago.

> IP residencial muda. Quando mudar, rode `terraform apply` de novo — o `carregar-env.sh` relê o IP
> atual. Para dar aula fora, acrescente o IP da instituição **antes**.

A correção definitiva é de aplicação, não de infra: um bloco `auth` no `langgraph.json` com um
handler `@auth.authenticate` checando um bearer token — ~10 linhas de Python que desligam o `noop`.

## O state guarda segredos em texto claro

`terraform.tfstate` contém as chaves do Azure OpenAI e do AI Search e a senha do Postgres, **em
JSON legível**. `sensitive = true` só esconde da saída do terminal; não criptografa nada.

- O `.gitignore` cobre `infra/*.tfstate*` e `infra/*.tfvars`
- `chmod 600 infra/terraform.tfstate`
- **Rotacione as chaves ao fim do curso**

Tentei manter a senha fora do state com `ephemeral` + `administrator_password_wo`. Não funciona
aqui, e o `terraform validate` pega: o `secret` do Container App não aceita valor efêmero
(`secret.value` é só `optional, sensitive`, sem versão write-only neste provider). E como a string
de conexão com a senha precisa virar secret do app, ela cai no state de qualquer jeito.

A correção real é Key Vault — o `secret` aceita `key_vault_secret_id`, e aí só o URI do cofre entra
no state. Fica como próximo passo.

## Custo: o que fazer entre aulas

```bash
# para o Postgres (o compute para de ser cobrado; o storage continua)
az postgres flexible-server stop -n $(terraform output -raw postgres_name) -g rg-devflow

# fim do curso: derruba tudo
terraform destroy
```

Se o state se perder, o teardown ainda funciona, porque tudo vive num resource group só:

```bash
az group delete --name rg-devflow --yes --no-wait
```

## Detalhes que não são óbvios

- **`min_replicas = 1` no agente é corretude, não conforto.** O `interrupt()` estaciona a thread na
  memória. Se a revisão escalar a zero durante a pausa — e uma pessoa lendo um plano passa fácil dos
  300 s de cooldown — toda thread pausada evapora.
- **Identidade user-assigned, não system-assigned.** Com system-assigned o principal só existe
  depois do app criado, mas o `AcrPull` precisa valer no primeiro pull. Isso é circular e falha no
  primeiro apply.
- **Nunca `:latest`.** Com tag fixa o `template` não muda, o Terraform não cria revisão nova, e a
  imagem nova simplesmente não entra no ar.
- **O MLflow interno não atrapalha o tracing.** O agente chama `http://devflow-mlflow`, e tráfego
  dentro do ambiente nunca sai dele. O `mlflow_public` só afeta o acesso do seu navegador à UI.
- **A regra de firewall `0.0.0.0-0.0.0.0` do Postgres** é um valor mágico que significa "qualquer
  serviço Azure" — **inclusive de outras assinaturas**. Risco aceito e nomeado: banco de
  demonstração, senha de 32 caracteres, `destroy` no fim.
