# Client Intelligence Agent

A full-stack AI-powered consulting intelligence platform. Ingests client documents, automatically extracts structured intelligence (stakeholders, action items, risks, engagement references), and exposes a streaming chat agent with full engagement lifecycle tracking. Designed to replace manual consulting workflows with automated document analysis, client memory, and dynamic tool extensibility.

## Architecture

```
Browser (React 18 SPA + Tailwind CSS)
  |
  +-- MSAL auth (Entra ID) or LOCAL_MODE bypass
  |
  +-- /api/* -----> FastAPI Backend (Python 3.11)
  |                   |
  |                   +-- Semantic Kernel (Agent Orchestration)
  |                   |     +-- SearchPlugin (Azure AI Search hybrid retrieval)
  |                   |     +-- MemoryPlugin (per-client Cosmos DB)
  |                   |     +-- FilePlugin (OneDrive document access)
  |                   |     +-- DocGenPlugin (PPTX/DOCX generation)
  |                   |     +-- Dynamic MCP Plugins (runtime-registered)
  |                   |     +-- Custom Prompt Tools (user-created)
  |                   |
  |                   +-- Analysis Service (LLM-based document intelligence)
  |                   +-- Ingestion Pipeline (parse -> chunk -> embed -> index)
  |                   +-- OpenTelemetry -> Azure Application Insights
  |
  +-- /ws/chat ----> WebSocket (streaming tokens + source citations)
  |
  +-- Azure AI Search (hybrid: vector 3072-dim + BM25 + semantic reranking)
  +-- Azure Cosmos DB (master DB + per-client isolated databases)
  +-- Azure OpenAI (gpt-4o chat + text-embedding-3-large)
  +-- Azure Container Apps (production runtime)
```

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, Vite 5, TypeScript 5, Tailwind CSS 3, Zustand, React Router 6, MSAL |
| Backend | Python 3.11, FastAPI, Semantic Kernel, Pydantic v2 |
| LLM | Azure OpenAI gpt-4o (chat) + text-embedding-3-large (embeddings, 3072 dims) |
| Search | Azure AI Search (hybrid vector + BM25 with semantic reranking) |
| Database | Azure Cosmos DB NoSQL (master + per-client isolated databases) |
| Observability | Azure Application Insights via OpenTelemetry SDK |
| Infrastructure | Terraform (azurerm ~>3.110), Azure Container Apps, ACR |
| CI/CD | GitHub Actions with OIDC federated credentials |
| Containers | Docker multi-stage builds, docker-compose for local dev |

## Project Structure

```
/
+-- backend/
|   +-- app/
|   |   +-- main.py                    # FastAPI app entry point
|   |   +-- config.py                  # pydantic-settings configuration
|   |   +-- telemetry.py               # OpenTelemetry + Azure Monitor bootstrap
|   |   +-- dependencies.py            # Dependency injection and service lifecycle
|   |   +-- api/
|   |   |   +-- health.py              # /health and /ready probes
|   |   |   +-- chat.py                # WebSocket streaming + REST chat
|   |   |   +-- files.py               # File browser + upload endpoint
|   |   |   +-- ingest.py              # Ingestion trigger + job polling
|   |   |   +-- clients.py             # Client listing + onboarding
|   |   |   +-- insights.py            # Client memory/insights retrieval
|   |   |   +-- memory.py              # Client memory CRUD
|   |   |   +-- analysis.py            # Document analysis results
|   |   |   +-- engagements.py         # Engagements, deliverables, risks, interactions CRUD
|   |   |   +-- timeline.py            # Unified chronological timeline
|   |   |   +-- mcp.py                 # MCP server management CRUD
|   |   |   +-- tools.py               # Tools listing, invocation, custom tool CRUD
|   |   |   +-- auth.py                # JWT validation middleware
|   |   +-- agent/
|   |   |   +-- kernel.py              # Semantic Kernel factory
|   |   |   +-- planner.py             # Agent orchestrator with streaming
|   |   |   +-- search_plugin.py       # Hybrid document search
|   |   |   +-- memory_plugin.py       # Client memory + engagement operations
|   |   |   +-- file_plugin.py         # File listing and preview
|   |   |   +-- docgen_plugin.py       # PPTX/DOCX generation
|   |   |   +-- mcp/
|   |   |       +-- base.py            # MCP plugin base class
|   |   |       +-- dynamic.py         # Generic dynamic MCP client
|   |   |       +-- ms_learn.py        # Microsoft Learn stub
|   |   |       +-- ms_graph.py        # Microsoft Graph stub
|   |   +-- ingestion/
|   |   |   +-- parser.py              # Multi-format document parser
|   |   |   +-- chunker.py             # Token-based chunker (tiktoken)
|   |   |   +-- embedder.py            # Batch embedding orchestrator
|   |   |   +-- pipeline.py            # End-to-end ingestion orchestrator
|   |   |   +-- watcher.py             # File system watcher (watchdog)
|   |   +-- services/
|   |   |   +-- cosmos.py              # CosmosClientManager (master + per-client DBs)
|   |   |   +-- search.py              # Azure AI Search wrapper
|   |   |   +-- embeddings.py          # Azure OpenAI embedding service
|   |   |   +-- analysis.py            # LLM document analysis service
|   |   |   +-- mcp_manager.py         # Dynamic MCP server lifecycle
|   |   |   +-- tool_manager.py        # Custom tool registration
|   |   +-- models/
|   |       +-- chunk.py               # Chunk and ChunkMetadata
|   |       +-- message.py             # ChatMessage, StreamEvent, SourceChip
|   |       +-- client_memory.py       # ClientMemory, Stakeholder, ActionItem
|   |       +-- source.py              # ParsedDocument, IngestJob
|   |       +-- analysis.py            # AnalysisResult, extracted entities
|   |       +-- engagement.py          # Engagement, Deliverable, Risk, Interaction
|   |       +-- mcp_server.py          # MCPServerConfig
|   |       +-- custom_tool.py         # CustomTool, ToolParameter
|   +-- tests/
|   +-- Dockerfile
|   +-- requirements.txt
|
+-- frontend/
|   +-- src/
|   |   +-- main.tsx                   # React entry point
|   |   +-- App.tsx                    # Router with all routes
|   |   +-- auth/                      # MSAL config + AuthProvider
|   |   +-- stores/clientStore.ts      # Zustand global state
|   |   +-- types/index.ts            # All TypeScript interfaces
|   |   +-- components/
|   |   |   +-- ClientDashboard.tsx    # Client list + onboarding (/)
|   |   |   +-- ClientWorkspace.tsx    # Three-panel workspace (/clients/:name)
|   |   |   +-- layout/               # AppShell, Sidebar (tabbed), InsightsPanel
|   |   |   +-- chat/                  # ChatTerminal, MessageBubble, StreamingResponse, ChatInput
|   |   |   +-- filebrowser/           # FileTree, FileNode, FilePreview, FileUpload
|   |   |   +-- insights/             # InsightsSummary, StakeholderList, ActionItems,
|   |   |   |                          # ProjectTracker, RiskRegister, InteractionTimeline,
|   |   |   |                          # EngagementTimeline, AnalysisResults
|   |   |   +-- settings/             # MCPServerPanel
|   |   |   +-- tools/                # ToolBrowser
|   |   |   +-- common/               # Toast notifications
|   |   +-- hooks/                     # useChat, useFileTree, useInsights, useEngagements,
|   |   |                              # useTimeline, useAnalysis, useMCPServers, useTools,
|   |   |                              # useFileUpload
|   |   +-- styles/globals.css
|   +-- nginx.conf
|   +-- Dockerfile / Dockerfile.dev
|   +-- package.json / tsconfig.json / vite.config.ts / tailwind.config.js
|
+-- infra/
|   +-- main.tf / variables.tf / outputs.tf
|   +-- modules/
|       +-- acr/                       # Azure Container Registry
|       +-- cosmos/                    # Cosmos DB (master DB + clients container)
|       +-- search/                    # Azure AI Search
|       +-- app_insights/             # Application Insights + Log Analytics
|       +-- container_apps/           # Container Apps (backend + frontend)
|
+-- .github/workflows/
|   +-- ci.yml                         # PR: lint, test, build, terraform validate
|   +-- cd.yml                         # Main: push ACR, terraform apply, smoke test
|
+-- scripts/
|   +-- create_search_index.py         # One-time search index setup
|   +-- seed_test_data.py              # Local dev test data
|
+-- docker-compose.yml                 # Production-like base
+-- docker-compose.override.yml        # Dev overrides (hot reload, LOCAL_MODE)
+-- .env.example
```

## Prerequisites

- Python 3.11+
- Node.js 20+
- Docker and Docker Compose
- Terraform >= 1.7.0 (for infrastructure provisioning)

## Quick Start (Local Development)

### 1. Clone and configure

```bash
git clone <repo-url> && cd Client-Agent
cp .env.example .env
```

Edit `.env` and set:

```env
LOCAL_MODE=true
DISABLE_TELEMETRY=true
ONEDRIVE_SYNC_PATH=./data
```

### 2. Seed test data

```bash
python scripts/seed_test_data.py
```

This creates a `Contoso` client folder with sample documents in `./data/`.

### 3. Option A: Docker Compose (recommended)

```bash
docker compose up
```

- Backend: http://localhost:8000 (hot reload via volume mount)
- Frontend: http://localhost:5173 (Vite dev server)
- API docs: http://localhost:8000/docs

### 3. Option B: Run services directly

```bash
# Terminal 1: Backend
cd backend
pip install -r requirements.txt
LOCAL_MODE=true DISABLE_TELEMETRY=true uvicorn app.main:app --reload --port 8000

# Terminal 2: Frontend
cd frontend
npm install
npm run dev
```

### 4. Open the application

Navigate to http://localhost:5173. In LOCAL_MODE, authentication is bypassed automatically.

## URL Routes

| Route | View |
|---|---|
| `/` | Client dashboard (list all clients, onboard new clients) |
| `/clients/:clientName` | Three-panel workspace (Files/Tools, Chat, Insights) |
| `/clients/:clientName/engagements` | Full-page Kanban engagement tracker |
| `/clients/:clientName/risks` | Full-page risk register |
| `/clients/:clientName/timeline` | Full-page interaction timeline |
| `/clients/:clientName/analysis` | Full-page document analysis results |

## API Reference

### Health Probes

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Liveness probe (always 200) |
| GET | `/ready` | Readiness probe (checks Cosmos DB + Search) |

### Client Management

| Method | Path | Description |
|---|---|---|
| GET | `/api/clients` | List all known clients (from filesystem + master DB) |
| POST | `/api/clients` | Onboard a new client (creates folder + isolated DB + initial memory) |

### Chat

| Method | Path | Description |
|---|---|---|
| WebSocket | `/ws/chat` | Streaming chat with source citations. Protocol: send `{type, content, client_name}`, receive `{type: token|source|done|error}` |
| POST | `/api/chat` | Non-streaming REST chat fallback |

### Files

| Method | Path | Description |
|---|---|---|
| GET | `/api/files/tree?path=` | Recursive file tree from OneDrive sync path |
| GET | `/api/files/preview?path=` | Extracted text preview of a document |
| POST | `/api/files/upload` | Upload a file (multipart: `file` + `client_name`). Auto-triggers ingestion + LLM analysis |

### Ingestion

| Method | Path | Description |
|---|---|---|
| POST | `/api/ingest` | Trigger ingestion for a path. Body: `{path, client_name}` |
| GET | `/api/ingest/{job_id}` | Poll ingestion job status and progress |

### Client Memory

| Method | Path | Description |
|---|---|---|
| GET | `/api/insights?client_name=` | Get full client memory (stakeholders, engagements, pain points, etc.) |
| GET | `/api/memory/{client_name}` | Get raw client memory document |
| PUT | `/api/memory/{client_name}` | Update client memory fields |

### Document Analysis

| Method | Path | Description |
|---|---|---|
| GET | `/api/analysis/{client_name}` | List all LLM analysis results for a client |
| GET | `/api/analysis/{client_name}/{id}` | Get a specific analysis result |

### Engagements

| Method | Path | Description |
|---|---|---|
| GET | `/api/clients/{name}/engagements` | List all engagements |
| POST | `/api/clients/{name}/engagements` | Create an engagement |
| GET | `/api/clients/{name}/engagements/{id}` | Get engagement details |
| PUT | `/api/clients/{name}/engagements/{id}` | Update an engagement |
| DELETE | `/api/clients/{name}/engagements/{id}` | Delete an engagement |

### Deliverables

| Method | Path | Description |
|---|---|---|
| GET | `/api/clients/{name}/engagements/{id}/deliverables` | List deliverables for an engagement |
| POST | `/api/clients/{name}/engagements/{id}/deliverables` | Create a deliverable |
| PUT | `/api/clients/{name}/deliverables/{id}` | Update a deliverable |

### Risks

| Method | Path | Description |
|---|---|---|
| GET | `/api/clients/{name}/engagements/{id}/risks` | List risks for an engagement |
| POST | `/api/clients/{name}/engagements/{id}/risks` | Create a risk |
| GET | `/api/clients/{name}/risks` | List all risks across all engagements |

### Status Updates

| Method | Path | Description |
|---|---|---|
| GET | `/api/clients/{name}/engagements/{id}/status-updates` | List status updates |
| POST | `/api/clients/{name}/engagements/{id}/status-updates` | Create a status update |

### Interactions

| Method | Path | Description |
|---|---|---|
| GET | `/api/clients/{name}/interactions` | List all client interactions |
| POST | `/api/clients/{name}/interactions` | Log a new interaction |

### Timeline

| Method | Path | Description |
|---|---|---|
| GET | `/api/clients/{name}/timeline?limit=50` | Unified timeline merging interactions, status updates, and analysis events |

### MCP Server Management

| Method | Path | Description |
|---|---|---|
| GET | `/api/mcp/servers` | List all configured MCP servers |
| POST | `/api/mcp/servers` | Register a new MCP server |
| GET | `/api/mcp/servers/{id}` | Get server details |
| PUT | `/api/mcp/servers/{id}` | Update server configuration |
| DELETE | `/api/mcp/servers/{id}` | Remove a server |
| POST | `/api/mcp/servers/{id}/test` | Test server connectivity |

### Tools Management

| Method | Path | Description |
|---|---|---|
| GET | `/api/tools` | List all available tools (built-in + MCP + custom) |
| GET | `/api/tools/{plugin}/{function}` | Get tool details and parameter schema |
| POST | `/api/tools/invoke` | Invoke a tool. Body: `{plugin, function, arguments}` |
| POST | `/api/tools/custom` | Create a custom prompt-based tool |
| PUT | `/api/tools/custom/{id}` | Update a custom tool |
| DELETE | `/api/tools/custom/{id}` | Delete a custom tool |

## Database Architecture

### Master Database (`clientagent`)

Provisioned by Terraform. Contains shared configuration.

| Container | Partition Key | Purpose |
|---|---|---|
| `clients` | `/id` | Client registry and metadata |
| `mcp_servers` | `/id` | MCP server configurations (shared across clients) |
| `custom_tools` | `/id` | Custom tool definitions (shared across clients) |

### Per-Client Databases (`client_{id}`)

Created dynamically when a client is onboarded. Full data isolation per client.

| Container | Partition Key | Purpose |
|---|---|---|
| `memories` | `/id` | Client memory (stakeholders, engagements, pain points, priorities) |
| `doc_index` | `/file_path` | Document tracking with content hashes for incremental sync |
| `analyses` | `/file_path` | LLM analysis results per document |
| `engagements` | `/id` | Engagement/project lifecycle tracking |
| `deliverables` | `/engagement_id` | Deliverable tracking per engagement |
| `risks` | `/engagement_id` | Risk register per engagement |
| `status_updates` | `/engagement_id` | Status update timeline per engagement |
| `interactions` | `/id` | Meeting, call, email, and workshop logs |

## Agent Capabilities

The Semantic Kernel agent has these built-in tools:

| Tool | Plugin | Description |
|---|---|---|
| `search_documents` | Search | Hybrid vector + BM25 search across indexed client documents |
| `recall_client_memory` | Memory | Retrieve full client memory (stakeholders, priorities, etc.) |
| `update_client_memory` | Memory | Store new facts about a client |
| `recall_engagements` | Memory | List all engagements with phase and status |
| `create_engagement` | Memory | Create a new engagement/project |
| `recall_risks` | Memory | List risks, optionally by engagement |
| `recall_recent_interactions` | Memory | View recent meetings, calls, emails |
| `log_interaction` | Memory | Record a client interaction |
| `list_files` | Files | Browse available client documents |
| `read_file_preview` | Files | Preview document contents |
| `generate_presentation` | DocumentGeneration | Create PowerPoint presentations |
| `generate_document` | DocumentGeneration | Create Word documents |
| Dynamic MCP tools | MCP_{name} | Tools from registered MCP servers |
| Custom tools | CustomTools | User-created prompt-based tools |

## Document Analysis Pipeline

When a file is uploaded or ingested, the system runs a two-stage pipeline:

### Stage 1: Ingestion
1. Parse document (supports .docx, .pptx, .xlsx, .pdf, .msg, .eml, .txt, .md)
2. Chunk at section boundaries (800 tokens max, 100-token overlap)
3. Embed with text-embedding-3-large (3072 dimensions, batches of 16)
4. Upsert to Azure AI Search (hybrid index)
5. Track in per-client `doc_index` container

### Stage 2: LLM Analysis
1. Send document text to Azure OpenAI with structured extraction prompt
2. Extract: stakeholders (name/title/email), action items, risks, dates, document classification
3. Store analysis result in per-client `analyses` container
4. Auto-merge findings into client memory (deduplicates by name/description)

### Supported Document Types

| Extension | Parser | Notes |
|---|---|---|
| `.docx` | python-docx | Preserves heading hierarchy |
| `.pptx` | python-pptx | One chunk per slide |
| `.xlsx` | openpyxl | One chunk per sheet, column headers as prefix |
| `.pdf` | pdfplumber (fallback: pymupdf) | Per-page extraction |
| `.msg` | extract-msg | Subject + body + sender |
| `.eml` | email stdlib | Subject + body + sender |
| `.txt` / `.md` | stdlib | Raw text |

## MCP Server Integration

MCP (Model Context Protocol) servers can be added at runtime from the UI. The system supports any MCP-compliant HTTP endpoint.

### Adding an MCP Server

1. Click the "MCP" label in the status bar to open the MCP panel
2. Click "Add MCP Server"
3. Enter: name, endpoint URL, optional description
4. The server is registered with the Semantic Kernel and its tools become available to the agent immediately

### Auth Types

| Type | Config |
|---|---|
| `none` | No authentication |
| `api_key` | `{header_name: "X-API-Key", api_key: "..."}` |
| `bearer` | `{token: "..."}` |

### Built-in MCP Stubs

- **MS Learn** -- Microsoft Learn documentation search (enable via `MCP_MS_LEARN_ENABLED`)
- **MS Graph** -- Microsoft Graph email/calendar search (enable via `MCP_MS_GRAPH_ENABLED`)

## Custom Tools

Create prompt-based tools from the UI that become available to the agent.

### Creating a Custom Tool

1. Open the "Tools" tab in the sidebar
2. Click "Create Custom Tool"
3. Enter: name, description, prompt template
4. Use `{{$input}}` for variable substitution in the prompt template
5. The tool is registered as a Semantic Kernel prompt function and persisted to Cosmos DB

### Example Custom Tool

```
Name: summarize_for_executive
Description: Summarize client information for an executive audience
Prompt Template: Summarize the following client information for a C-suite executive briefing. Focus on strategic impact, financial implications, and recommended next steps. Keep it under 200 words.

Client info: {{$input}}
```

## Environment Variables

| Variable | Default | Required | Description |
|---|---|---|---|
| `AZURE_OPENAI_ENDPOINT` | | Yes (non-local) | Azure OpenAI endpoint URL |
| `AZURE_OPENAI_API_KEY` | | Yes (non-local) | Azure OpenAI API key |
| `AZURE_OPENAI_DEPLOYMENT` | `gpt-4o` | No | Chat model deployment name |
| `AZURE_OPENAI_EMBEDDING_DEPLOYMENT` | `text-embedding-3-large` | No | Embedding model deployment |
| `AZURE_OPENAI_API_VERSION` | `2024-08-01-preview` | No | API version |
| `AZURE_SEARCH_ENDPOINT` | | Yes (non-local) | Azure AI Search endpoint |
| `AZURE_SEARCH_API_KEY` | | Yes (non-local) | Azure AI Search admin key |
| `AZURE_SEARCH_INDEX_NAME` | `client-knowledge` | No | Search index name |
| `COSMOS_ENDPOINT` | | Yes (non-local) | Cosmos DB endpoint |
| `COSMOS_KEY` | | Yes (non-local) | Cosmos DB key |
| `COSMOS_DB_NAME` | `clientagent` | No | Master database name |
| `APPLICATIONINSIGHTS_CONNECTION_STRING` | | No | App Insights connection string |
| `DISABLE_TELEMETRY` | `false` | No | Disable OpenTelemetry |
| `ONEDRIVE_SYNC_PATH` | `/mnt/onedrive` | No | Base path for client documents |
| `ENTRA_CLIENT_ID` | | Yes (non-local) | App registration client ID |
| `ENTRA_TENANT_ID` | | Yes (non-local) | Azure AD tenant ID |
| `ENTRA_CLIENT_SECRET` | | Yes (non-local) | App registration secret |
| `LOCAL_MODE` | `false` | No | Skip auth, use in-memory stubs |
| `MCP_MS_LEARN_ENABLED` | `false` | No | Enable MS Learn MCP plugin |
| `MCP_MS_LEARN_ENDPOINT` | | No | MS Learn MCP endpoint URL |
| `MCP_MS_GRAPH_ENABLED` | `false` | No | Enable MS Graph MCP plugin |
| `MCP_MS_GRAPH_ENDPOINT` | | No | MS Graph MCP endpoint URL |
| `FRONTEND_URL` | `http://localhost:5173` | No | Allowed CORS origin |
| `BACKEND_PORT` | `8000` | No | Backend listen port |
| `LOG_LEVEL` | `INFO` | No | Python logging level |

In LOCAL_MODE, all Azure services are replaced with in-memory stubs. No Azure credentials required.

## Infrastructure (Terraform)

### Bootstrap Remote State

Before first `terraform apply`, create the storage account for state:

```bash
az group create --name rg-tfstate --location australiaeast
az storage account create --name sttfstateclientagent --resource-group rg-tfstate --sku Standard_LRS
az storage container create --name tfstate --account-name sttfstateclientagent
```

### Deploy

```bash
cd infra
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your values

terraform init
terraform plan -out=tfplan
terraform apply tfplan
```

### Terraform Modules

| Module | Resources |
|---|---|
| `acr` | Azure Container Registry (Basic SKU) |
| `cosmos` | Cosmos DB serverless account + master database + `clients` container |
| `search` | Azure AI Search (Standard SKU) |
| `app_insights` | Log Analytics workspace + Application Insights |
| `container_apps` | Container Apps environment + backend (1-3 replicas, 1 CPU, 2Gi) + frontend (1-2 replicas, 0.25 CPU, 0.5Gi) |

Per-client databases are created dynamically by the application on client onboard.

### Outputs

| Output | Description |
|---|---|
| `acr_login_server` | ACR login URL |
| `cosmos_endpoint` | Cosmos DB endpoint |
| `search_endpoint` | Azure AI Search endpoint |
| `frontend_fqdn` | Public frontend URL |
| `backend_fqdn` | Internal backend URL |
| `app_insights_connection_string` | App Insights connection string |

## CI/CD

### CI Pipeline (`.github/workflows/ci.yml`)

Runs on every PR to `main`:

1. **Lint backend** -- ruff + mypy
2. **Test backend** -- pytest with mock env vars
3. **Lint frontend** -- eslint + tsc --noEmit
4. **Build images** -- Docker build smoke test for both services
5. **Terraform validate** -- syntax and config validation

### CD Pipeline (`.github/workflows/cd.yml`)

Runs on push to `main`:

1. **Azure OIDC login** -- passwordless federated credentials
2. **Build and push** -- Docker images tagged with git SHA to ACR
3. **Terraform apply** -- deploy infrastructure changes (requires manual approval via GitHub Environments)
4. **Smoke test** -- curl health endpoints on deployed services

### Required GitHub Secrets

| Secret | Description |
|---|---|
| `AZURE_CLIENT_ID` | Service principal client ID (OIDC federated) |
| `AZURE_CLIENT_SECRET` | Service principal secret (for Terraform ARM provider) |
| `AZURE_TENANT_ID` | Azure AD tenant ID |
| `AZURE_SUBSCRIPTION_ID` | Target subscription |
| `ACR_NAME` | Container Registry name (without `.azurecr.io`) |
| `ACR_REGISTRY` | Full ACR login server (e.g., `myacr.azurecr.io`) |
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI endpoint |
| `AZURE_OPENAI_API_KEY` | Azure OpenAI API key |
| `AZURE_OPENAI_DEPLOYMENT` | Chat model deployment name |
| `AZURE_OPENAI_EMBEDDING_DEPLOYMENT` | Embedding model deployment |
| `ENTRA_TENANT_ID` | Entra tenant ID |
| `ENTRA_CLIENT_ID` | App registration client ID |
| `ENTRA_CLIENT_SECRET` | App registration secret |
| `NAME_SUFFIX` | Resource name suffix (e.g., `prod01`) |
| `BACKEND_FQDN` | Deployed backend FQDN (for smoke test) |
| `FRONTEND_FQDN` | Deployed frontend FQDN (for smoke test) |

### OIDC Setup

Set up federated credentials on the service principal so `azure/login@v2` uses passwordless auth:

1. Create an Azure AD App Registration for GitHub Actions
2. Add federated credential: issuer `https://token.actions.githubusercontent.com`, subject `repo:<org>/<repo>:ref:refs/heads/main`
3. Grant `Contributor` role on the resource group and `AcrPush` on the ACR

## WebSocket Chat Protocol

### Client to Server

```json
{
  "type": "message",
  "content": "What are the key risks for Contoso?",
  "client_name": "Contoso"
}
```

### Server to Client

```json
{"type": "source", "source": {"file_path": "Contoso/status_report.docx", "section_title": "Risks", "page_number": 3, "excerpt": "...", "score": 0.92}}
{"type": "token", "content": "Based on "}
{"type": "token", "content": "the latest "}
{"type": "token", "content": "status report..."}
{"type": "done"}
```

Sources are emitted before or alongside tokens, never after `done`.

## Design Tokens

```css
--color-bg-primary:    #0d0d0d
--color-bg-secondary:  #161616
--color-bg-panel:      #1a1a1a
--color-accent:        #86BC25    /* Primary accent (Deloitte Green) */
--color-accent-bright: #86EB22    /* Progress indicators */
--color-accent-blue:   #00A3E0    /* Source chips, links */
--font-ui:   'DM Sans', system-ui, sans-serif
--font-mono: 'JetBrains Mono', 'Fira Code', monospace
```

## Testing

```bash
# Backend tests
cd backend
LOCAL_MODE=true DISABLE_TELEMETRY=true pytest tests -v

# Frontend type check
cd frontend
npm run typecheck

# Frontend lint
npm run lint
```

## Key Design Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Per-client databases | Isolated Cosmos DBs per client | Data isolation, independent scaling, compliance |
| Auto-analysis | LLM extracts entities on upload, auto-merges into memory | Removes manual data entry, builds intelligence passively |
| Dynamic MCP | Hot-reload MCP servers at runtime | No restart needed to add integrations |
| Custom tools | Prompt templates, not Python code | Security (no arbitrary code execution) + SK native support |
| 3072-dim embeddings | Full fidelity from text-embedding-3-large | Best retrieval quality |
| LOCAL_MODE | Interface substitution at service layer | Same code paths tested locally, no conditional branches in business logic |
| URL-based routing | React Router with `/clients/:name/*` | Bookmarkable views, browser back/forward navigation |
| Chat history | localStorage per client | No server-side storage needed for conversation state |
