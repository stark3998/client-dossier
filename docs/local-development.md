# Local Development

---

## Prerequisites

| Requirement | Version |
| --- | --- |
| Python | 3.11+ |
| Node.js | 20+ |
| Docker + Docker Compose | Any recent version |
| Microsoft Outlook | Desktop app, for communication scanning |

Azure credentials are not required for local development. Set `LOCAL_MODE=true` and all Azure services are replaced with in-memory stubs.

---

## Quick Start

### 1. Clone and configure

```bash
git clone <repo-url>
cd Client-Agent
cp .env.example .env
```

Minimum `.env` for local development:

```env
LOCAL_MODE=true
DISABLE_TELEMETRY=true
ONEDRIVE_SYNC_PATH=./data
LOG_LEVEL=DEBUG
```

### 2. Seed sample data

```bash
python scripts/seed_test_data.py
```

Creates a `Contoso` client folder under `./data/` with sample documents.

### 3. Start services

**Option A — Docker Compose (recommended)**

```bash
docker compose up
```

- Backend: `http://localhost:8000` — hot reload via volume mount
- Frontend: `http://localhost:5173` — Vite dev server
- API docs: `http://localhost:8000/docs`

**Option B — Run directly**

```bash
# Terminal 1
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Terminal 2
cd frontend
npm install
npm run dev
```

### 4. Open the app

Navigate to `http://localhost:5173`. In `LOCAL_MODE`, authentication is bypassed automatically — no login is required.

---

## Environment Variables

### Required for Azure (non-local)

| Variable | Description |
| --- | --- |
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI endpoint URL |
| `AZURE_OPENAI_API_KEY` | Azure OpenAI API key |
| `AZURE_OPENAI_DEPLOYMENT` | Chat model deployment name (default: `gpt-4o`) |
| `AZURE_OPENAI_EMBEDDING_DEPLOYMENT` | Embedding model (default: `text-embedding-3-large`) |
| `AZURE_SEARCH_ENDPOINT` | Azure AI Search endpoint |
| `AZURE_SEARCH_API_KEY` | Azure AI Search admin key |
| `AZURE_SEARCH_INDEX_NAME` | Index name (default: `client-knowledge`) |
| `COSMOS_ENDPOINT` | Cosmos DB endpoint |
| `COSMOS_KEY` | Cosmos DB key |
| `ENTRA_CLIENT_ID` | App registration client ID |
| `ENTRA_TENANT_ID` | Azure AD tenant ID |

### Optional

| Variable | Default | Description |
| --- | --- | --- |
| `COSMOS_DB_NAME` | `clientagent` | Master database name |
| `AZURE_OPENAI_API_VERSION` | `2024-08-01-preview` | API version |
| `APPLICATIONINSIGHTS_CONNECTION_STRING` | — | App Insights connection string |
| `DISABLE_TELEMETRY` | `false` | Disable OpenTelemetry |
| `ONEDRIVE_SYNC_PATH` | `/mnt/onedrive` | Base path watched for client documents |
| `LOCAL_MODE` | `false` | Skip auth, use in-memory stubs |
| `BYPASS_AUTH` | `false` | Skip JWT validation, use real Azure services |
| `MCP_API_KEY` | — | Static bearer token for MCP routes |
| `RERANK_ENABLED` | `true` | Enable semantic reranking in AI Search |
| `SEMANTIC_CHUNKING` | `true` | Semantic chunking strategy for ingestion |
| `INGEST_CONCURRENCY` | `5` | Parallel ingestion workers |
| `TAVILY_API_KEY` | — | Web search via Tavily |
| `ALERT_CHECK_INTERVAL` | `900` | AlertChecker poll interval (seconds) |
| `ALERT_RISK_THRESHOLD` | `15` | Risk severity score that triggers an alert |
| `ALERT_STALE_DAYS` | `14` | Days without interaction before stale alert |
| `COMM_SCAN_INTERVAL` | `900` | Communication scanner poll interval (seconds) |
| `COMM_DRAFT_LOOKBACK_DAYS` | `7` | Email scan lookback window |
| `COMM_MEETING_LOOKBACK_DAYS` | `30` | Calendar scan lookback window |
| `GRAPH_CLIENT_ID` | — | Graph API app registration client ID |
| `GRAPH_TENANT_ID` | — | Graph API tenant ID |
| `GRAPH_USER_EMAIL` | — | Mailbox UPN to read (delegated flow) |
| `GRAPH_CLIENT_SECRET` | — | Graph API client secret |
| `FRONTEND_URL` | `http://localhost:5173` | Allowed CORS origin |
| `BACKEND_PORT` | `8000` | Backend listen port |
| `LOG_LEVEL` | `INFO` | Python logging level |

---

## One-Time Azure Setup

### Create the search index

```bash
cd backend
python scripts/create_search_index.py
```

This creates the hybrid index in Azure AI Search with the correct vector field, BM25 fields, and semantic ranker configuration. Only needs to run once per Azure environment.

---

## Running Tests

```bash
# Backend
cd backend
LOCAL_MODE=true DISABLE_TELEMETRY=true pytest tests -v

# Frontend type check
cd frontend
npm run typecheck

# Frontend lint
npm run lint
```

---

## Logging

In local development, debug logs are visible in the terminal. The backend uses Python's standard `logging` module configured with `force=True` to override uvicorn's pre-installed handlers:

```python
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL, logging.INFO),
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
    force=True,
)
```

Set `LOG_LEVEL=DEBUG` to see full scanner output including per-folder fetch counts and attribution results.

---

## Extension Points

| Task | Where |
| --- | --- |
| Add a Semantic Kernel plugin | Implement a class with `@kernel_function` methods, register in `dependencies.py` `plugins` dict |
| Add a built-in MCP tool | Add `Tool` to `TOOL_DEFINITIONS`, entry to `TOOL_CATEGORIES`, handler in `_build_dispatch()` in `mcp_server/server.py` |
| Connect an external MCP server | Use the MCP panel in the UI, or `POST /api/mcp/servers` |
| Create a custom prompt tool | Use the Tools tab in the UI, or `POST /api/tools/custom` |
| Add a document format | Implement a branch in `ingestion/parser.py` `parse_document()` returning `ParsedDocument` |
| Add a LOCAL_MODE stub | Implement the service protocol interface and return it from the factory in `dependencies.py` |
