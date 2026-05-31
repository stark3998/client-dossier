# Knowledge Pipeline: How the Client Intelligence Agent Learns and Remembers

This document traces the complete lifecycle of information in the system — from a raw document on disk to a cited answer in the chat — covering ingestion, vectorisation, LLM analysis, memory consolidation, and how the agent uses all of it at query time.

---

## Overview

The system has three distinct but connected pipelines:

```
┌─────────────────────────────────────────────────────────────────┐
│  1. EXTRACTION         2. MEMORY                 3. RETRIEVAL   │
│                                                                  │
│  Document             Structured facts           Agent answers  │
│  on disk    ───────►  in Cosmos DB    ────────►  with citations │
│             vectorise  + search index  inject                   │
└─────────────────────────────────────────────────────────────────┘
```

Each pipeline feeds the next. A document contributes both a vector index entry (for semantic search) and a structured memory update (for fast, summarised context). At query time the agent draws on both.

---

## Part 1: Extraction — Document to Vector Index

### Trigger

Ingestion is kicked off in three ways:

| Method | How |
|---|---|
| **Sync button** | `POST /api/ingest` with `{client_name}` — scans entire client directory |
| **File upload** | `POST /api/files/upload` — ingests the single uploaded file immediately |
| **File watcher** | Background process watching `ONEDRIVE_SYNC_PATH`; triggers on create/modify with a 2-second debounce |

All three paths funnel into the same `run_ingestion()` function in `backend/app/ingestion/pipeline.py`.

### Step 1 — Parse

`parse_document(file_path)` in `backend/app/ingestion/parser.py` converts the raw file into a `ParsedDocument`:

```
ParsedDocument
  ├── file_path
  ├── file_type          (.docx, .pdf, .pptx, .xlsx, .msg, .eml, .txt, .md)
  ├── last_modified
  ├── metadata           {size_bytes, ...}
  └── sections[]
        ├── title        (heading, slide title, sheet name, page number)
        └── text         (extracted body content)
```

Each file type has its own parser — Word extracts by heading level, PowerPoint one section per slide, Excel one section per worksheet, PDF one section per page, email uses From/Subject as the title.

### Step 2 — Deduplication check

Before doing any expensive work, the pipeline computes a **SHA-256 hash of the file content** and checks the `doc_index` container in Cosmos DB. If a record exists with a matching hash, the file is skipped entirely. This means re-running ingestion on an already-indexed client is fast — only new or changed files are processed.

### Step 3 — Chunk

`chunk_document()` in `backend/app/ingestion/chunker.py` splits each section into overlapping windows:

- **Max size**: 800 tokens (using tiktoken `cl100k_base`)
- **Overlap**: 100 tokens between consecutive chunks
- Each chunk carries the section title, page number, file path, and client name as metadata
- Each chunk gets a **SHA-256 ID** derived from `file_path + content`

The overlap ensures that information spanning a chunk boundary remains retrievable.

### Step 4 — Embed

`embed_chunks()` calls `EmbeddingService.embed_texts()` in batches of 16 against the Azure OpenAI `text-embedding-3-large` deployment. This produces **3072-dimensional float vectors** per chunk.

In `LOCAL_MODE`, a `LocalEmbeddingService` produces deterministic vectors seeded from the content hash so the system functions without Azure credits.

### Step 5 — Index

The enriched chunks (content + metadata + embedding) are bulk-upserted to **Azure AI Search** via `SearchService.upsert_chunks()`. The index schema:

| Field | Type | Purpose |
|---|---|---|
| `id` | Key | SHA-256 chunk hash |
| `content` | Searchable string | Chunk text for BM25 |
| `content_vector` | 3072-dim float | HNSW vector for semantic search |
| `file_path` | Filterable | Per-file scoping |
| `client_name` | Filterable | **Per-client isolation** |
| `section_title` | Searchable | Boosts relevance for titled sections |
| `page_number` | Int | For citation display |
| `last_modified` | DateTimeOffset | Sortable recency |

### Step 6 — Record

A record is written to the `doc_index` Cosmos container marking the file as ingested:

```json
{
  "id": "<sha256>",
  "file_path": "Acme Corp/Uploads/Q4-Review.pdf",
  "content_hash": "<sha256>",
  "chunk_count": 14,
  "last_indexed": "2026-05-31T09:00:00Z"
}
```

---

## Part 2: Analysis — Document to Structured Facts

In parallel with vectorisation, every ingested document is also passed through an **LLM analysis step** that extracts structured facts and merges them into the client's memory.

### LLM Extraction

`AnalysisService.analyze_document()` in `backend/app/services/analysis.py`:

1. Concatenates all parsed sections (truncated to ~48K characters / ~12K tokens)
2. Sends to Azure OpenAI with the system prompt from `backend/app/prompts/analysis_prompt.txt`
3. Receives a structured JSON response:

```json
{
  "doc_type": "meeting_notes",
  "analysis_summary": "Q4 planning session covering ...",
  "extracted_stakeholders": [
    { "name": "Jane Smith", "title": "CFO", "email": "jsmith@acme.com", "confidence": 0.95 }
  ],
  "extracted_actions": [
    { "description": "Send revised SOW by Friday", "owner": "Jane", "due_date": "2026-06-06", "priority": "high" }
  ],
  "extracted_risks": [
    { "description": "Budget approval delayed", "severity": "high", "category": "commercial" }
  ],
  "extracted_dates": [
    { "date": "2026-06-15", "description": "Milestone review", "date_type": "milestone" }
  ],
  "engagement_references": ["Project Orion"],
  "key_topics": ["budget", "resourcing", "timeline"]
}
```

The prompt instructs the model to:
- Classify `doc_type` from: `meeting_notes`, `contract`, `proposal`, `status_report`, `email`, `presentation`, `spreadsheet`, `memo`, `other`
- Find stakeholders in signatures, attendee lists, and org chart references; assign a confidence score 0.5–1.0
- Identify action items from TODO/Next Steps patterns; extract owner and due date if present
- Detect risks from language like "risk", "concern", "issue", "blocker"; categorise as technical/commercial/operational/timeline
- Extract explicit dates and classify them as milestone/meeting/deadline

The full `AnalysisResult` is stored in the client's `analyses` Cosmos container (partitioned by `file_path`) so it can be reviewed later in the Analysis view of the frontend.

### Memory Merge

`merge_analysis_into_memory()` in `backend/app/services/analysis.py` takes the `AnalysisResult` and merges it into the live `ClientMemory` object in Cosmos:

| Extracted field | Merges into ClientMemory field | Dedup logic |
|---|---|---|
| `extracted_stakeholders` | `key_stakeholders` | Match by name (case-insensitive), skip if exists |
| `extracted_actions` | `open_action_items` | Match by description, skip if exists |
| `engagement_references` | `active_engagements` | Set union |
| `extracted_risks[].description` | `pain_points` | Set union |
| `file_path` | `sources` | Append |
| *(always)* | `last_updated` | Overwrite with UTC now |

The `ClientMemory` object in the `memories` Cosmos container accumulates facts from every document ever ingested for that client:

```
ClientMemory
  ├── client_name
  ├── industry
  ├── key_stakeholders[]      ← accumulated from all docs
  ├── active_engagements[]    ← accumulated from all docs
  ├── financials_summary
  ├── pain_points[]           ← risk descriptions from all docs
  ├── strategic_priorities[]
  ├── past_deliverables[]
  ├── open_action_items[]     ← accumulated from all docs
  ├── last_updated
  └── sources[]               ← every file that contributed
```

---

## Part 3: Retrieval — How the Agent Uses Knowledge

When a user sends a message, `AgentPlanner.stream_response()` in `backend/app/agent/planner.py` orchestrates the following before the model even sees the user's words.

### Pre-query: Context Injection

`ContextInjector.build_context_block(client_name)` in `backend/app/agent/context_injector.py` fetches four things in parallel from Cosmos and assembles them into a structured block (capped at 2000 tokens):

```
=== CLIENT CONTEXT: Acme Corp ===
Industry: Technology
Priorities: Digital transformation, cost reduction, ...
Pain points: Budget approval delayed, ...

RECENT INTERACTIONS (3):
- [meeting] 2026-05-28: Discussed Q4 roadmap and resourcing...

ACTIVE RISKS (2):
- [Sev:8] Budget approval delayed in commercial track
- [Sev:6] Key resource leaving in July

OVERDUE ACTION ITEMS (1):
- Send revised SOW (due: 2026-06-06, owner: Jane)
===
```

This block is injected as a system message at the top of the conversation history. The model always has the most relevant client facts without needing to call a tool first.

### Pre-query: Conversation Compaction

`ConversationManager.maybe_summarize()` in `backend/app/agent/conversation_manager.py` checks the total token count of the chat history. If it exceeds **8000 tokens**:

1. The oldest messages (everything except the last 6) are summarised by the LLM using `summarize_conversation_prompt.txt`
2. The summary preserves: decisions made, facts learned, action items raised, unresolved questions
3. The compressed history becomes: `[system: CLIENT CONTEXT] + [system: CONVERSATION_SUMMARY ...] + [last 6 messages]`

This prevents context window exhaustion on long sessions while keeping recent turns verbatim.

### Routing: Simple vs Complex

`is_complex_query()` checks for signals like "compare", "across all", "for each", "summarize all", query length > 150 characters. 

- **Simple** → `run_react_loop()` directly
- **Complex** → `plan_and_execute()` first generates a JSON step plan, then runs each step through `run_react_loop()`

### The ReAct Loop

`run_react_loop()` in `backend/app/agent/react_loop.py` runs up to 10 iterations:

```
┌──────────────────────────────────────────────────┐
│  LLM sees: system context + chat history          │
│  LLM outputs: text + optional tool call(s)        │
└────────────────────┬─────────────────────────────┘
                     │ tool call requested?
          ┌──────────┴──────────┐
         Yes                    No
          │                     │
          ▼                     ▼
   Execute tool(s)         Stream final
   Add results to          answer to user
   history                 (done)
   Loop again
```

The model decides which tools to call. The full tool set available:

**Knowledge retrieval**
- `search_documents(query, client_name)` — hybrid search (BM25 + vector) against the indexed chunks
- `search_with_rewriting(query, client_name)` — generates 2-3 query variants via `query_rewrite_prompt.txt`, runs each, deduplicates results
- `list_files(client_name)` — browse the file tree
- `read_file_preview(path)` — read up to 5000 chars of a specific file

**Memory access**
- `recall_client_memory(client_name)` — fetches the live `ClientMemory` object
- `update_client_memory(client_name, field_name, value)` — writes back to Cosmos
- `get_client_health(client_name)` — returns the computed health score

**Engagement & risk management**
- `recall_engagements`, `create_engagement`, `update_engagement_phase`
- `recall_risks`, `create_risk`
- `recall_deliverables`, `create_deliverable`
- `create_interaction`, `create_action_item`

**Document generation**
- `generate_presentation`, `generate_document`, `draft_status_report`, `generate_meeting_summary`

### Hybrid Search in Detail

When `search_documents()` is called, `SearchService.hybrid_search()` fires a single request to Azure AI Search that combines:

1. **BM25 full-text search** on `content` and `section_title` — handles exact keyword matches
2. **HNSW vector search** on `content_vector` — handles semantic similarity
3. **Semantic re-ranking** — Azure AI Search re-scores results using its semantic model, prioritising `content` then `section_title`
4. **Client filter** — `client_name eq 'Acme Corp'` scopes results to this client only

Returns the top 8 chunks with scores. The agent formats them and the ReAct loop emits a `StreamEvent(type="source")` for each unique source file — these become the citation chips displayed under the response in the UI.

### Memory Updates During Conversation

The agent's system prompt instructs it to **proactively update memory** whenever it learns something new. When the model calls `update_client_memory()`, it writes directly back to the Cosmos `memories` container, so future conversations (and future context injections) will include the updated fact. The model effectively maintains memory continuity across sessions.

---

## Cosmos DB Schema Summary

Each client gets its own Cosmos database (`client_{id}`) with these containers:

| Container | Partition Key | What's stored |
|---|---|---|
| `memories` | `/id` | Single ClientMemory object per client |
| `doc_index` | `/file_path` | Ingestion tracking (hash, chunk count, timestamp) |
| `analyses` | `/file_path` | Full AnalysisResult per document |
| `engagements` | `/id` | Engagement records with phase, status |
| `interactions` | `/id` | Meeting notes, calls, emails logged |
| `action_items` | `/engagement_id` | Open/closed action items |
| `risks` | `/engagement_id` | Risk register entries |
| `deliverables` | `/engagement_id` | Deliverable tracking |
| `status_updates` | `/engagement_id` | Status report history |
| `events` | `/event_type` | System events and timeline entries |

---

## Data Flow — Complete End-to-End

```
FILE ON DISK
    │
    ▼
parse_document()              → ParsedDocument (sections + metadata)
    │
    ├──► chunk_document()     → Chunk[] (800 tok, 100 tok overlap)
    │         │
    │         ▼
    │    embed_chunks()       → Chunk[] + 3072-dim vectors
    │         │
    │         ▼
    │    upsert_chunks()      → Azure AI Search index (BM25 + HNSW)
    │    doc_index upsert     → Cosmos (hash tracking)
    │
    └──► analyze_document()   → AnalysisResult (LLM extraction)
              │
              ▼
         merge_analysis_into_memory()
              │
              ▼
         ClientMemory in Cosmos (stakeholders, actions, risks, priorities)


CHAT MESSAGE
    │
    ▼
maybe_summarize()             → compact history if > 8000 tokens
    │
    ▼
build_context_block()         → inject memory + risks + overdue items
    │
    ▼
is_complex_query()?
    ├── Yes → plan_and_execute()  → JSON step plan → loop each step
    └── No  → run_react_loop()
                   │
                   ▼
              LLM + tools (up to 10 iterations)
                   │
                   ├── search_documents()
                   │       └── embed query → hybrid_search() → top 8 chunks + sources
                   ├── recall_client_memory()
                   │       └── fetch ClientMemory from Cosmos
                   ├── update_client_memory()
                   │       └── write new facts back to Cosmos
                   └── (other tools: engagements, risks, docs, ...)
                   │
                   ▼
              Stream to frontend: tokens + source chips + tool events
```

---

## Building Further on the Knowledge Base

The memory compounds over time in two ways:

**Passive accumulation** — every new document synced via OneDrive or uploaded through the UI runs through both the vector pipeline and the LLM analysis pipeline. Stakeholders, risks, and action items accumulate in `ClientMemory` without manual input.

**Active enrichment by the agent** — during conversations the agent is instructed to call `update_client_memory()` whenever it infers something new (e.g., the user mentions a new stakeholder or the user confirms a risk has been resolved). This means the memory is live and reflects the conversation as well as the documents.

**Cross-session continuity** — `ConversationManager` compacts old chat history into a summary that travels forward into new sessions. Combined with the persistent `ClientMemory` and the context injection at every query, the agent maintains a coherent picture of the client across weeks of conversations and hundreds of documents.
