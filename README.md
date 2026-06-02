# Client Intelligence Agent

A full-stack AI-powered consulting intelligence platform. Ingests client documents,
automatically extracts structured intelligence (stakeholders, action items, risks,
engagement references), and exposes a streaming chat agent with full engagement lifecycle
tracking, communication scanning, and a built-in MCP server. Designed to replace manual
consulting workflows with automated document analysis, client memory, and dynamic tool
extensibility.

## Architecture

```text
+------------------------------------------------------------------+
|                        Browser (SPA)                             |
|  React 18 + Vite 5 + TypeScript + Tailwind CSS + Zustand + MSAL |
+------------------+------------------+---------------------------+
                   |  REST /api/*      |  WebSocket /ws/chat
                   |  Auth: Bearer JWT |  Auth: ?token=JWT
                   v                  v
+------------------------------------------------------------------+
|                    FastAPI Backend  (Python 3.11)                |
|                                                                  |
|  AuthMiddleware (Entra ID JWT / MCP_API_KEY / LOCAL_MODE)        |
|                                                                  |
|  AgentPlanner + Semantic Kernel v1.x                             |
|    SearchPlugin   MemoryPlugin   FilePlugin   DocGenPlugin        |
|    EngagementPlugin  ReportingPlugin  WebSearchPlugin            |
|    CommunicationPlugin   MCP_{name} plugins  CustomTools         |
|    ReAct loop (max 10 iter) | Plan-and-Execute (complex queries) |
|                                                                  |
|  Built-in MCP Server (/mcp/sse, /mcp/message)                   |
|    14 tools — Search, Memory, Engagements, Comms, Reporting      |
|                                                                  |
|  MCPManager — dynamic external MCP servers from Cosmos           |
|  CommunicationScanner — Outlook win32com + MS Graph API          |
|  AlertChecker — stale client / risk alerts every 900s            |
|  EventBus (in-process) -> WebSocket push -> notification bell    |
|                                                                  |
+------+--------+--------+--------+---------+--------------------+
       |        |        |        |         |
       v        v        v        v         v
  Cosmos DB  AI Search  Azure   App      OneDrive
  NoSQL      hybrid     OpenAI  Insights  sync path
  master +   BM25 +     gpt-4o  OTel
  per-client vector     embed-  traces
  isolation  3072-dim   3-large
```

### Startup Sequence

On first request, `dependencies.py` initializes services in order:
CosmosClientManager -> EventBus -> SearchService -> EmbeddingService ->
create_kernel() -> 8 SK plugins -> AgentPlanner -> MCPManager (loads saved servers) ->
ToolManager (loads custom tools) -> AlertChecker -> CommunicationScanner ->
EventBus subscriber wiring -> optional FileWatcher.

See [docs/architecture.md](docs/architecture.md) for the full deep-dive reference.

## Tech Stack

| Layer | Technology |
| --- | --- |
| Frontend | React 18, Vite 5, TypeScript 5, Tailwind CSS 3, Zustand, React Router 6, MSAL |
| Backend | Python 3.11, FastAPI, Semantic Kernel v1.x, Pydantic v2 |
| LLM | Azure OpenAI gpt-4o (chat, max_tokens=4096, temp=0.3) + text-embedding-3-large (3072 dims) |
| Search | Azure AI Search (hybrid: BM25 + vector HNSW + semantic reranking) |
| Database | Azure Cosmos DB NoSQL (master `clientagent` DB + per-client `client_{id}` DBs) |
| Observability | Azure Application Insights via OpenTelemetry SDK |
| Infrastructure | Terraform (azurerm ~>3.110), Azure Container Apps, ACR |
| CI/CD | GitHub Actions with OIDC federated credentials |
| Containers | Docker multi-stage builds, docker-compose for local dev |
| Communication | Outlook win32com (local) + Microsoft Graph API (fallback/Teams) |

## Project Structure

```text
/
+-- backend/
|   +-- app/
|   |   +-- main.py                    # FastAPI app, 16 routers mounted
|   |   +-- config.py                  # pydantic-settings (all env vars)
|   |   +-- telemetry.py               # OpenTelemetry + Azure Monitor bootstrap
|   |   +-- dependencies.py            # Service lifecycle + startup_services()
|   |   +-- api/
|   |   |   +-- health.py              # /health and /ready probes
|   |   |   +-- chat.py                # WebSocket /ws/chat + REST /api/chat
|   |   |   +-- files.py               # /api/files — tree, preview, upload
|   |   |   +-- ingest.py              # /api/ingest — trigger + job polling
|   |   |   +-- clients.py             # /api/clients — list, onboard
|   |   |   +-- insights.py            # /api/insights — client memory
|   |   |   +-- memory.py              # /api/memory — memory CRUD
|   |   |   +-- analysis.py            # /api/analysis — document analysis results
|   |   |   +-- engagements.py         # /api/clients/{name}/engagements + deliverables/risks/interactions
|   |   |   +-- timeline.py            # /api/clients/{name}/timeline
|   |   |   +-- mcp.py                 # /api/mcp — external server management + invoke
|   |   |   +-- tools.py               # /api/tools — listing, invocation, custom tool CRUD
|   |   |   +-- action_items.py        # /api/clients/{name}/action_items
|   |   |   +-- client_health.py       # /api/client_health/{name}
|   |   |   +-- notifications.py       # /api/notifications + /ws/notifications
|   |   |   +-- briefing.py            # /api/briefing/{name}
|   |   |   +-- communication.py       # /api/communication/{name}/* + /ws/communication/*
|   |   |   +-- auth.py                # AuthMiddleware (JWT/MCP_API_KEY/LOCAL_MODE)
|   |   +-- agent/
|   |   |   +-- kernel.py              # Semantic Kernel factory + execution settings
|   |   |   +-- planner.py             # AgentPlanner — routes to ReAct or Plan-Execute
|   |   |   +-- planner_executor.py    # plan_and_execute() for complex queries
|   |   |   +-- react_loop.py          # ReAct loop — max 10 iterations, manual tool invoke
|   |   |   +-- context_injector.py    # Builds 2000-token client context block
|   |   |   +-- conversation_manager.py# Summarizes history when > 8000 tokens
|   |   |   +-- query_rewriter.py      # LLM query rewrite for better retrieval
|   |   |   +-- search_plugin.py       # Hybrid search with QueryRewriter
|   |   |   +-- memory_plugin.py       # Client memory + engagement operations
|   |   |   +-- file_plugin.py         # File listing and preview
|   |   |   +-- docgen_plugin.py       # PPTX/DOCX generation
|   |   |   +-- engagement_plugin.py   # Engagement lifecycle (publishes EventBus events)
|   |   |   +-- reporting_plugin.py    # Report generation
|   |   |   +-- web_search_plugin.py   # Tavily API external search
|   |   |   +-- communication_plugin.py# Email/Teams/calendar from CommunicationAccess
|   |   |   +-- communication_scanner.py# Background email/calendar polling
|   |   |   +-- alert_checker.py       # Stale client + risk alert background task
|   |   |   +-- mcp/
|   |   |       +-- base.py            # MCPPluginBase
|   |   |       +-- dynamic.py         # DynamicMCPPlugin (REST + SSE protocols)
|   |   |       +-- ms_learn.py        # MS Learn stub
|   |   |       +-- ms_graph.py        # MS Graph stub
|   |   +-- mcp_server/
|   |   |   +-- server.py              # Built-in MCP server: 14 tools, dispatch
|   |   |   +-- router.py              # /mcp/sse, /mcp/message, /mcp/tools, /mcp/health
|   |   |   +-- logger.py              # MCP audit log (tool_call_start/success/error)
|   |   |   +-- tools/                 # One file per tool category
|   |   |       +-- search.py, ingest.py, memory.py, files.py, insights.py
|   |   |       +-- communications.py, engagements.py, timeline.py
|   |   |       +-- action_items.py, client_health.py, briefing.py, clients.py
|   |   +-- ingestion/
|   |   |   +-- parser.py              # Multi-format document parser
|   |   |   +-- chunker.py             # Token-based chunker (tiktoken, 800 tok / 100 overlap)
|   |   |   +-- embedder.py            # Batch embedding (batch_size=16)
|   |   |   +-- pipeline.py            # End-to-end ingestion orchestrator
|   |   |   +-- watcher.py             # watchdog FileWatcher for OneDrive sync path
|   |   +-- services/
|   |   |   +-- cosmos.py              # CosmosClientManager + local stub
|   |   |   +-- search.py              # Azure AI Search wrapper + local stub
|   |   |   +-- embeddings.py          # Azure OpenAI embedding + local stub
|   |   |   +-- analysis.py            # LLM document analysis service
|   |   |   +-- mcp_manager.py         # Dynamic MCP server lifecycle (load/connect/register)
|   |   |   +-- tool_manager.py        # Custom tool load/register
|   |   |   +-- event_bus.py           # In-process pub/sub EventBus
|   |   |   +-- outlook_win32.py       # Outlook win32com email/calendar access
|   |   |   +-- graph_api_service.py   # Microsoft Graph API email/calendar fallback
|   |   |   +-- communication_access.py# Facade: win32com first, Graph API fallback
|   |   +-- models/
|   |       +-- chunk.py, message.py, client_memory.py, source.py
|   |       +-- analysis.py, engagement.py, mcp_server.py
|   |       +-- custom_tool.py, communication.py, event.py
|   +-- tests/
|   +-- Dockerfile
|   +-- requirements.txt
|
+-- frontend/
|   +-- src/
|   |   +-- main.tsx                   # React entry, MsalProvider, ThemeProvider
|   |   +-- App.tsx                    # React Router — all routes
|   |   +-- auth/                      # MSAL config + AuthProvider + apiFetch + getAuthenticatedWsUrl
|   |   +-- stores/clientStore.ts      # Zustand global store (chat, files, mcp, ui, notifications)
|   |   +-- types/index.ts             # All TypeScript interfaces
|   |   +-- components/
|   |   |   +-- ClientDashboard.tsx    # Client grid + onboarding wizard (/)
|   |   |   +-- ClientWorkspace.tsx    # Three-panel workspace (/clients/:name)
|   |   |   +-- layout/               # AppShell, Sidebar (tabbed), InsightsPanel
|   |   |   +-- chat/                 # ChatTerminal, MessageBubble, StreamingResponse,
|   |   |   |                         # ReasoningSteps, ChatInput
|   |   |   +-- filebrowser/          # FileTree, FileNode, FilePreview, FileUpload
|   |   |   +-- insights/             # InsightsSummary, StakeholderList, ActionItems,
|   |   |   |                         # ProjectTracker (Kanban), RiskRegister,
|   |   |   |                         # InteractionTimeline, AnalysisResults
|   |   |   +-- communication/        # CommunicationView, thread viewer
|   |   |   +-- tools/                # ToolBrowser (Agent Tools + MCP Tools tabs)
|   |   |   +-- settings/             # MCPServerPanel
|   |   |   +-- notifications/        # Notification bell + list
|   |   |   +-- common/               # Toast notifications
|   |   +-- hooks/
|   |       +-- useChat.ts            # WebSocket connection, event routing, auto-reconnect
|   |       +-- useFileTree.ts, useInsights.ts, useEngagements.ts
|   |       +-- useTimeline.ts, useAnalysis.ts, useMCPServers.ts
|   |       +-- useTools.ts, useFileUpload.ts
|   +-- nginx.conf
|   +-- Dockerfile / Dockerfile.dev
|   +-- package.json / tsconfig.json / vite.config.ts / tailwind.config.js
|
+-- infra/
|   +-- main.tf / variables.tf / outputs.tf
|   +-- modules/
|       +-- acr/            # Azure Container Registry
|       +-- cosmos/         # Cosmos DB account + master database
|       +-- search/         # Azure AI Search (Standard SKU)
|       +-- app_insights/   # Log Analytics + Application Insights
|       +-- container_apps/ # Backend (1-3 replicas, 1 CPU/2Gi) + Frontend (1-2 replicas)
|
+-- .github/workflows/
|   +-- ci.yml              # PR: ruff, mypy, pytest, eslint, tsc, docker build, tf validate
|   +-- cd.yml              # Main: OIDC login, ACR push, terraform apply, smoke test
|
+-- scripts/
|   +-- create_search_index.py    # One-time index setup
|   +-- seed_test_data.py         # Local dev: creates Contoso client with sample docs
|
+-- docs/
|   +-- architecture.md           # Deep-dive architecture + all data flows (this file's companion)
|   +-- knowledge-pipeline.md     # Ingestion pipeline internals
|
+-- docker-compose.yml            # Production-like base
+-- docker-compose.override.yml   # Dev overrides (hot reload, LOCAL_MODE)
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

- Backend: <http://localhost:8000> (hot reload via volume mount)
- Frontend: <http://localhost:5173> (Vite dev server)
- API docs: <http://localhost:8000/docs>

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

Navigate to <http://localhost:5173>. In LOCAL_MODE, authentication is bypassed automatically.

## URL Routes

| Route | View |
| --- | --- |
| `/` | Client dashboard (list all clients, onboard new clients) |
| `/clients/:clientName` | Three-panel workspace (Files/Tools, Chat, Insights) |
| `/clients/:clientName/engagements` | Full-page Kanban engagement tracker |
| `/clients/:clientName/risks` | Full-page risk register |
| `/clients/:clientName/timeline` | Full-page interaction timeline |
| `/clients/:clientName/analysis` | Full-page document analysis results |
| `/clients/:clientName/communications` | Email/meeting/draft communication view |

## API Reference

### Health Probes

| Method | Path | Description |
| --- | --- | --- |
| GET | `/health` | Liveness probe (always 200) |
| GET | `/ready` | Readiness probe (checks Cosmos DB + Search) |

### Client Management

| Method | Path | Description |
| --- | --- | --- |
| GET | `/api/clients` | List all known clients (filesystem + master DB) |
| POST | `/api/clients` | Onboard a new client (creates folder + isolated DB + initial memory) |

### Chat

| Method | Path | Description |
| --- | --- | --- |
| WebSocket | `/ws/chat` | Streaming chat. Send `{type, content, client_name}`. See WebSocket Protocol section. |
| POST | `/api/chat` | Non-streaming REST chat fallback |

### Files

| Method | Path | Description |
| --- | --- | --- |
| GET | `/api/files/tree?path=` | Recursive file tree from OneDrive sync path |
| GET | `/api/files/preview?path=` | Extracted text preview of a document |
| POST | `/api/files/upload` | Upload file (multipart: `file` + `client_name`). Auto-triggers ingestion + LLM analysis. |

### Ingestion

| Method | Path | Description |
| --- | --- | --- |
| POST | `/api/ingest` | Trigger ingestion for a path. Body: `{path, client_name, mode}` |
| GET | `/api/ingest/{job_id}` | Poll ingestion job status and progress |

### Client Memory

| Method | Path | Description |
| --- | --- | --- |
| GET | `/api/insights?client_name=` | Full client memory (stakeholders, engagements, pain points, etc.) |
| GET | `/api/memory/{client_name}` | Raw client memory document |
| PUT | `/api/memory/{client_name}` | Update client memory fields |

### Document Analysis

| Method | Path | Description |
| --- | --- | --- |
| GET | `/api/analysis/{client_name}` | List all LLM analysis results for a client |
| GET | `/api/analysis/{client_name}/{id}` | Get a specific analysis result |

### Engagements

| Method | Path | Description |
| --- | --- | --- |
| GET | `/api/clients/{name}/engagements` | List all engagements |
| POST | `/api/clients/{name}/engagements` | Create an engagement |
| GET | `/api/clients/{name}/engagements/{id}` | Get engagement details |
| PUT | `/api/clients/{name}/engagements/{id}` | Update an engagement |
| DELETE | `/api/clients/{name}/engagements/{id}` | Delete an engagement |

### Deliverables

| Method | Path | Description |
| --- | --- | --- |
| GET | `/api/clients/{name}/engagements/{id}/deliverables` | List deliverables for an engagement |
| POST | `/api/clients/{name}/engagements/{id}/deliverables` | Create a deliverable |
| PUT | `/api/clients/{name}/deliverables/{id}` | Update a deliverable |

### Risks

| Method | Path | Description |
| --- | --- | --- |
| GET | `/api/clients/{name}/engagements/{id}/risks` | List risks for an engagement |
| POST | `/api/clients/{name}/engagements/{id}/risks` | Create a risk |
| GET | `/api/clients/{name}/risks` | List all risks across all engagements |

### Status Updates

| Method | Path | Description |
| --- | --- | --- |
| GET | `/api/clients/{name}/engagements/{id}/status-updates` | List status updates |
| POST | `/api/clients/{name}/engagements/{id}/status-updates` | Create a status update |

### Interactions

| Method | Path | Description |
| --- | --- | --- |
| GET | `/api/clients/{name}/interactions` | List all client interactions |
| POST | `/api/clients/{name}/interactions` | Log a new interaction |

### Timeline

| Method | Path | Description |
| --- | --- | --- |
| GET | `/api/clients/{name}/timeline?limit=50` | Unified timeline: interactions + status updates + analyses |

### Action Items

| Method | Path | Description |
| --- | --- | --- |
| GET | `/api/clients/{name}/action_items` | List action items (filterable by status, engagement_id) |
| POST | `/api/clients/{name}/action_items` | Create action item |
| PUT | `/api/clients/{name}/action_items/{id}` | Update action item status |

### Client Health

| Method | Path | Description |
| --- | --- | --- |
| GET | `/api/client_health/{name}` | Health score, risk level, overdue action items, engagement status |

### Briefing

| Method | Path | Description |
| --- | --- | --- |
| GET | `/api/briefing/{name}` | Executive briefing: recent analyses, overdue items, risk changes |

### Notifications

| Method | Path | Description |
| --- | --- | --- |
| GET | `/api/notifications` | List recent notifications |
| WebSocket | `/ws/notifications` | Real-time push from EventBus (alerts, comm updates) |

### MCP Server Management (External Servers)

| Method | Path | Description |
| --- | --- | --- |
| GET | `/api/mcp/servers` | List all configured external MCP servers |
| POST | `/api/mcp/servers` | Register and connect a new external MCP server |
| GET | `/api/mcp/servers/{id}` | Get server details and status |
| PUT | `/api/mcp/servers/{id}` | Update server configuration |
| DELETE | `/api/mcp/servers/{id}` | Remove and disconnect a server |
| POST | `/api/mcp/servers/{id}/test` | Test server connectivity |
| POST | `/api/mcp/invoke` | Invoke a built-in MCP tool directly. Body: `{tool_name, arguments}` |

### Built-in MCP Server (for External Clients)

| Method | Path | Auth | Description |
| --- | --- | --- | --- |
| GET | `/mcp/sse` | Required | SSE stream — persistent MCP session (Claude Desktop, Cursor, etc.) |
| POST | `/mcp/message` | Required | JSON-RPC message endpoint for active SSE sessions |
| GET | `/mcp/tools` | None | Tool manifest — returns `{tools[], count}` with categories |
| GET | `/mcp/health` | None | Liveness probe — returns `{status, transport, tools}` |

### Communications

| Method | Path | Description |
| --- | --- | --- |
| GET | `/api/communication/{name}/accounts` | List Outlook accounts (win32com) |
| GET | `/api/communication/{name}/accounts/{account}/folders` | List folders in account |
| GET | `/api/communication/{name}/config` | Get per-client communication scan config |
| PUT | `/api/communication/{name}/config` | Update config (domains, contacts, keywords, auto_draft) |
| POST | `/api/communication/{name}/scan` | Trigger manual communication scan |
| GET | `/api/communication/{name}/emails` | List emails (params: days, search, folder) |
| GET | `/api/communication/{name}/emails/{id}` | Get email with full body |
| GET | `/api/communication/{name}/meetings` | List meetings (params: days, upcoming_only) |
| GET | `/api/communication/{name}/meetings/{id}` | Get meeting details |
| POST | `/api/communication/{name}/meetings/{id}/fetch-transcript` | Trigger Teams transcript fetch |
| POST | `/api/communication/{name}/meetings/{id}/respond` | RSVP accept/decline/tentative via win32com |
| GET | `/api/communication/{name}/drafts` | List AI-generated draft replies |
| GET | `/api/communication/{name}/drafts/{id}` | Get draft body |
| PUT | `/api/communication/{name}/drafts/{id}` | Edit draft (subject, body, to, cc) |
| POST | `/api/communication/{name}/drafts/{id}/approve` | Push draft to Outlook Drafts folder |
| POST | `/api/communication/{name}/drafts/{id}/feedback` | Save feedback, update agent memory |
| POST | `/api/communication/{name}/drafts` | Manually generate draft for an email_id |
| DELETE | `/api/communication/{name}/drafts/{id}` | Discard draft |
| GET | `/api/communication/{name}/teams` | List joined Teams (Graph API) |
| GET | `/api/communication/{name}/teams/{team_id}/channels` | List channels in a team |
| GET | `/api/communication/{name}/teams/{team_id}/channels/{ch_id}/messages` | Get channel messages |
| GET | `/api/communication/{name}/threads` | Emails grouped into threads (params: days, search) |
| GET | `/api/communication/{name}/threads/{thread_key}` | All emails in thread (chronological) |
| WebSocket | `/ws/communication/{name}/threads/{key}/insight` | Stream AI insight for an email thread |

### Tools Management

| Method | Path | Description |
| --- | --- | --- |
| GET | `/api/tools` | List all tools (built-in SK plugins + MCP + custom) |
| GET | `/api/tools/{plugin}/{function}` | Get tool details and parameter schema |
| POST | `/api/tools/invoke` | Invoke a tool. Body: `{plugin, function, arguments}` |
| POST | `/api/tools/custom` | Create a custom prompt-based tool |
| PUT | `/api/tools/custom/{id}` | Update a custom tool |
| DELETE | `/api/tools/custom/{id}` | Delete a custom tool |

## WebSocket Chat Protocol

### Client to Server

```json
{
  "type": "message",
  "content": "What are the key risks for Contoso?",
  "client_name": "Contoso"
}
```

### Server to Client — All Event Types

| Event type | Fields | When emitted |
| --- | --- | --- |
| `token` | `content: str` | Each streaming text chunk from LLM |
| `source` | `source: {file_path, section_title, page_number, excerpt, score}` | Search plugin citation |
| `thought` | `content: str` | Between ReAct iterations ("Processing 2 tool(s)...") |
| `plan` | `plan_steps: str[]` | Plan-and-execute generated plan |
| `plan_step` | `content: str, step_number: int, step_total: int` | Each step of plan execution |
| `tool_call` | `tool_name: str, tool_args: dict, tool_source: "mcp" \| null` | Before each tool invocation |
| `tool_result` | `tool_name: str, content: str (max 500 chars), tool_source: "mcp" \| null` | After tool returns |
| `error` | `message: str` | Exception in agent loop |
| `done` | (no fields) | Stream complete |

`tool_source: "mcp"` is set when the invoked plugin name starts with `"MCP_"` (an
external MCP server dynamically registered via MCPManager). Built-in SK plugins yield
`tool_source: null`.

### Example Stream

```json
{"type": "tool_call", "tool_name": "Search.search_documents", "tool_args": {"query": "Contoso risks"}, "tool_source": null}
{"type": "source", "source": {"file_path": "Contoso/risk_register.xlsx", "section_title": "Sheet1", "page_number": null, "excerpt": "Risk: integration delay...", "score": 0.94}}
{"type": "tool_result", "tool_name": "Search.search_documents", "content": "[{\"file_path\": \"...\"}]", "tool_source": null}
{"type": "thought", "content": "Processing results from 1 tool(s)..."}
{"type": "token", "content": "Based on the risk register, "}
{"type": "token", "content": "the top three risks for Contoso are..."}
{"type": "done"}
```

## Database Architecture

### Master Database (`clientagent`)

Provisioned by Terraform.

| Container | Partition Key | Purpose |
| --- | --- | --- |
| `clients` | `/id` | Client registry and metadata |
| `mcp_servers` | `/id` | External MCP server configurations |
| `custom_tools` | `/id` | Custom prompt-based tool definitions |
| `ingest_jobs` | `/id` | Ingestion job status tracking |

### Per-Client Databases (`client_{id}`)

Created dynamically when a client is onboarded.

| Container | Partition Key | Purpose |
| --- | --- | --- |
| `memories` | `/id` | Client memory (stakeholders, engagements, pain points, priorities, communication notes) |
| `doc_index` | `/file_path` | Document tracking with content hashes for incremental sync |
| `analyses` | `/file_path` | LLM analysis results per document |
| `engagements` | `/id` | Engagement/project lifecycle tracking |
| `deliverables` | `/engagement_id` | Deliverable tracking per engagement |
| `risks` | `/engagement_id` | Risk register per engagement |
| `status_updates` | `/engagement_id` | Status update timeline per engagement |
| `interactions` | `/id` | Meeting, call, email, and workshop logs |
| `action_items` | `/id` | Action item tracking across engagements |
| `events` | `/id` | Event sourcing for unified timeline |
| `emails` | `/id` | Scanned emails with classification metadata |
| `meetings` | `/id` | Calendar items with Teams transcript summaries |
| `draft_replies` | `/id` | AI-generated email draft replies |
| `communication_config` | `/id` | Per-client scan rules (domains, contacts, keywords) |

## Built-in MCP Server

The platform exposes its own MCP server at `/mcp/sse`. External MCP clients (Claude
Desktop, Cursor, VS Code extensions) can connect to access all client intelligence.

### 14 Built-in Tools

| Category | Tool | Description |
| --- | --- | --- |
| Search & Documents | `search_client_documents` | Hybrid vector + BM25 search, returns ranked chunks with source metadata |
| Search & Documents | `ingest_documents` | Trigger re-ingestion from OneDrive sync folder (incremental or complete) |
| Search & Documents | `list_indexed_files` | List doc_index metadata for a client (paginated) |
| Search & Documents | `get_ingest_status` | Poll ingestion job status by job_id |
| Client Intelligence | `read_client_memory` | Fetch structured memory with optional field filtering |
| Client Intelligence | `write_client_memory` | Append or overwrite a memory field |
| Client Intelligence | `generate_insights` | Memory + analyses + risks + action_items summary |
| Client Intelligence | `get_client_health` | Health score, risk level, engagement status |
| Client Intelligence | `get_clients` | List all clients in the system |
| Engagements | `get_engagements` | List engagements, optionally with risks/deliverables |
| Engagements | `get_action_items` | List action items, filterable by status/engagement |
| Engagements | `get_client_timeline` | Unified chronological event stream |
| Communications | `get_client_communications` | Emails, meetings, and drafts from the communication store |
| Reporting | `generate_briefing` | Executive briefing: analyses + overdue items + risk changes |

### Connecting Claude Desktop

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "client-intelligence": {
      "command": "none",
      "url": "http://localhost:8000/mcp/sse",
      "headers": {
        "Authorization": "Bearer YOUR_MCP_API_KEY"
      }
    }
  }
}
```

Set `MCP_API_KEY` in your `.env` to the same value.

### Direct Tool Invocation (no SSE)

```bash
curl -X POST http://localhost:8000/api/mcp/invoke \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "get_clients", "arguments": {}}'
```

## External MCP Servers

Add external MCP-compliant servers at runtime. Their tools become immediately available
to the agent without restart.

### Adding an External MCP Server

**Via UI**: click the MCP label in the status bar -> Add Server -> fill name, endpoint, auth.

**Via API**:

```bash
curl -X POST http://localhost:8000/api/mcp/servers \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Server",
    "endpoint": "https://my-mcp.example.com/sse",
    "protocol": "sse",
    "auth_type": "bearer",
    "auth_config": {"token": "secret"}
  }'
```

### Auth Types

| Type | Config |
| --- | --- |
| `none` | No authentication |
| `api_key` | `{"header_name": "X-API-Key", "api_key": "..."}` |
| `bearer` | `{"token": "..."}` |

### Protocols

| Protocol | Discovery | Invocation |
| --- | --- | --- |
| `sse` | Full MCP `initialize` + `list_tools` | `session.call_tool()` via live SSE session |
| `rest` | `GET /tools` | `POST /tools/{name}/invoke` |

## Communication Scanning

The `CommunicationScanner` background task polls every `COMM_SCAN_INTERVAL` seconds
(default 900). It reads emails and calendar items from Outlook (win32com) or Microsoft
Graph API (fallback), classifies them per client, stores them in Cosmos, generates AI
draft replies, and fetches Teams meeting transcripts.

### Per-Client Configuration

Configure which communications belong to a client via `PUT /api/communication/{name}/config`:

```json
{
  "accounts": [{"display_name": "user@company.com", "folders": ["Inbox"]}],
  "domains": ["contoso.com"],
  "contacts": ["jane.doe@contoso.com"],
  "keywords": ["Contoso", "Project Phoenix"],
  "scan_sent": true,
  "auto_draft": true,
  "scan_interval_minutes": 15
}
```

Classification priority:

1. Domain match — sender/recipient email contains `@contoso.com`
2. Contact match — exact match against `contacts` list
3. Keyword match — `keywords` found in subject or body

### Auto Draft Replies

When `auto_draft: true`, the scanner generates an AI draft reply (via gpt-4o) for every
inbound email from a client contact. Drafts sit in `pending_review` status. Approve via
`POST /api/communication/{name}/drafts/{id}/approve` to push to Outlook Drafts folder.

### Teams Transcript Summarization

For Teams meetings that have ended, the scanner fetches the transcript via Graph API,
summarizes it with gpt-4o (<300 words), and extracts action items as a JSON array. These
are stored on the meeting record and surfaced in CommunicationView.

## Agent Capabilities

The Semantic Kernel agent has these built-in tools available in the ReAct loop:

| Tool | Plugin | Description |
| --- | --- | --- |
| `search_documents` | Search | Hybrid vector + BM25 search across indexed client documents |
| `recall_client_memory` | Memory | Retrieve full client memory |
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
| `get_emails` | Communication | Retrieve emails from the scanned communication store |
| `get_meetings` | Communication | Retrieve meeting history and transcripts |
| `get_draft_replies` | Communication | List AI-generated draft replies for review |
| `web_search` | WebSearch | External web search via Tavily API |
| Dynamic MCP tools | MCP_{name} | One function per tool from each connected external MCP server |
| Custom tools | CustomTools | User-created prompt-based tools |

## Document Analysis Pipeline

When a file is uploaded or ingested, a two-stage pipeline runs concurrently.

### Stage 1: Ingestion

1. Parse document (supports .docx, .pptx, .xlsx, .pdf, .msg, .eml, .txt, .md)
2. Chunk at section boundaries (800 tokens max, 100-token overlap, tiktoken)
3. Embed with text-embedding-3-large (3072 dimensions, batches of 16)
4. Upsert to Azure AI Search (hybrid index: BM25 + vector HNSW)
5. Track in per-client `doc_index` container for incremental sync

### Stage 2: LLM Analysis

1. Truncate document text to ~8000 tokens
2. gpt-4o structured extraction: stakeholders, action items, risks, dates, classification
3. Store in per-client `analyses` container
4. Auto-merge into client memory (stakeholders deduped by name, action items by description)

### Supported Document Types

| Extension | Parser | Notes |
| --- | --- | --- |
| `.docx` | python-docx | Preserves heading hierarchy |
| `.pptx` | python-pptx | One chunk per slide |
| `.xlsx` | openpyxl | One chunk per sheet, column headers as prefix |
| `.pdf` | pdfplumber (fallback: pymupdf) | Per-page extraction |
| `.msg` | extract-msg | Subject + body + sender |
| `.eml` | email stdlib | Subject + body + sender |
| `.txt` / `.md` | stdlib | Raw text |

## Custom Tools

Create prompt-based tools from the UI that become available to the agent immediately.

### Creating a Custom Tool

1. Open the "Tools" tab in the sidebar -> "Agent Tools" sub-tab
2. Click "Create Custom Tool"
3. Enter: name, description, prompt template (use `{{$input}}` for variable substitution)
4. The tool is registered as a Semantic Kernel `KernelFunctionFromPrompt` and persisted to Cosmos

### Example

```text
Name: summarize_for_executive
Description: Summarize client information for an executive audience
Prompt Template: Summarize the following client information for a C-suite executive
briefing. Focus on strategic impact, financial implications, and recommended next steps.
Keep it under 200 words.

Client info: {{$input}}
```

## Extension Points

| Extension | How |
| --- | --- |
| Add SK plugin | Implement class with `@kernel_function` methods, add to `plugins` dict in `dependencies.py` |
| Add built-in MCP tool | Add `Tool` to `TOOL_DEFINITIONS`, entry to `TOOL_CATEGORIES`, handler to `_build_dispatch()` in `server.py` |
| Connect external MCP server | UI MCP panel or `POST /api/mcp/servers` — auto-wired to kernel immediately |
| Create custom tool | UI Tools tab or `POST /api/tools/custom` — prompt template stored in Cosmos |
| Add document parser | Implement branch in `ingestion/parser.py` `parse_document()` returning `ParsedDocument` |
| LOCAL_MODE stub | Implement service protocol interface, return from factory in `dependencies.py` |

## Environment Variables

| Variable | Default | Required | Description |
| --- | --- | --- | --- |
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
| `LOCAL_MODE` | `false` | No | Skip auth, use in-memory stubs |
| `BYPASS_AUTH` | `false` | No | Skip JWT validation without switching to local stubs |
| `MCP_API_KEY` | | No | Static bearer token accepted on all MCP routes |
| `RERANK_ENABLED` | `true` | No | Enable semantic reranking in AI Search |
| `SEMANTIC_CHUNKING` | `true` | No | Use semantic chunking strategy |
| `INGEST_CONCURRENCY` | `5` | No | Parallel ingestion workers |
| `TAVILY_API_KEY` | | No | API key for WebSearch plugin (Tavily) |
| `ALERT_CHECK_INTERVAL` | `900` | No | AlertChecker poll interval (seconds) |
| `ALERT_RISK_THRESHOLD` | `15` | No | Risk severity score threshold for alerts |
| `ALERT_STALE_DAYS` | `14` | No | Days without interaction before stale alert |
| `COMM_SCAN_INTERVAL` | `900` | No | CommunicationScanner poll interval (seconds) |
| `COMM_DRAFT_LOOKBACK_DAYS` | `7` | No | Email scan lookback window |
| `COMM_MEETING_LOOKBACK_DAYS` | `30` | No | Calendar scan lookback window |
| `GRAPH_CLIENT_ID` | | No | Microsoft Graph app registration client ID |
| `GRAPH_TENANT_ID` | | No | Microsoft Graph tenant ID |
| `GRAPH_USER_EMAIL` | | No | Mailbox UPN to read (delegated flow) |
| `GRAPH_CLIENT_SECRET` | | No | Graph API client secret (Key Vault in production) |
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
| --- | --- |
| `acr` | Azure Container Registry (Basic SKU) |
| `cosmos` | Cosmos DB serverless account + master database + `clients` container |
| `search` | Azure AI Search (Standard SKU, semantic reranking enabled) |
| `app_insights` | Log Analytics workspace + Application Insights |
| `container_apps` | Container Apps environment + backend (1-3 replicas, 1 CPU/2Gi) + frontend (1-2 replicas, 0.25 CPU/0.5Gi) |

Per-client databases are created dynamically by the application on client onboard.

### Outputs

| Output | Description |
| --- | --- |
| `acr_login_server` | ACR login URL |
| `cosmos_endpoint` | Cosmos DB endpoint |
| `search_endpoint` | Azure AI Search endpoint |
| `frontend_fqdn` | Public frontend URL |
| `backend_fqdn` | Internal backend URL |
| `app_insights_connection_string` | App Insights connection string |

## CI/CD

### CI Pipeline (`.github/workflows/ci.yml`)

Runs on every PR to `main`:

1. Lint backend — ruff + mypy
2. Test backend — pytest with mock env vars
3. Lint frontend — eslint + tsc --noEmit
4. Build images — Docker build smoke test
5. Terraform validate

### CD Pipeline (`.github/workflows/cd.yml`)

Runs on push to `main`:

1. Azure OIDC login (passwordless federated credentials)
2. Build and push Docker images tagged with git SHA to ACR
3. Terraform apply (requires manual approval via GitHub Environments)
4. Smoke test — curl health endpoints on deployed services

### Required GitHub Secrets

| Secret | Description |
| --- | --- |
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
| `NAME_SUFFIX` | Resource name suffix (e.g., `prod01`) |
| `BACKEND_FQDN` | Deployed backend FQDN (for smoke test) |
| `FRONTEND_FQDN` | Deployed frontend FQDN (for smoke test) |

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

## Design Tokens

```css
--color-bg-primary:    #0d0d0d    /* App root background */
--color-bg-secondary:  #161616    /* Header, footer, sidebar */
--color-bg-panel:      #1a1a1a    /* Cards, inputs */
--color-accent:        #86BC25    /* Deloitte Green — primary CTA, active states */
--color-accent-bright: #86EB22    /* Progress indicators, pulses */
--color-accent-blue:   #00A3E0    /* MCP badges, source chips, links */
--color-status-green:  #22c55e    /* Connected, active */
--color-status-red:    #ef4444    /* Error, high risk */
--color-status-amber:  #f59e0b    /* Warning, medium risk */
--font-ui:   'DM Sans', system-ui, sans-serif
--font-mono: 'JetBrains Mono', 'Fira Code', monospace
```

## Key Design Decisions

| Decision | Choice | Rationale |
| --- | --- | --- |
| Per-client databases | Isolated Cosmos DBs per client | Data isolation, independent scaling, compliance |
| Auto-analysis | LLM extracts entities on upload, auto-merges into memory | Removes manual data entry, builds intelligence passively |
| Dynamic MCP | Hot-reload MCP servers at runtime via MCPManager | No restart needed to add integrations |
| ReAct vs Plan-Execute | Route by query complexity (length + keyword heuristics) | Simple queries stay fast; complex multi-step queries get structured plans |
| Custom tools | Prompt templates, not Python code | Security (no arbitrary code execution) + SK native support |
| 3072-dim embeddings | Full fidelity from text-embedding-3-large | Best retrieval quality for long consulting documents |
| Communication scanning | Background poll + per-client attribution config | Passive intelligence gathering without user action |
| Teams transcripts | Fetched post-meeting via Graph API, summarized by LLM | Automatic meeting intelligence without manual note-taking |
| LOCAL_MODE | Interface substitution at service layer | Same code paths tested locally, no conditional branches in business logic |
| URL-based routing | React Router with `/clients/:name/*` | Bookmarkable views, browser back/forward navigation |
| Chat history | In-memory per WebSocket connection | No server-side persistence needed; ConversationManager handles token limits |
