# Client-Agent MCP Tools

This repository has a local Client-Agent MCP server running at `http://localhost:8000`.
Use the following tools when working with client documents, engagements, and intelligence.

## Available Tools

### Knowledge & Search
- **`search_client_documents`** — Hybrid vector + BM25 search across all indexed client files. Use for any question about client content. Parameters: `query` (required), `client_id`, `top_k`, `search_mode`.
- **`list_indexed_files`** — Browse the document metadata index for a client. Parameters: `client_name` (required), `page`, `page_size`.
- **`ingest_documents`** — Trigger document re-ingestion for a client. Parameters: `client_name` (required), `mode` (incremental/complete), `dry_run`.

### Client Intelligence
- **`read_client_memory`** — Read structured client facts, stakeholders, engagements, and pain points from Cosmos DB. Parameters: `client_name` (required), `fields`.
- **`write_client_memory`** — Update a field in client memory. Parameters: `client_name`, `field`, `value`, `overwrite`.
- **`generate_insights`** — Analyses, open risks, and overdue action items. Parameters: `client_name` (required), `insight_types`, `max_insights`.
- **`get_client_health`** — Health score and risk assessment. Parameters: `client_name` (required).

### Engagements & Activity
- **`get_engagements`** — Engagement list with optional risks and deliverables. Parameters: `client_name` (required), `status`, `include_risks`, `include_deliverables`.
- **`get_action_items`** — Action items by status or engagement. Parameters: `client_name` (required), `status`, `engagement_id`.
- **`get_client_timeline`** — Chronological event timeline. Parameters: `client_name` (required), `limit`, `event_types`.

### Communications & Briefings
- **`get_client_communications`** — Emails, meetings, and draft replies from Outlook/Graph. Parameters: `client_name` (required), `comm_type`, `limit`, `lookback_days`.
- **`generate_briefing`** — Executive briefing with recent analyses, overdue items, and risk changes. Parameters: `client_name` (required), `since`.

## Error Handling

When a tool returns `{"error": {...}}`, check:
- `error.code` — one of: `NOT_FOUND`, `INTERNAL_ERROR`, `INVALID_INPUT`
- `error.trace_id` — include in bug reports
- Retry transient errors after a brief delay

## Auth Note

Set `CLIENT_AGENT_MCP_TOKEN` in your environment to your Entra ID Bearer token.
For local development with `LOCAL_MODE=true`, any non-empty token value works.
