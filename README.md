# Client Intelligence Agent

An AI-powered consulting intelligence platform that turns your existing SharePoint/OneDrive documents and Outlook communications into a living, searchable client knowledgebase — running entirely within your own Azure environment, with no data leaving your control.

---

## What It Does

Client work generates enormous volumes of intelligence: proposals, meeting notes, risk registers, financial models, email threads, Teams transcripts. Most of it is locked in files and inboxes. Client Intelligence Agent fixes this by continuously reading the places where client context already lives — your OneDrive sync folder and your Outlook mailbox — and building a structured, queryable knowledgebase automatically.

**Document intelligence** — Drop any file (Word, PowerPoint, Excel, PDF, .msg) into a client folder and it is automatically parsed, chunked, embedded, and analyzed by GPT-4o. Stakeholders, action items, risks, and engagement references are extracted and merged into the client's memory without any manual action.

**Communication intelligence** — The scanner reads your Outlook inbox and calendar using the local win32com interface. No new permissions or admin consent required. Emails and meetings are attributed to clients by domain, contact, or keyword match, and stored in Cosmos DB. GPT-4o generates draft replies for review, and Teams meeting transcripts are summarised automatically.

**Chat agent** — Ask plain-English questions against your own data ("What are the open risks for Navy Federal?", "Summarise communications from Contoso this week") and get grounded, cited answers drawn from your documents and emails. The agent can also generate PowerPoint presentations and Word documents from its findings.

**Everything in your environment** — All processing runs on Azure services in your own tenant. Your Azure OpenAI, your Cosmos DB, your AI Search index. No third-party SaaS receives client materials.

---

## Quick Start

```bash
git clone <repo-url> && cd Client-Agent
cp .env.example .env
# Set LOCAL_MODE=true in .env — no Azure credentials needed
docker compose up
```

Open `http://localhost:5173`. Auth is bypassed in LOCAL_MODE.

For full setup instructions, environment variables, and Azure configuration see [docs/local-development.md](docs/local-development.md).

---

## Tech Stack

| Layer | Technology |
| --- | --- |
| Frontend | React 18, Vite 5, TypeScript, Tailwind CSS 3, Zustand, MSAL |
| Backend | Python 3.11, FastAPI, Semantic Kernel v1.x, Pydantic v2 |
| LLM | Azure OpenAI gpt-4o + text-embedding-3-large (3072 dims) |
| Search | Azure AI Search — BM25 + vector HNSW + semantic reranking |
| Database | Azure Cosmos DB NoSQL — isolated per-client databases |
| Communication | Outlook win32com (primary) + Microsoft Graph API (Teams/fallback) |
| Infrastructure | Azure Container Apps, Azure Container Registry, Terraform |
| CI/CD | GitHub Actions with OIDC federated credentials |

---

## Documentation

| Doc | Contents |
| --- | --- |
| [Architecture](docs/architecture.md) | System overview, startup sequence, agent loop, MCP server, frontend, extension points |
| [Data Flow & Knowledge Pipeline](docs/knowledge-pipeline.md) | Document ingestion, embedding, analysis, Cosmos DB schema, RAG retrieval |
| [Communications](docs/communications.md) | Email scanning, attribution logic, draft replies, Teams transcripts, live progress |
| [Infrastructure](docs/infrastructure.md) | Terraform modules, Azure resources, CI/CD pipelines, Docker images, scaling |
| [Security](docs/security.md) | Auth modes, Entra ID JWT, data isolation, secrets management, permission model |
| [API Reference](docs/api-reference.md) | All REST and WebSocket endpoints |
| [Local Development](docs/local-development.md) | Quick start, environment variables, testing, extension points |
