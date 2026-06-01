# Knowledge Pipeline: Data Architecture & Flow

This document is the authoritative reference for how data moves through the system — from a file on disk to a cited answer in chat. It covers every storage layer, schema, partition strategy, and service interaction.

---

## System Overview

The platform uses **three Azure services** for persistent data and **one in-process embedding model** for vectorisation:

| Service | Role |
|---|---|
| **Azure AI Search** | Full-text + vector search index — the RAG retrieval store |
| **Azure Cosmos DB (NoSQL)** | All structured state — client memory, engagements, tracking |
| **Azure OpenAI** | Embeddings (`text-embedding-3-large`) + LLM (`gpt-4o`) |
| **FlashRank** | In-process cross-encoder re-ranking of search results |

Data flows through two parallel pipelines triggered on every sync or upload, then converges at query time:

```
Document on disk
      │
      ├──► VECTOR PIPELINE ──────────────────► Azure AI Search (chunks + embeddings)
      │                                        Cosmos doc_index (hash tracking)
      │
      └──► ANALYSIS PIPELINE ────────────────► Cosmos analyses (AnalysisResult per doc)
                                               Cosmos memories (merged ClientMemory)

Chat message
      │
      ├── Cosmos memories / risks / actions ─► Context injection (2000 tok budget)
      ├── Azure AI Search ────────────────────► Hybrid search (BM25 + HNSW + rerank)
      └── Cosmos all containers ──────────────► Tool calls (engagements, risks, etc.)
```

---

## Part 1: Azure AI Search

### Index: `client-knowledge`

Configured in `app/services/search.py`. One index shared across all clients; `client_name` is a filterable field used to scope every query.

| Field | Type | Attributes | Notes |
| --- | --- | --- | --- |
| `id` | String | Key | SHA-256(`file_path:content`) |
| `content` | String | Searchable | Full chunk text — BM25 searches this |
| `content_vector` | Collection(Single) | Searchable, 3072-dim | HNSW vector index — semantic search |
| `file_path` | String | Filterable | Full path to source file |
| `file_type` | String | Filterable | `.docx`, `.pdf`, `.pptx`, etc. |
| `section_title` | String | Searchable | Heading / slide title / sheet name |
| `page_number` | Int32 | | 0-indexed; used in citations |
| `client_name` | String | Filterable | **Per-client isolation at query time** |
| `chunk_hash` | String | | SHA-256(content) — for dedup detection |
| `last_modified` | DateTimeOffset | Sortable | From file system metadata |

### Vector Configuration

- **Algorithm**: HNSW (`HnswAlgorithmConfiguration`, name `hnsw-config`)
- **Profile**: `hnsw-profile`
- **Dimensions**: 3072 (matches `text-embedding-3-large`)
- **Semantic config**: `semantic-config` — prioritises `content` then `section_title` for re-ranking

### Hybrid Search

`SearchService.hybrid_search()` fires a single Azure AI Search request that combines:

1. **BM25 full-text** on `content` + `section_title`
2. **HNSW vector search** on `content_vector` using the embedded query
3. **Semantic re-ranking** — Azure's hosted semantic model rescores the merged list
4. **Client filter** — `client_name eq '{client}'` applied to every query
5. **FlashRank cross-encoder** — `ms-marco-MiniLM-L-12-v2` re-ranks the top results in-process (toggled by `RERANK_ENABLED`)

Returns top 8 chunks. Each result includes: `id`, `content`, `file_path`, `file_type`, `section_title`, `page_number`, `client_name`, `score`.

---

## Part 2: Cosmos DB

### Account Structure

```
Cosmos Account
├── Database: "clientagent"          ← master / shared
│     ├── Container: clients
│     ├── Container: custom_tools
│     └── Container: mcp_servers
│
├── Database: "client_{client_id}"   ← one per client
│     ├── Container: memories
│     ├── Container: doc_index
│     ├── Container: analyses
│     ├── Container: engagements
│     ├── Container: interactions
│     ├── Container: action_items
│     ├── Container: risks
│     ├── Container: deliverables
│     ├── Container: status_updates
│     └── Container: events
│
└── Database: "client_{client_id}"   ← (repeated for each client)
```

**Client ID format**: `client_name.lower().replace(" ", "-")` — e.g., `"Acme Corp"` → `client_acme-corp`.

---

### Master Database: `clientagent`

#### `clients` — partition key `/id`

One document per registered client. Queried by the frontend to populate the client selector.

| Field | Type |
|---|---|
| `id` | string |
| `name` | string |
| `description` | string |
| `created_at` | ISO timestamp |

#### `custom_tools` — partition key `/id`

User-defined tool definitions injectable into the agent's tool set.

#### `mcp_servers` — partition key `/id`

MCP server configurations (URL, enabled flag, headers) managed via the Settings panel.

---

### Per-Client Databases: `client_{client_id}`

#### `memories` — partition key `/id`

A **single document per client** — accumulated facts from every ingested document and every conversation. Fetched at the start of every chat session for context injection.

```
ClientMemory
├── id                    string   — same as client_id
├── client_name           string
├── industry              string?
├── key_stakeholders[]
│     ├── name            string
│     ├── title           string?
│     └── email           string?
├── active_engagements[]  string[]  — engagement names
├── financials_summary    string?
├── pain_points[]         string[]  — risk descriptions merged from documents
├── strategic_priorities[] string[]
├── past_deliverables[]
│     ├── title           string
│     ├── date            datetime?
│     └── file_path       string?
├── open_action_items[]
│     ├── description     string
│     ├── owner           string?
│     ├── due_date        datetime?
│     └── completed       bool
├── last_updated          datetime
└── sources[]             string[]  — every file_path that contributed
```

Dedup logic on merge: stakeholders by name (case-insensitive), action items by description (case-insensitive), pain points and engagements by exact match.

#### `doc_index` — partition key `/file_path`

One document per **indexed file**. Sole purpose: incremental sync deduplication.

```json
{
  "id": "<sha256-of-file-content>",
  "file_path": "Acme Corp/Q4-Review.pdf",
  "file_type": ".pdf",
  "content_hash": "<sha256>",
  "chunk_count": 14,
  "last_indexed": "2026-05-31T09:00:00Z"
}
```

Before any expensive work, `_ingest_file()` reads this record. If `content_hash` matches the current file hash, the file is skipped entirely (incremental mode). In complete mode (`force=True`) the check is bypassed.

#### `analyses` — partition key `/file_path`

Full `AnalysisResult` per document, stored after LLM extraction. Used by the Analysis view in the frontend.

```
AnalysisResult
├── id                       string (uuid)
├── file_path                string
├── client_name              string
├── doc_type                 string  — meeting_notes | contract | proposal | status_report
│                                      email | presentation | spreadsheet | memo | other
├── analysis_summary         string
├── extracted_stakeholders[]
│     ├── name               string
│     ├── title              string?
│     ├── email              string?
│     ├── organization       string?
│     └── confidence         float   — 0.5–1.0
├── extracted_actions[]
│     ├── description        string
│     ├── owner              string?
│     ├── due_date           string?
│     └── priority           string?
├── extracted_risks[]
│     ├── description        string
│     ├── severity           string?
│     └── category           string?  — technical | commercial | operational | timeline
├── extracted_dates[]
│     ├── date               string
│     ├── description        string
│     └── date_type          string  — milestone | meeting | deadline
├── engagement_references[]  string[]
├── key_topics[]             string[]
└── analyzed_at              datetime
```

LLM call: `gpt-4o`, `temperature=0.1`, `max_tokens=4096`, `response_format=json_object`. Input truncated to ~48,000 characters (~12K tokens).

#### `engagements` — partition key `/id`

```
Engagement
├── id               string (uuid)
├── name             string
├── client_name      string
├── phase            discovery | design | execute | deliver | sustain
├── status           active | completed | on-hold | cancelled
├── description      string
├── start_date       string?
├── end_date         string?
├── budget           float?
├── team[]           string[]
├── created_at       datetime
└── updated_at       datetime
```

#### `interactions` — partition key `/id`

Meeting notes, calls, and emails logged against a client.

```
Interaction
├── id               string (uuid)
├── type             meeting | call | email | workshop
├── date             string
├── participants[]   string[]
├── summary          string
├── action_items[]   string[]
├── source_file      string?   — file_path if auto-extracted
├── engagement_id    string?
└── created_at       datetime
```

#### `action_items` — partition key `/engagement_id`

```
ActionItem
├── id               string (uuid)
├── description      string
├── owner            string?
├── due_date         string?
├── completed        bool
└── engagement_id    string
```

#### `risks` — partition key `/engagement_id`

Risk score = `probability × impact` (both 1–5 integers). Used to compute client health score and surface overdue/high-severity items in context injection.

```
Risk
├── id               string (uuid)
├── description      string
├── probability      int    1–5
├── impact           int    1–5
├── mitigation       string
├── status           open | mitigating | resolved | accepted
├── engagement_id    string
├── owner            string
├── category         technical | commercial | operational | timeline
├── created_at       datetime
└── updated_at       datetime
```

#### `deliverables` — partition key `/engagement_id`

```
Deliverable
├── id               string (uuid)
├── title            string
├── type             document | presentation | report | code | other
├── engagement_id    string
├── status           draft | review | delivered | accepted
├── due_date         string?
├── owner            string
├── feedback         string?
├── file_path        string?
├── created_at       datetime
└── updated_at       datetime
```

#### `status_updates` — partition key `/engagement_id`

```
StatusUpdate
├── id               string (uuid)
├── engagement_id    string
├── date             string
├── author           string
├── summary          string
├── sentiment        positive | neutral | negative | concerning
├── source_file      string?
└── created_at       datetime
```

#### `events` — partition key `/event_type`

System events and timeline entries (file uploads, sync runs, agent actions).

---

## Part 3: Ingestion Pipeline

### Supported File Types

```python
SUPPORTED_EXTENSIONS = {".docx", ".pptx", ".xlsx", ".pdf", ".msg", ".eml", ".txt", ".md"}
```

| Extension | Parser | Section Boundary |
|---|---|---|
| `.docx` | python-docx | Word heading styles |
| `.pptx` | python-pptx | One section per slide |
| `.xlsx` | openpyxl | One section per worksheet |
| `.pdf` | pdfplumber / fitz | One section per page |
| `.msg` | extract-msg | From / Subject / Body |
| `.eml` | email stdlib | From / Subject / Body |
| `.txt` / `.md` | stdlib | Single section |

### Chunking

`chunk_document()` in `app/ingestion/chunker.py`:

- **Tokeniser**: `cl100k_base` (tiktoken)
- **Max chunk size**: 800 tokens
- **Overlap**: 100 tokens between consecutive chunks (ensures boundary content stays retrievable)
- **Sentence boundary splitting**: `(?<=[.!?])\s+` — never splits mid-sentence
- **Semantic chunking** (optional, `SEMANTIC_CHUNKING=True`): uses chonkie `SemanticChunker` at similarity threshold 0.5

**Chunk identity**:

```
chunk_hash = SHA-256(content)
chunk.id   = SHA-256(file_path + ":" + content)
```

### Embedding

`embed_chunks()` in `app/ingestion/embedder.py` calls `EmbeddingService.embed_texts()`:

- **Model**: `text-embedding-3-large` (Azure OpenAI deployment `AZURE_OPENAI_EMBEDDING_DEPLOYMENT`)
- **Vector dimensions**: 3072
- **Batch size**: 16 chunks per API call
- **Local mode**: `LocalEmbeddingService` — deterministic 3072-dim vectors seeded from content hash, no API calls

### Pipeline Steps (per file)

```
_ingest_file(file_path, client_name, force)
│
├─ 1. SHA-256 hash the file bytes
├─ 2. Query doc_index (Cosmos) for matching content_hash
│     └─ If match found AND force=False → return {indexed: False}  [SKIP]
│
├─ 3. parse_document() → ParsedDocument with sections[]
├─ 4. chunk_document() → Chunk[] (800 tok, 100 tok overlap)
├─ 5. embed_chunks()   → Chunk[].embedding = float[3072]
│
├─ 6. upsert_chunks() → Azure AI Search
│     └─ Bulk upsert: id, content, content_vector, file_path, file_type,
│                      section_title, page_number, client_name, chunk_hash, last_modified
│
├─ 7. doc_index upsert → Cosmos
│     └─ {id: content_hash, file_path, file_type, content_hash, chunk_count, last_indexed}
│
└─ return {indexed: True, chunks: N, duration_ms: T}
```

The analysis pipeline runs **in parallel** (separate call from `run_ingestion()`):

```
analyze_document(parsed, client_name)
│
├─ Concatenate sections → truncate to ~48K chars
├─ gpt-4o call (temp=0.1, max_tokens=4096) → AnalysisResult JSON
├─ Store AnalysisResult → Cosmos analyses container
│
└─ merge_analysis_into_memory(result, memory_repo)
      ├─ Fetch existing ClientMemory from Cosmos memories
      ├─ Merge stakeholders (dedup by name)
      ├─ Merge action_items (dedup by description)
      ├─ Union engagement_references → active_engagements
      ├─ Union risk descriptions → pain_points
      ├─ Append file_path → sources
      └─ Upsert updated ClientMemory back to Cosmos memories
```

### Job State (`IngestJob` — in-memory only)

Jobs are held in a process-level dict `_jobs` in `app/api/ingest.py` and do not persist to Cosmos. Polling via `GET /api/ingest/{job_id}` reads directly from this dict.

```
IngestJob
├── id                  string (uuid)
├── status              pending | running | done | error
├── mode                incremental | complete
├── path                string
├── client_name         string
├── total_files         int
├── processed_files     int
├── current_file_index  int   — 1-based, updated per file
├── skipped_files       int   — unchanged files (incremental mode)
├── current_file        string?
├── file_events[]             — last 20 completed files
│     ├── file_name     string
│     ├── status        done | error
│     ├── chunks        int?
│     ├── duration_ms   int?
│     └── error         string?  (error events only)
├── error               string?
├── started_at          datetime
└── completed_at        datetime?
```

---

## Part 4: Query-Time Data Flow

### 1. Context Injection

`ContextInjector.build_context_block(client_name)` fetches four things **in parallel** from Cosmos before any LLM call:

| Query | Container | Filter |
|---|---|---|
| Client memory | `memories` | `GET memories/{client_id}` |
| Recent interactions | `interactions` | Last 5, ordered by `date DESC` |
| Active risks | `risks` | `status = 'open'`, top 10 by `probability × impact` |
| Overdue actions | `action_items` | `status = 'open'` AND `due_date < today` |

Assembles a structured text block capped at **2000 tokens**, injected as a system message at the top of the conversation history. The model always has the most relevant client facts before seeing the user's message.

### 2. Conversation Compaction

`ConversationManager.maybe_summarize()` checks total token count of chat history (using `cl100k_base` or `len // 4` approximation):

- **Threshold**: 8000 tokens
- **Minimum kept verbatim**: last 6 messages
- **Summarisation**: `gpt-4o` call with `summarize_conversation_prompt.txt` (temp=0.2, max_tokens=1024)
- **Fallback**: joins last 10 messages truncated to 200 chars each
- **Result**: `[system: CLIENT CONTEXT] + [system: CONVERSATION_SUMMARY] + [last 6 messages]`

### 3. Query Routing

`is_complex_query()` checks for terms like "compare", "across all", "for each", "summarize all", or query length > 150 characters:

- **Simple** → `run_react_loop()` directly
- **Complex** → `plan_and_execute()` generates a JSON step plan, then runs each step through `run_react_loop()`

### 4. ReAct Tool Loop (up to 10 iterations)

The model receives the full context + history and emits tool calls until it has enough information to answer.

#### Knowledge retrieval tools

| Tool | Reads from | Notes |
| --- | --- | --- |
| `search_documents(query, client_name)` | Azure AI Search | Hybrid BM25 + HNSW + rerank, returns top 8 chunks |
| `search_with_rewriting(query, client_name)` | Azure AI Search | Generates 2-3 query variants, deduplicates results |
| `list_files(client_name)` | File system | Directory tree |
| `read_file_preview(path)` | File system | Up to 5000 characters |

#### Memory tools

| Tool | Reads/writes | Container |
| --- | --- | --- |
| `recall_client_memory(client_name)` | Read | `memories` |
| `update_client_memory(client_name, field, value)` | Write | `memories` |
| `get_client_health(client_name)` | Read | `memories`, `risks`, `action_items` |

#### Engagement & risk tools

| Tool | Container |
| --- | --- |
| `recall_engagements` / `create_engagement` / `update_engagement_phase` | `engagements` |
| `recall_risks` / `create_risk` | `risks` |
| `recall_deliverables` / `create_deliverable` | `deliverables` |
| `create_interaction` | `interactions` |
| `create_action_item` | `action_items` |

#### Document generation tools

`generate_presentation`, `generate_document`, `draft_status_report`, `generate_meeting_summary` — write output files to the client directory and may create `deliverables` or `interactions` records.

### 5. Search Result to Citation

When `search_documents()` returns chunks, each unique `file_path` in the results becomes a `StreamEvent(type="source")` emitted to the frontend. These appear as citation chips below the agent's response, linking back to the source document.

---

## Part 5: Environment & Configuration

All Azure service coordinates come from environment variables (sourced from Key Vault in production, `.env` in local mode):

| Variable | Purpose |
| --- | --- |
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI base URL |
| `AZURE_OPENAI_API_KEY` | Azure OpenAI key |
| `AZURE_OPENAI_DEPLOYMENT` | Chat model (`gpt-4o`) |
| `AZURE_OPENAI_EMBEDDING_DEPLOYMENT` | Embedding model (`text-embedding-3-large`) |
| `AZURE_OPENAI_API_VERSION` | API version (`2024-08-01-preview`) |
| `AZURE_SEARCH_ENDPOINT` | Azure AI Search endpoint |
| `AZURE_SEARCH_API_KEY` | Azure AI Search key |
| `AZURE_SEARCH_INDEX_NAME` | Index name (default: `client-knowledge`) |
| `COSMOS_ENDPOINT` | Cosmos DB account URL |
| `COSMOS_KEY` | Cosmos DB key |
| `COSMOS_DB_NAME` | Master database name (default: `clientagent`) |
| `ONEDRIVE_SYNC_PATH` | Root path for file discovery |
| `RERANK_ENABLED` | Enable FlashRank cross-encoder reranking |
| `SEMANTIC_CHUNKING` | Enable chonkie semantic chunker |
| `LOCAL_MODE` | Skip auth + use local stub services |
| `TAVILY_API_KEY` | Web search tool (optional) |
| `ALERT_RISK_THRESHOLD` | Risk score threshold for alerts (default: 15) |
| `ALERT_STALE_DAYS` | Days before client is flagged stale (default: 14) |

---

## Quick Reference

| Parameter | Value |
| --- | --- |
| Search index name | `client-knowledge` |
| Vector model | `text-embedding-3-large` |
| Vector dimensions | 3072 |
| Embedding batch size | 16 texts / API call |
| Chunk max size | 800 tokens |
| Chunk overlap | 100 tokens |
| Token encoder | `cl100k_base` (tiktoken) |
| Chat model | `gpt-4o` |
| Search top-k | 8 chunks |
| Context injection budget | 2000 tokens |
| Conversation compaction threshold | 8000 tokens |
| Messages kept verbatim | last 6 |
| ReAct max iterations | 10 |
| Analysis max input | ~48,000 chars (~12K tokens) |
| Master Cosmos DB | `clientagent` |
| Per-client DB prefix | `client_{id}` |
| Per-client containers | 10 |
| Job state persistence | In-memory only (process-level dict) |
| Reranker | FlashRank `ms-marco-MiniLM-L-12-v2` |
