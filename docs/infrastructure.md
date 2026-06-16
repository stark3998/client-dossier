# Infrastructure & Deployment

All infrastructure is defined as code in `infra/` using Terraform. A single `terraform apply` provisions every Azure resource the application needs.

---

## Azure Resources

| Resource | SKU / Config | Purpose |
| --- | --- | --- |
| Azure Container Registry | Basic | Stores Docker images for backend and frontend |
| Azure Container Apps Environment | Consumption | Hosts containerised workloads |
| Container App — Backend | 1–3 replicas, 1 vCPU / 2 GiB | FastAPI application |
| Container App — Frontend | 1–2 replicas, 0.25 vCPU / 0.5 GiB | React SPA served via nginx |
| Azure Cosmos DB | Serverless (NoSQL API) | Client knowledgebase and application state |
| Azure AI Search | Standard S1, semantic ranking on | Document index — hybrid BM25 + vector |
| Log Analytics Workspace | Pay-per-use | Centralised log sink |
| Application Insights | Connected to Log Analytics | OpenTelemetry traces and metrics |

### Terraform Modules

```
infra/modules/
├── acr/             # Container Registry
├── cosmos/          # Cosmos DB account + master database + clients container
├── search/          # Azure AI Search + semantic ranker profile
├── app_insights/    # Log Analytics workspace + Application Insights
└── container_apps/  # Container Apps environment + both apps
```

Per-client Cosmos databases (`client_{id}`) are created dynamically by the application when a client is onboarded — they are not provisioned by Terraform.

---

## Bootstrap Remote State

Run once before the first `terraform apply`:

```bash
az group create --name rg-tfstate --location australiaeast
az storage account create \
  --name sttfstateclientagent \
  --resource-group rg-tfstate \
  --sku Standard_LRS
az storage container create \
  --name tfstate \
  --account-name sttfstateclientagent
```

---

## Deploying

```bash
cd infra
cp terraform.tfvars.example terraform.tfvars
# Fill in terraform.tfvars: subscription_id, tenant_id, name_suffix, region
terraform init
terraform plan -out=tfplan
terraform apply tfplan
```

### Terraform Outputs

| Output | Description |
| --- | --- |
| `acr_login_server` | ACR login URL for image push |
| `cosmos_endpoint` | Cosmos DB endpoint |
| `search_endpoint` | Azure AI Search endpoint |
| `frontend_fqdn` | Public-facing frontend URL |
| `backend_fqdn` | Internal backend URL |
| `app_insights_connection_string` | Application Insights connection string |

---

## CI/CD Pipelines

Both pipelines live in `.github/workflows/`.

### CI — `ci.yml` (runs on every PR to `main`)

| Step | Tool |
| --- | --- |
| Backend lint | ruff + mypy |
| Backend tests | pytest with mock env vars |
| Frontend lint | eslint + `tsc --noEmit` |
| Docker build | smoke test — confirms images build cleanly |
| IaC validate | `terraform validate` |

### CD — `cd.yml` (runs on push to `main`)

| Step | Detail |
| --- | --- |
| Azure login | OIDC federated credentials — no static secrets in CI |
| Build images | Tagged with git SHA |
| Push to ACR | `docker push myacr.azurecr.io/backend:sha` |
| Terraform apply | Gated behind a GitHub Environment manual approval |
| Smoke test | `curl /health` and `curl /ready` on deployed services |

### Authentication in CI

OIDC federated credentials are used throughout — no service principal secrets are stored in GitHub. The pipeline authenticates via a federated identity token that the Azure AD app trusts for the specific repository and branch.

### Required GitHub Secrets

| Secret | Description |
| --- | --- |
| `AZURE_CLIENT_ID` | Service principal client ID |
| `AZURE_CLIENT_SECRET` | Service principal secret (Terraform ARM provider) |
| `AZURE_TENANT_ID` | Azure AD tenant ID |
| `AZURE_SUBSCRIPTION_ID` | Target subscription |
| `ACR_NAME` | Container Registry name (without `.azurecr.io`) |
| `ACR_REGISTRY` | Full ACR login server |
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI endpoint |
| `AZURE_OPENAI_API_KEY` | Azure OpenAI API key |
| `AZURE_OPENAI_DEPLOYMENT` | Chat model deployment name |
| `AZURE_OPENAI_EMBEDDING_DEPLOYMENT` | Embedding model deployment name |
| `ENTRA_TENANT_ID` | Entra tenant ID |
| `ENTRA_CLIENT_ID` | App registration client ID |
| `NAME_SUFFIX` | Resource name suffix (e.g., `prod01`) |
| `BACKEND_FQDN` | Deployed backend FQDN (used in smoke test) |
| `FRONTEND_FQDN` | Deployed frontend FQDN (used in smoke test) |

---

## Docker Images

Both images use multi-stage builds.

**Backend** (`backend/Dockerfile`):
- Stage 1: `python:3.11-slim` — install dependencies
- Stage 2: copy app, set `CMD uvicorn app.main:app`

**Frontend** (`frontend/Dockerfile`):
- Stage 1: `node:20-alpine` — `npm ci && npm run build`
- Stage 2: `nginx:alpine` — copy `dist/` and serve via `nginx.conf`

For local development with hot reload, `docker-compose.override.yml` mounts source volumes and runs Vite dev server instead of the production nginx image.

---

## Scaling

Container Apps scale on HTTP request concurrency. Default rules:

| App | Min replicas | Max replicas | Scale trigger |
| --- | --- | --- | --- |
| Backend | 1 | 3 | HTTP concurrency ≥ 10 |
| Frontend | 1 | 2 | HTTP concurrency ≥ 20 |

The backend holds stateful in-process resources (EventBus, MCPManager). Scaling to multiple replicas means each replica has its own in-memory state. For the current design this is acceptable — the scan progress dict and notification bus are per-replica. Persistent state (engagements, emails, memory) is always read from Cosmos DB.
