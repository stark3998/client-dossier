# API Reference

All routes are prefixed with the base URL of the backend (default: `http://localhost:8000`).

Protected routes require `Authorization: Bearer <token>`. In `LOCAL_MODE`, auth is bypassed. MCP routes also accept the static `MCP_API_KEY` as a bearer token.

---

## Health Probes

| Method | Path | Auth | Description |
| --- | --- | --- | --- |
| GET | `/health` | None | Liveness — always 200 |
| GET | `/ready` | None | Readiness — checks Cosmos DB and AI Search |

---

## Clients

| Method | Path | Description |
| --- | --- | --- |
| GET | `/api/clients` | List all clients (filesystem + master DB) |
| POST | `/api/clients` | Onboard a new client. Creates folder, isolated Cosmos DB, initial memory. |

---

## Chat

| Method | Path | Description |
| --- | --- | --- |
| WebSocket | `/ws/chat` | Streaming chat. Send `{type, content, client_name}`. See [WebSocket Protocol](#websocket-chat-protocol). |
| POST | `/api/chat` | Non-streaming REST fallback |

---

## Files

| Method | Path | Description |
| --- | --- | --- |
| GET | `/api/files/tree?path=` | Recursive file tree from OneDrive sync path |
| GET | `/api/files/preview?path=` | Extracted text preview of a document |
| POST | `/api/files/upload` | Upload file (`multipart/form-data`: `file` + `client_name`). Triggers ingestion and LLM analysis. |

---

## Ingestion

| Method | Path | Description |
| --- | --- | --- |
| POST | `/api/ingest` | Trigger ingestion. Body: `{path, client_name, mode}` |
| GET | `/api/ingest/{job_id}` | Poll job status and progress |

---

## Client Memory

| Method | Path | Description |
| --- | --- | --- |
| GET | `/api/insights?client_name=` | Full client memory: stakeholders, engagements, pain points, priorities |
| GET | `/api/memory/{client_name}` | Raw memory document |
| PUT | `/api/memory/{client_name}` | Update memory fields |

---

## Document Analysis

| Method | Path | Description |
| --- | --- | --- |
| GET | `/api/analysis/{client_name}` | List all LLM analysis results for a client |
| GET | `/api/analysis/{client_name}/{id}` | Get one analysis result |

---

## Engagements

| Method | Path | Description |
| --- | --- | --- |
| GET | `/api/clients/{name}/engagements` | List all engagements |
| POST | `/api/clients/{name}/engagements` | Create an engagement |
| GET | `/api/clients/{name}/engagements/{id}` | Get engagement details |
| PUT | `/api/clients/{name}/engagements/{id}` | Update an engagement |
| DELETE | `/api/clients/{name}/engagements/{id}` | Delete an engagement |

---

## Deliverables

| Method | Path | Description |
| --- | --- | --- |
| GET | `/api/clients/{name}/engagements/{id}/deliverables` | List deliverables for an engagement |
| POST | `/api/clients/{name}/engagements/{id}/deliverables` | Create a deliverable |
| PUT | `/api/clients/{name}/deliverables/{id}` | Update a deliverable |

---

## Risks

| Method | Path | Description |
| --- | --- | --- |
| GET | `/api/clients/{name}/engagements/{id}/risks` | List risks for an engagement |
| POST | `/api/clients/{name}/engagements/{id}/risks` | Create a risk |
| GET | `/api/clients/{name}/risks` | All risks across all engagements |

---

## Status Updates

| Method | Path | Description |
| --- | --- | --- |
| GET | `/api/clients/{name}/engagements/{id}/status-updates` | List status updates |
| POST | `/api/clients/{name}/engagements/{id}/status-updates` | Create a status update |

---

## Interactions

| Method | Path | Description |
| --- | --- | --- |
| GET | `/api/clients/{name}/interactions` | List all interactions |
| POST | `/api/clients/{name}/interactions` | Log an interaction |

---

## Timeline

| Method | Path | Description |
| --- | --- | --- |
| GET | `/api/clients/{name}/timeline?limit=50` | Unified timeline: interactions + status updates + analyses |

---

## Action Items

| Method | Path | Description |
| --- | --- | --- |
| GET | `/api/clients/{name}/action_items` | List action items. Params: `status`, `engagement_id` |
| POST | `/api/clients/{name}/action_items` | Create an action item |
| PUT | `/api/clients/{name}/action_items/{id}` | Update status |

---

## Client Health & Briefing

| Method | Path | Description |
| --- | --- | --- |
| GET | `/api/client_health/{name}` | Health score, risk level, overdue items, engagement status |
| GET | `/api/briefing/{name}` | Executive briefing: recent analyses, overdue items, risk changes |

---

## Notifications

| Method | Path | Description |
| --- | --- | --- |
| GET | `/api/notifications` | List recent notifications |
| WebSocket | `/ws/notifications` | Real-time push from EventBus |

---

## MCP — External Server Management

| Method | Path | Description |
| --- | --- | --- |
| GET | `/api/mcp/servers` | List configured external MCP servers |
| POST | `/api/mcp/servers` | Register and connect a new server |
| GET | `/api/mcp/servers/{id}` | Get server details and status |
| PUT | `/api/mcp/servers/{id}` | Update configuration |
| DELETE | `/api/mcp/servers/{id}` | Remove and disconnect |
| POST | `/api/mcp/servers/{id}/test` | Test connectivity |
| POST | `/api/mcp/invoke` | Invoke a built-in MCP tool. Body: `{tool_name, arguments}` |

---

## Built-in MCP Server

| Method | Path | Auth | Description |
| --- | --- | --- | --- |
| GET | `/mcp/sse` | Required | SSE stream — persistent MCP session |
| POST | `/mcp/message` | Required | JSON-RPC message for an active session |
| GET | `/mcp/tools` | None | Tool manifest |
| GET | `/mcp/health` | None | Liveness probe |

---

## Communications

| Method | Path | Description |
| --- | --- | --- |
| GET | `/api/communication/{name}/accounts` | List Outlook accounts |
| GET | `/api/communication/{name}/accounts/{account}/folders` | List folders in an account |
| GET | `/api/communication/{name}/config` | Get scan config |
| PUT | `/api/communication/{name}/config` | Update scan config |
| POST | `/api/communication/{name}/scan` | Trigger manual scan |
| GET | `/api/communication/{name}/scan/status` | Poll live scan progress |
| GET | `/api/communication/{name}/emails` | List emails. Params: `days`, `search`, `folder` |
| GET | `/api/communication/{name}/emails/{id}` | Get email with full body |
| GET | `/api/communication/{name}/meetings` | List meetings. Params: `days`, `upcoming_only` |
| GET | `/api/communication/{name}/meetings/{id}` | Get meeting details |
| POST | `/api/communication/{name}/meetings/{id}/fetch-transcript` | Trigger Teams transcript fetch |
| POST | `/api/communication/{name}/meetings/{id}/respond` | RSVP via win32com |
| GET | `/api/communication/{name}/drafts` | List AI draft replies |
| GET | `/api/communication/{name}/drafts/{id}` | Get draft body |
| PUT | `/api/communication/{name}/drafts/{id}` | Edit draft (subject, body, to, cc) |
| POST | `/api/communication/{name}/drafts/{id}/approve` | Push draft to Outlook Drafts folder |
| POST | `/api/communication/{name}/drafts/{id}/feedback` | Save feedback, update memory |
| POST | `/api/communication/{name}/drafts` | Manually generate draft for an `email_id` |
| DELETE | `/api/communication/{name}/drafts/{id}` | Discard draft |
| GET | `/api/communication/{name}/teams` | List joined Teams |
| GET | `/api/communication/{name}/teams/{team_id}/channels` | List channels |
| GET | `/api/communication/{name}/teams/{team_id}/channels/{ch_id}/messages` | Get channel messages |
| GET | `/api/communication/{name}/threads` | Emails grouped into threads. Params: `days`, `search` |
| GET | `/api/communication/{name}/threads/{thread_key}` | All emails in thread |
| WebSocket | `/ws/communication/{name}/threads/{key}/insight` | Stream AI insight for a thread |

---

## Tools

| Method | Path | Description |
| --- | --- | --- |
| GET | `/api/tools` | All tools: SK plugins + MCP + custom |
| GET | `/api/tools/{plugin}/{function}` | Tool details and parameter schema |
| POST | `/api/tools/invoke` | Invoke a tool. Body: `{plugin, function, arguments}` |
| POST | `/api/tools/custom` | Create a custom prompt-based tool |
| PUT | `/api/tools/custom/{id}` | Update a custom tool |
| DELETE | `/api/tools/custom/{id}` | Delete a custom tool |

---

## WebSocket Chat Protocol

### Client → Server

```json
{
  "type": "message",
  "content": "What are the open risks for Navy Federal?",
  "client_name": "Navy Federal"
}
```

### Server → Client Event Types

| Type | Fields | When emitted |
| --- | --- | --- |
| `token` | `content: str` | Each streaming text chunk from the LLM |
| `source` | `source: {file_path, section_title, page_number, excerpt, score}` | Search plugin citation |
| `thought` | `content: str` | Between ReAct iterations |
| `plan` | `plan_steps: str[]` | Plan-and-Execute generated plan |
| `plan_step` | `content: str, step_number: int, step_total: int` | Each step during execution |
| `tool_call` | `tool_name: str, tool_args: dict, tool_source: "mcp" \| null` | Before each tool invocation |
| `tool_result` | `tool_name: str, content: str, tool_source: "mcp" \| null` | After tool returns (max 500 chars) |
| `error` | `message: str` | Exception in agent loop |
| `done` | — | Stream complete |

`tool_source: "mcp"` is set when the plugin name starts with `"MCP_"` (a dynamically registered external MCP server). Built-in Semantic Kernel plugins yield `tool_source: null`.
