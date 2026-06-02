# Client-Agent MCP Server — Claude Code / Claude Desktop Setup

## Prerequisites

- Client-Agent backend running locally: `uvicorn app.main:app --port 8000`
- `LOCAL_MODE=true` in your `.env` for development (skips JWT validation)

## Install for Claude Desktop

Copy `claude_desktop_config.json` to:

- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`

Restart Claude Desktop after saving.

## Install for Claude Code (CLI)

Add to `~/.claude/claude_desktop_config.json` (same format, same location).

Or run Claude Code from the repo root with:

```
claude
```

Claude Code auto-discovers the config at `%APPDATA%\Claude\claude_desktop_config.json`.

## Production Use

Replace the `Authorization` header value with a valid Entra ID Bearer token:

```json
"headers": {
  "Authorization": "Bearer <your-entra-id-token>"
}
```

## Available Tools

| Tool | Description |
|---|---|
| `search_client_documents` | Hybrid vector + BM25 search across indexed client files |
| `ingest_documents` | Trigger document ingestion for a client |
| `read_client_memory` | Read structured client intelligence from Cosmos DB |
| `write_client_memory` | Update client memory fields |
| `list_indexed_files` | Browse the document metadata index |
| `generate_insights` | Analyses, risks, and open action items |
| `get_client_communications` | Emails, meetings, and draft replies |
| `get_engagements` | Engagement list with optional risks and deliverables |
| `get_client_timeline` | Chronological event timeline |
| `get_action_items` | Action items by status or engagement |
| `get_client_health` | Health score and risk assessment |
| `generate_briefing` | Executive briefing with recent changes |

## Verify

```
GET http://localhost:8000/mcp/health
→ {"status": "ok", "transport": "http+sse", "tools": 12}

GET http://localhost:8000/mcp/tools
→ {"tools": [...], "count": 12}
```
