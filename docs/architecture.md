# Client Intelligence Agent — Architecture Reference

This document is the single authoritative technical reference for the system. It covers
every major subsystem, the exact startup sequence, all data flows end-to-end, the database
schema, the WebSocket protocol, and the extension points a developer needs to modify or
extend the platform.

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Service Initialization Order](#2-service-initialization-order)
3. [FastAPI Router Map](#3-fastapi-router-map)
4. [Authentication Middleware](#4-authentication-middleware)
5. [Semantic Kernel Plugin Architecture](#5-semantic-kernel-plugin-architecture)
6. [ReAct Agent Loop](#6-react-agent-loop)
7. [Plan-and-Execute Path](#7-plan-and-execute-path)
8. [MCP Server Architecture](#8-mcp-server-architecture)
9. [Data Flows](#9-data-flows)
10. [Communication Scanning](#10-communication-scanning)
11. [Frontend Architecture](#11-frontend-architecture)
12. [WebSocket Streaming Protocol](#12-websocket-streaming-protocol)
13. [Database Schema](#13-database-schema)
14. [Infrastructure and Deployment](#14-infrastructure-and-deployment)
15. [Design System Tokens](#15-design-system-tokens)
16. [Extension Points](#16-extension-points)

---

## 1. System Overview

```
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
|  AuthMiddleware  (Entra ID JWT / MCP_API_KEY / LOCAL_MODE)       |
|                                                                  |
|  +--------------------+    +--------------------------------+    |
|  |  AgentPlanner      |    |  Ingestion Pipeline            |    |
|  |  Semantic Kernel   |    |  parse -> chunk -> embed ->    |    |
|  |  8 SK Plugins      |    |  Azure AI Search upsert        |    |
|  |  ReAct / Plan-Exec |    +--------------------------------+    |
|  +--------------------+                                         |
|  +--------------------+    +--------------------------------+    |
|  |  Built-in MCP      |    |  CommunicationScanner          |    |
|  |  Server (14 tools) |    |  win32com + Graph API          |    |
|  |  SSE transport     |    |  email / calendar / Teams      |    |
|  +--------------------+    +--------------------------------+    |
|  +--------------------+    +--------------------------------+    |
|  |  MCPManager        |    |  AlertChecker                  |    |
|  |  Dynamic external  |    |  stale-client / risk alerts    |    |
|  |  MCP servers       |    |  every 900 s                   |    |
|  +--------------------+    +--------------------------------+    |
|                                                                  |
|  EventBus (in-process pub/sub) -> WebSocket push                 |
+------+--------+--------+--------+---------+--------------------+
       |        |        |        |         |
       v        v        v        v         v
  Cosmos DB  AI Search  Azure   App      OneDrive
  (NoSQL)    (hybrid)   OpenAI  Insights  sync path
  master DB  BM25 +     gpt-4o  OTel      /mnt/onedrive
  + per-     vector     embed-  traces
  client DBs 3072-dim   3-large
```

The backend is a single FastAPI process. All service singletons are initialized at startup
via `dependencies.py` and wired together before any request is served.

---

## 2. Service Initialization Order

`startup_services()` in `backend/app/dependencies.py` runs during the FastAPI lifespan
event. Services initialize in this exact order:

```
startup_services():
  1.  CosmosClientManager
        connect to master DB "clientagent"
        lazy per-client DB init on first access

  2.  EventBus
        in-process pub/sub
        initialized with cosmos_manager reference

  3.  SearchService
        connect Azure AI Search
        ensure_index() — create index if missing

  4.  EmbeddingService
        connect Azure OpenAI text-embedding-3-large (3072 dim)

  5.  create_kernel()
        AzureChatCompletion: gpt-4o
        max_tokens=4096, temperature=0.3

  6.  8 SK plugins registered:
        Search        = SearchPlugin(search_svc, embedding_svc)
                        QueryRewriter wired in after plugin construction
        Memory        = MemoryPlugin(cosmos_manager)
        Files         = FilePlugin()
        DocumentGen   = DocumentGenerationPlugin()
        Engagements   = EngagementPlugin(cosmos_manager, event_bus)
        Reporting     = ReportingPlugin(cosmos_manager)
        WebSearch     = WebSearchPlugin(settings)   [Tavily API key]
        Communication = CommunicationPlugin(cosmos_manager, comm_access)

  7.  Communication services:
        OutlookWin32Service   (local Outlook via win32com)
        GraphAPIService       (Microsoft Graph REST API fallback)
        CommunicationAccess   (facade, tries win32com first)
        CommunicationPlugin   (wraps CommunicationAccess for agent)

  8.  AgentPlanner
        adds all 8 plugins to kernel
        wires ContextInjector and ConversationManager

  9.  MCPManager
        loads saved external MCP servers from Cosmos
        connects each -> DynamicMCPPlugin -> register_per_tool_functions(kernel)
        registers built-in server metadata (id="__local__", 14 tools, display only)

  10. ToolManager
        loads custom tools from Cosmos custom_tools container
        registers each as KernelFunctionFromPrompt

  11. AlertChecker
        asyncio.create_task(_run_loop())
        polls every 900 s for stale clients and high-risk conditions

  12. CommunicationScanner
        asyncio.create_task(_run_loop())
        polls every COMM_SCAN_INTERVAL seconds (default 900)
        scans Outlook/Graph for emails and calendar items

  13. EventBus subscriber wired:
        event_bus.subscribe(notification_manager.broadcast)
        all published events -> WebSocket push to connected frontend clients

  14. FileWatcher (optional)
        starts watchdog observer if ONEDRIVE_SYNC_PATH directory exists
        triggers ingestion on new/modified files
```

**Shutdown** (`shutdown_services()`): stops CommunicationScanner, AlertChecker,
FileWatcher; closes Search, Embedding, and Cosmos connections in reverse order.

---

## 3. FastAPI Router Map

All routers are mounted in `backend/app/main.py`. Auth middleware runs on every route
except `/health`, `/ready`, `/mcp/tools`, and `/mcp/health`.

```
Path prefix                             Source file                  Tags
-----------                             -----------                  ----
/health, /ready                         api/health.py                health
/api/ingest                             api/ingest.py                ingestion
/api/files                              api/files.py                 files
/ws/chat, /api/chat                     api/chat.py                  chat
/api/insights                           api/insights.py              insights
/api/memory                             api/memory.py                memory
/api/clients                            api/clients.py               clients
/api/analysis                           api/analysis.py              analysis
/api/clients/{name}/engagements         api/engagements.py           engagements
  /deliverables, /risks, /status-updates,
  /interactions
/api/clients/{name}/timeline            api/timeline.py              timeline
/api/tools                              api/tools.py                 tools
/api/mcp                                api/mcp.py                   mcp-management
/api/clients/{name}/action_items        api/action_items.py          action-items
/api/client_health                      api/client_health.py         health-scores
/api/notifications                      api/notifications.py         notifications
/ws/notifications                       api/notifications.py         notifications-ws
/api/briefing                           api/briefing.py              briefing
/api/communication                      api/communication.py         communication
/ws/communication                       api/communication.py         communication-ws
/mcp/sse, /mcp/message,                 mcp_server/router.py         MCP Server
/mcp/tools, /mcp/health
```

Total: 16 distinct router modules, 1 MCP server router.

---

## 4. Authentication Middleware

`AuthMiddleware` in `backend/app/api/auth.py` wraps every request.

```
Incoming request
      |
      v
  LOCAL_MODE=true OR BYPASS_AUTH=true?
      |-- YES --> set request.state.user = mock_user, pass through
      |
      v
  Authorization header present?
      |-- NO  --> 401 Unauthorized (except public routes: /health, /mcp/tools, /mcp/health)
      |
      v
  Header == "Bearer {MCP_API_KEY}"?  (MCP_API_KEY set in config)
      |-- YES --> set request.state.user = {sub: "mcp-client"}, pass through
      |
      v
  Validate Entra ID JWT:
      fetch JWKS from https://login.microsoftonline.com/{tenant}/discovery/v2.0/keys
      verify signature, audience (ENTRA_CLIENT_ID), issuer (v2.0)
      |-- FAIL --> 401 Unauthorized
      |-- PASS --> set request.state.user = JWT claims dict
      |
      v
  Handler runs with request.state.user available
```

---

## 5. Semantic Kernel Plugin Architecture

### Plugin Registration

Each plugin is a Python class with methods decorated `@kernel_function`. The `AgentPlanner`
adds them to the kernel at startup via `kernel.add_plugin(instance, plugin_name=name)`.

```
Kernel
  |-- "Search"        -> SearchPlugin
  |     search_documents(query, client_name, top_k)
  |     [internally: QueryRewriter.rewrite() -> embed -> hybrid_search]
  |
  |-- "Memory"        -> MemoryPlugin
  |     recall_client_memory(client_name)
  |     update_client_memory(client_name, field, value)
  |     recall_engagements(client_name)
  |     create_engagement(client_name, name, description)
  |     recall_risks(client_name, engagement_id?)
  |     recall_recent_interactions(client_name)
  |     log_interaction(client_name, type, notes, attendees, date)
  |
  |-- "Files"         -> FilePlugin
  |     list_files(client_name)
  |     read_file_preview(file_path)
  |
  |-- "DocumentGeneration" -> DocumentGenerationPlugin
  |     generate_presentation(client_name, title, content)
  |     generate_document(client_name, title, content)
  |
  |-- "Engagements"   -> EngagementPlugin
  |     get_engagements(client_name)
  |     update_engagement_status(engagement_id, status)
  |     create_deliverable(engagement_id, name, due_date)
  |     [publishes EventBus events on lifecycle changes]
  |
  |-- "Reporting"     -> ReportingPlugin
  |     generate_report(client_name, report_type)
  |
  |-- "WebSearch"     -> WebSearchPlugin
  |     web_search(query)   [Tavily API]
  |
  |-- "Communication" -> CommunicationPlugin
  |     get_emails(client_name, lookback_days)
  |     get_meetings(client_name, lookback_days)
  |     get_draft_replies(client_name)
  |
  |-- "MCP_{name}"    -> DynamicMCPPlugin (one per registered external server)
  |     per-tool functions (one SK function per discovered MCP tool)
  |     fallback: query_mcp_server, invoke_mcp_tool, list_mcp_tools
  |
  |-- "CustomTools"   -> KernelFunctionFromPrompt (one per custom tool)
        prompt template with {{$input}} substitution
```

### ContextInjector (`agent/context_injector.py`)

Called before every chat request. Fetches from Cosmos in parallel and assembles a
2000-token system message block injected into chat history:

```
ContextInjector.build_context_block(client_name):
  parallel Cosmos queries:
    -> memories container    : client memory (stakeholders, priorities, pain points)
    -> interactions container: last 5 interactions
    -> risks container       : open/high-severity risks
    -> action_items container: overdue items
  assemble:
    "## Client Context: {client_name}
     Stakeholders: ...
     Strategic priorities: ...
     Open risks: ...
     Overdue action items: ...
     Recent interactions: ..."
  inject as chat_history.add_system_message(block)
```

### ConversationManager (`agent/conversation_manager.py`)

Prevents token exhaustion in long sessions:

```
ConversationManager.maybe_summarize(chat_history):
  count tokens in history
  if total > 8000 tokens:
    take oldest messages (all but last 6)
    gpt-4o: "Summarize this conversation history in 3-5 sentences"
    -> summary string
    remove old messages from history
    prepend summary as system message
    retain last 6 messages verbatim
```

### Query Routing

```
AgentPlanner.stream_response(history, message, client_name):
  -> ConversationManager.maybe_summarize(history)
  -> ContextInjector.build_context_block(client_name)
  -> is_complex_query(message)?
       criteria: contains "compare", "across all", "for each", "summarize all",
                 "every engagement", "full report"; OR len(message) > 150
       YES -> plan_and_execute(kernel, history, settings, message)
       NO  -> run_react_loop(kernel, history, settings)
  -> yield StreamEvent items to WebSocket
```

---

## 6. ReAct Agent Loop

`backend/app/agent/react_loop.py` — `run_react_loop()`. Manual loop, `auto_invoke=False`.
Maximum 10 iterations.

```
run_react_loop(kernel, chat_history, execution_settings):

  for iteration in range(10):

    [LLM CALL]
    response = AzureChatCompletion.get_streaming_chat_message_content(
        chat_history=chat_history,
        settings=execution_settings,  # auto_invoke=False
        kernel=kernel,
    )

    [STREAM TOKENS]
    async for chunk in response:
      text = str(chunk)
      if text: yield StreamEvent(type="token", content=text)

    [REDUCE]
    result_content = reduce(all_chunks)

    [CHECK FOR TOOL CALLS]
    function_calls = [item for item in result_content.items
                      if isinstance(item, FunctionCallContent)]

    if not function_calls:
      chat_history.add_assistant_message(full_text)
      break   # agent finished

    chat_history.add_message(result_content)  # includes function call metadata

    [EXECUTE TOOLS]
    for fc in function_calls:
      tool_name = "{plugin_name}.{function_name}"
      tool_source = "mcp" if plugin_name.startswith("MCP_") else None

      yield StreamEvent(type="tool_call",
                        tool_name=tool_name,
                        tool_args=fc.arguments,
                        tool_source=tool_source)

      result = await kernel.invoke_function_call(fc, chat_history)
      display = str(result)[:500]

      yield StreamEvent(type="tool_result",
                        tool_name=tool_name,
                        tool_source=tool_source,
                        content=display)

      # extract document citations from JSON result
      for source in _extract_sources(str(result)):
        yield StreamEvent(type="source", source=source)

    yield StreamEvent(type="thought",
                      content=f"Processing results from {N} tool(s)...")

  yield StreamEvent(type="done")
```

`tool_source` field is `"mcp"` for tools registered by `DynamicMCPPlugin` (plugin name
starts with `"MCP_"`), `null` for built-in SK plugins.

---

## 7. Plan-and-Execute Path

`backend/app/agent/planner_executor.py` — activated for complex multi-step queries.

```
plan_and_execute(kernel, chat_history, settings, user_message):

  [GENERATE PLAN]
  system = "You are a planning agent. Generate a JSON plan: [{step, tool, args}]"
  plan_json = await kernel.invoke_prompt(planning_prompt)
  steps = json.loads(plan_json)
  yield StreamEvent(type="plan", plan_steps=[s["step"] for s in steps])

  [EXECUTE STEPS]
  for i, step in enumerate(steps):
    yield StreamEvent(type="plan_step",
                      content=step["step"],
                      step_number=i+1,
                      step_total=len(steps))

    # run each step through the ReAct loop
    step_history = ChatHistory()
    step_history.add_user_message(step["step"])
    async for event in run_react_loop(kernel, step_history, settings):
      yield event

  yield StreamEvent(type="done")
```

---

## 8. MCP Server Architecture

### 8.1 Built-in MCP Server

Exposed at `/mcp` prefix (mounted in `main.py`). Implements the Model Context Protocol
over SSE transport. External MCP clients (Claude Desktop, Cursor, etc.) connect here.

```
Endpoints:
  GET  /mcp/sse      SSE stream — persistent MCP session, requires auth
  POST /mcp/message  JSON-RPC messages for active sessions, requires auth
  GET  /mcp/tools    Tool manifest, public (no auth)
  GET  /mcp/health   Liveness probe, public (no auth)
```

Auth: `AuthMiddleware` runs before SSE connection. Bearer token is either `MCP_API_KEY`
(static secret) or a valid Entra ID JWT.

`_caller_identity` is a Python `ContextVar` set by `router.py` per request to carry the
authenticated user identity into the MCP session.

**14 built-in tools in 5 categories:**

```
Category: Search & Documents
  search_client_documents  hybrid vector + BM25 search, returns ranked chunks
  ingest_documents         trigger re-ingestion from OneDrive sync folder
  list_indexed_files       list doc_index metadata for a client
  get_ingest_status        poll ingest job by job_id

Category: Client Intelligence
  read_client_memory       fetch structured memory (stakeholders, priorities, etc.)
  write_client_memory      append or overwrite a memory field
  generate_insights        memory + analyses + risks + action_items summary
  get_client_health        health score, risk level, engagement status
  get_clients              list all known clients

Category: Engagements
  get_engagements          list engagements, optionally with risks/deliverables
  get_action_items         list action items, filterable by status/engagement
  get_client_timeline      unified chronological event stream

Category: Communications
  get_client_communications  emails, meetings, and drafts from communication store

Category: Reporting
  generate_briefing        executive briefing: analyses + overdue items + risks
```

**Tool dispatch in `server.py`:**

```python
_TOOL_DISPATCH: dict = {}

def _build_dispatch():
    # lazy-initialized on first call_tool invocation
    _TOOL_DISPATCH.update({
        "search_client_documents": search.search_client_documents,
        "ingest_documents":        ingest.ingest_documents,
        "get_ingest_status":       ingest.get_ingest_status,
        "read_client_memory":      memory.read_client_memory,
        "write_client_memory":     memory.write_client_memory,
        "list_indexed_files":      files.list_indexed_files,
        "generate_insights":       insights.generate_insights,
        "get_client_communications": communications.get_client_communications,
        "get_engagements":         engagements.get_engagements,
        "get_client_timeline":     timeline.get_client_timeline,
        "get_action_items":        action_items.get_action_items,
        "get_client_health":       client_health.get_client_health,
        "generate_briefing":       briefing.generate_briefing,
        "get_clients":             clients.get_clients,
    })

async def dispatch_tool(name, arguments) -> dict:
    if not _TOOL_DISPATCH: _build_dispatch()
    handler = _TOOL_DISPATCH.get(name)
    if handler is None: return {"error": {"code": "NOT_FOUND"}}
    return await handler(arguments)
```

`handle_call_tool()` adds tracing: generates `trace_id = uuid4()`, logs
`tool_call_start` and `tool_call_success` / `tool_call_error` with duration_ms via
`mcp_logger`.

**Direct HTTP invocation (bypasses SSE):**

`POST /api/mcp/invoke {tool_name, arguments}` calls `dispatch_tool()` directly. Used by
the ToolBrowser component in the frontend to test tools without establishing an SSE
session.

### 8.2 External MCP Servers (Dynamic)

`MCPManager` in `services/mcp_manager.py`:

```
MCPManager.load_saved_servers():
  query Cosmos master DB "mcp_servers" container
  for each server config:
    plugin = DynamicMCPPlugin(name, endpoint, auth_type, auth_config, protocol)
    await plugin.connect()
      protocol == "sse":
        sse_client(endpoint, headers) -> (read, write) streams
        ClientSession(read, write).initialize()
        session.list_tools() -> self._tools
      protocol == "rest":
        GET /tools -> self._tools
    if connected:
      plugin.register_per_tool_functions(kernel, "MCP_{name}")
        for each tool:
          create async closure calling invoke_tool(t_name, arguments_json)
          decorate with @kernel_function(name=t_name, description=enriched_desc)
          kernel.add_function(plugin_name="MCP_{name}", function=decorated)
      status -> "connected"
    else:
      register generic plugin (3 functions: query_mcp_server, invoke_mcp_tool, list_mcp_tools)
      status -> "error"
    persist status to Cosmos
```

`DynamicMCPPlugin.register_per_tool_functions()` enriches the SK function description
with the tool's JSON schema parameter list (name, type, required flag, description) so
the LLM knows exactly what arguments to pass.

---

## 9. Data Flows

### 9.1 Chat Message Flow

```
User types message
  |
  v
ChatInput.tsx
  useChat.sendMessage(content, client_name)
    WS.send(JSON.stringify({type:"message", content, client_name}))
  |
  v
backend api/chat.py ws_endpoint
  receive JSON, parse {type, content, client_name}
  planner = get_planner()
  chat_history = ChatHistory()  [in-memory per WS connection]
  |
  v
AgentPlanner.stream_response(chat_history, content, client_name)
  |
  +-- ConversationManager.maybe_summarize(history)
  |     if tokens > 8000: gpt-4o summary, trim history
  |
  +-- ContextInjector.build_context_block(client_name)
  |     parallel: memory, interactions, risks, action_items from Cosmos
  |     assemble 2000-token system message
  |     history.add_system_message(block)
  |
  +-- is_complex_query(message)?
  |     YES -> plan_and_execute() [generates JSON plan, executes each step]
  |     NO  -> run_react_loop()   [manual ReAct, max 10 iterations]
  |
  for each StreamEvent yielded:
    ws.send_text(event.model_dump_json(exclude_none=True))
  |
  v
useChat.ws.onmessage(event)
  data = JSON.parse(event.data)
  switch data.type:
    "token"      -> appendToken(data.content)    -> streamBuffer in Zustand
    "source"     -> addStreamSource(data.source) -> streamSources[]
    "thought"
    "plan"
    "plan_step"
    "tool_call"
    "tool_result" -> addReasoningStep(step)      -> streamReasoning[]
    "done"        -> finalizeStream()            -> completed ChatMessage
    "error"       -> finalizeStream(), log
  |
  v
ChatTerminal renders:
  StreamingResponse.tsx  (live: streamBuffer + cursor blink)
  MessageBubble.tsx      (final: markdown + SourceCard chips)
  ReasoningSteps.tsx     (collapsible thought/tool/plan trace, MCP badge)
```

### 9.2 Document Ingestion Flow

```
User drops file on FileUpload.tsx
  POST /api/files/upload
    multipart: file (binary) + client_name (string)
  |
  v
api/files.py
  save file -> {ONEDRIVE_SYNC_PATH}/{client_name}/{filename}
  asyncio.create_task(run_ingestion(job))      [Stage 1, non-blocking]
  asyncio.create_task(run_analysis(path, name)) [Stage 2, non-blocking]
  return {job_id, status: "started"}
  |
  v
Stage 1: ingestion/pipeline.py

  parse_document(file_path) -> ParsedDocument(sections[])
    .docx  : python-docx, preserves heading hierarchy -> sections
    .pptx  : python-pptx, one section per slide
    .xlsx  : openpyxl, one section per sheet
    .pdf   : pdfplumber per page (pymupdf fallback)
    .msg   : extract-msg, subject + body + sender fields
    .eml   : stdlib email, subject + body + sender fields
    .txt/.md: raw text

  chunk(sections, max_tokens=800, overlap=100) -> List[Chunk]
    tiktoken tokenizer; respects section boundaries

  embed_batch(chunks, batch_size=16) -> List[float[3072]]
    Azure OpenAI text-embedding-3-large

  search_service.upsert_chunks(chunks_with_embeddings)
    Azure AI Search: vector (3072-dim HNSW) + keyword fields
    filter field: client_name

  doc_index_repo.upsert({file_path, content_hash, chunk_count, last_indexed})
    Cosmos client_{id}/doc_index for dedup tracking

  job_repo.update({status:"complete", files_processed:N})

Stage 2: services/analysis.py

  truncate document text to ~8000 tokens
  gpt-4o structured extraction prompt:
    -> stakeholders [{name, title, email}]
    -> action_items [{description, owner, due_date}]
    -> risks [{description, severity}]
    -> dates [{label, date}]
    -> classification (e.g. "proposal", "status report", "contract")
  store AnalysisResult in Cosmos client_{id}/analyses

  merge into ClientMemory:
    stakeholders: dedup by name + title
    action_items: dedup by description
    risks: append (no dedup, track severity)
    strategic_priorities: merge list
```

### 9.3 Hybrid Search at Query Time

```
SearchPlugin.search_documents(query, client_name, top_k):
  |
  +-- QueryRewriter.rewrite(query, chat_history)
  |     LLM rewrites for better retrieval (removes pronouns, adds context)
  |
  +-- EmbeddingService.embed(rewritten_query) -> float[3072]
  |
  +-- SearchService.hybrid_search(text, vector, client_name, top_k):
  |     Azure AI Search:
  |       1. BM25 full-text on {content, file_path, section_title}
  |       2. Vector HNSW cosine on embedding field (3072 dim)
  |       3. Reciprocal Rank Fusion — merge BM25 + vector rank lists
  |       4. Filter: "client_name eq '{client_name}'"
  |       5. Semantic reranker (if RERANK_ENABLED=true):
  |            rerank top-50 candidates -> reordered top_k
  |     -> List[SourceChip {file_path, section_title, page_number, excerpt, score}]
  |
  for each SourceChip: yield StreamEvent(type="source", source=chip)
  return ranked JSON for LLM context window
```

### 9.4 Direct MCP Tool Invocation from UI

```
User opens ToolBrowser -> "MCP Tools" tab
  |
  v
MCPToolList:
  fetch GET /mcp/tools  [public, no auth]
  router.py list_tools_endpoint()
  -> [{name, description, category, inputSchema}] for all 14 tools

User selects tool, fills parameters, clicks Execute:
  |
  v
MCPToolDetail:
  apiFetch POST /api/mcp/invoke
    body: {tool_name, arguments}
  |
  v
api/mcp.py invoke_mcp_tool()
  server.py dispatch_tool(tool_name, arguments)
    _TOOL_DISPATCH[tool_name](arguments)  [direct Python call, no SSE]
    -> dict result
  return {"result": {...}}
  |
  v
MCPToolDetail renders JSON result inline
```

### 9.5 External MCP Client Connection (Claude Desktop etc.)

```
External client connects:
  GET ws://host:8000/mcp/sse
  Header: Authorization: Bearer {MCP_API_KEY}
  |
  v
AuthMiddleware:
  verify Bearer token (MCP_API_KEY or Entra JWT)
  set request.state.user
  |
  v
mcp_router.sse_endpoint(request):
  _caller_identity.set(user)        [ContextVar, per async context]
  SseServerTransport.connect_sse()  -> (read_stream, write_stream)
  mcp_server.run(streams, init_options)
    |
    -> MCP initialize message
    -> list_tools: handle_list_tools() -> TOOL_DEFINITIONS (14 tools)
    -> call_tool(name, arguments):
         _build_dispatch() [once, lazy]
         trace_id = uuid4()
         mcp_logger.log_event("tool_call_start", ...)
         result = await _TOOL_DISPATCH[name](arguments)
         mcp_logger.log_event("tool_call_success", duration_ms=...)
         return [TextContent(text=json.dumps(result))]
```

### 9.6 AlertChecker Background Task

```
AlertChecker._run_loop() every 900 seconds:
  for each client in master DB:
    memory = fetch client memory
    last_interaction_date = interactions container latest entry
    if (now - last_interaction_date) > ALERT_STALE_DAYS (14):
      event_bus.publish(ClientEvent(
        event_type="alert.stale_client",
        summary="No client interaction in 14+ days"
      ))

    for each active engagement:
      overdue_deliverables = deliverables past due_date with status != "complete"
      high_risks = risks with severity > ALERT_RISK_THRESHOLD (15)
      if overdue_deliverables or high_risks:
        event_bus.publish(ClientEvent(event_type="alert.engagement_risk", ...))

  EventBus -> notification_manager.broadcast()
           -> WebSocket push to frontend
           -> Notifications bell in Header updates unreadCount
```

---

## 10. Communication Scanning

`CommunicationScanner` in `backend/app/agent/communication_scanner.py`.
Background asyncio task polling every `COMM_SCAN_INTERVAL` seconds (default 900).

### 10.1 Architecture

```
CommunicationAccess (facade)
  |-- try OutlookWin32Service (win32com, local Outlook)
  |-- fallback GraphAPIService (Microsoft Graph REST)

CommunicationScanner._scan_all_clients():
  master_repo.query("SELECT * FROM c") -> all clients
  for each client:
    config = Cosmos client_{id}/communication_config
    if config exists: scanner.scan_client(client_name, config)
```

### 10.2 Per-Client Scan Cycle

```
scan_client(client_name, config):
  |
  +-- _scan_emails(client_name, client_id, config, since)
  |     for each account in config.accounts:
  |       folders = account.folders + ["Sent Items"] if config.scan_sent
  |       for each folder:
  |         raw_emails = access.get_emails(account, folder, since)
  |         for each email:
  |           cls = _attribute(email, config)  [classify to this client]
  |             checks: domain match, contact match, keyword match
  |             (subject, body, sender, recipients)
  |           if classified:
  |             email_id = sha256(message_id)[:36]
  |             skip if already in Cosmos emails container
  |             scanned = ScannedEmail(...) + classification
  |             email_repo.upsert(scanned)
  |             _update_memory_from_email(client_name, scanned)
  |               -> append sender/recipients to stakeholders in memory
  |             if config.auto_draft and folder=="Inbox":
  |               _maybe_create_draft(client_name, scanned, draft_repo, config)
  |                 -> LLM draft via gpt-4o if kernel available
  |                 -> DraftReply stored in draft_replies container
  |             event_bus.publish("comm_new_email", summary)
  |
  +-- _scan_calendar(client_name, client_id, config, since)
        for each account:
          raw_items = access.get_calendar_events(account, since, until=now+30d)
          for each calendar item:
            meeting_cls = _meeting_matches(item, config)
              checks: domain match in attendee emails, contact match, keyword match
            if classified:
              meeting_id = sha256(global_id)[:36]
              if existing and is_teams_meeting and no transcript yet:
                fetch transcript -> summarize -> extract action items -> update
              if new:
                if is_teams_meeting and meeting already ended:
                  fetch_transcript_summary(online_meeting_id)
                    -> Graph API transcript fetch
                    -> gpt-4o: "Summarize this meeting transcript in < 300 words"
                  extract_action_items(summary)
                    -> gpt-4o: "Extract action items as JSON array"
                meeting_repo.upsert(MeetingLog)
                _update_memory_from_meeting(client_name, meeting)
                event_bus.publish("comm_new_meeting", summary)
```

### 10.3 Classification Logic

Email attribution (in priority order):

```
1. Domain match:   sender or recipient contains "@{config.domain}"
2. Contact match:  sender or recipient exactly matches config.contacts entry
3. Keyword match:  config.keywords found in subject or body
```

Meeting attribution uses same rules applied to attendee email list and subject/body.

### 10.4 Communication API Endpoints

Full endpoint list in `/api/communication/{client_name}/*`:

```
GET  /accounts                                  list Outlook accounts (win32com)
GET  /accounts/{account}/folders               list folders in account
GET  /config                                    get per-client communication config
PUT  /config                                    update config (domains, contacts, keywords, auto_draft)
POST /scan                                      trigger manual scan for this client
GET  /emails                                    list emails (days, search, folder params)
GET  /emails/{id}                               get single email with full body
GET  /meetings                                  list meetings (days, upcoming_only params)
GET  /meetings/{id}                             get single meeting
POST /meetings/{id}/fetch-transcript            trigger Teams transcript fetch (background)
POST /meetings/{id}/respond                     RSVP accept/decline/tentative via win32com
GET  /drafts                                    list AI-generated draft replies
GET  /drafts/{id}                               get draft body
PUT  /drafts/{id}                               edit draft (subject, body, to, cc)
POST /drafts/{id}/approve                       push draft to Outlook Drafts folder
POST /drafts/{id}/feedback                      save feedback, update agent memory
POST /drafts                                    manually generate draft for an email_id
DELETE /drafts/{id}                             discard draft
GET  /teams                                     list joined Teams via Graph API
GET  /teams/{team_id}/channels                  list channels in a team
GET  /teams/{team_id}/channels/{ch_id}/messages get channel messages (days param)
GET  /threads                                   emails grouped into threads (days, search)
GET  /threads/{thread_key}                      all emails in thread (chronological)
WS   /ws/communication/{name}/threads/{key}/insight  stream AI thread insight analysis
```

---

## 11. Frontend Architecture

### 11.1 Component Tree

```
main.tsx
  MsalProvider
  ThemeProvider
  BrowserRouter
    |
    v
  App.tsx (React Router v6)
    |
    +-- Route "/" -> ClientDashboard.tsx
    |     client grid, search, onboarding wizard
    |
    +-- Route "/clients/:clientName" -> ClientWorkspace.tsx
          |
          v
        AppShell.tsx  (three-panel layout, draggable dividers)
          |
          +-- Header (48px)
          |     back nav, client name, theme toggle, profile menu
          |
          +-- Left Panel (default 280px, 200-500px range)
          |     Sidebar.tsx
          |       Tab: Files
          |         FileTree.tsx    (recursive folder tree)
          |         FileUpload.tsx  (drop zone, progress bar)
          |         FilePreview.tsx (extracted text viewer)
          |       Tab: Tools
          |         ToolBrowser.tsx
          |           Sub-tab: "Agent Tools"
          |             SK plugin list + custom tool CRUD
          |           Sub-tab: "MCP Tools"
          |             MCPToolList (fetch /mcp/tools)
          |             MCPToolDetail (inline invoke via /api/mcp/invoke)
          |       Tab: Insights
          |         InsightsSummary.tsx (memory snapshot)
          |
          +-- Center Panel (flex-1)
          |     ChatTerminal.tsx
          |       StreamingResponse.tsx (live: token buffer + cursor)
          |       MessageBubble.tsx     (final: markdown + SourceCard chips)
          |       ReasoningSteps.tsx    (collapsible trace: thought/tool/plan + MCP badge)
          |       ChatInput.tsx         (auto-expand textarea, quick action buttons)
          |
          +-- Right Panel (default 320px, 200-500px range)
          |     InsightsPanel.tsx
          |       client memory summary
          |       StakeholderList.tsx
          |       ActionItems.tsx
          |       nav cards:
          |         Engagements -> /clients/:name/engagements
          |         Risks       -> /clients/:name/risks
          |         Timeline    -> /clients/:name/timeline
          |         Analysis    -> /clients/:name/analysis
          |         Comms       -> /clients/:name/communications
          |
          +-- Footer (32px)
                left/right panel toggles, model name,
                "Built-in MCP" chip, external server badges, "MCP" label

    +-- Route "/clients/:name/engagements"   -> ProjectTracker.tsx  (Kanban board)
    +-- Route "/clients/:name/risks"         -> RiskRegister.tsx
    +-- Route "/clients/:name/timeline"      -> InteractionTimeline.tsx
    +-- Route "/clients/:name/analysis"      -> AnalysisResults.tsx
    +-- Route "/clients/:name/communications" -> CommunicationView.tsx
```

### 11.2 Zustand Store (`stores/clientStore.ts`)

Single global store, organized by domain slice:

```
client:
  activeClient       string | null
  clients            Client[]

files:
  fileTree           FileNode[]
  selectedFile       string | null
  expandedFolders    Set<string>
  ingestionStatus    Record<string, IngestionJob>

chat:
  messages           ChatMessage[]
  isStreaming        boolean
  streamBuffer       string             (accumulates token events)
  streamSources      SourceChip[]
  streamReasoning    ReasoningStep[]    (thought/tool/plan events during stream)

insights:
  clientMemory       ClientMemory | null

mcp:
  mcpServers         MCPServerConfig[]
  showMCPPanel       boolean
  lastIndexed        string | null

ui:
  leftPanelWidth     number  (200-500, default 280)
  rightPanelWidth    number  (200-500, default 320)
  leftPanelCollapsed boolean
  rightPanelCollapsed boolean
  activeLeftTab      "files" | "tools" | "insights"
  activeToolsTab     "agent" | "mcp"

uploads:
  uploads            Record<string, UploadProgress>

notifications:
  notifications      Notification[]
  unreadCount        number

health:
  clientHealthScores Record<string, HealthScore>
```

### 11.3 Authentication (`auth/`)

```
AuthProvider wraps app with MsalProvider (msalInstance from auth/config.ts)

apiFetch(path, options):
  account = msalInstance.getAllAccounts()[0]
  tokenResponse = await msalInstance.acquireTokenSilent({
    scopes: ["api://{ENTRA_CLIENT_ID}/.default"],
    account
  })
  fetch(path, {
    ...options,
    headers: { Authorization: "Bearer {tokenResponse.accessToken}", ...options.headers }
  })

getAuthenticatedWsUrl(path):
  token = await acquireTokenSilent(...)
  return `${WS_BASE}${path}?token=${token}`

LOCAL_MODE: token acquisition is skipped; mock user returned
```

### 11.4 useChat Hook (`hooks/useChat.ts`)

```
useChat(clientName):
  ws = new WebSocket(getAuthenticatedWsUrl("/ws/chat"))

  ws.onclose = () => setTimeout(reconnect, 3000)   [auto-reconnect]

  sendMessage(content):
    ws.send(JSON.stringify({type:"message", content, client_name: clientName}))
    setIsStreaming(true)

  ws.onmessage = (event):
    data = JSON.parse(event.data)
    switch data.type:
      "token"      -> appendToken(data.content)
      "source"     -> addStreamSource(data.source)
      "thought"    -> addReasoningStep({type:"thought", content})
      "plan"       -> addReasoningStep({type:"plan", plan_steps})
      "plan_step"  -> addReasoningStep({type:"plan_step", content, step_number, step_total})
      "tool_call"  -> addReasoningStep({type:"tool_call", tool_name, tool_args, tool_source})
      "tool_result"-> addReasoningStep({type:"tool_result", tool_name, content, tool_source})
      "done"       -> finalizeStream() -> ChatMessage{role:"assistant", content:buffer, sources}
      "error"      -> finalizeStream(), console.error
```

---

## 12. WebSocket Streaming Protocol

### Client to Server

```json
{
  "type": "message",
  "content": "What are the open risks for the Contoso engagement?",
  "client_name": "Contoso"
}
```

### Server to Client — All Event Types

| Event type   | Fields                                                              | When emitted                          |
|-------------|----------------------------------------------------------------------|---------------------------------------|
| `token`      | `content: str`                                                      | Each streaming text chunk from LLM    |
| `source`     | `source: {file_path, section_title, page_number, excerpt, score}`  | Search plugin citation                |
| `thought`    | `content: str`                                                      | Between ReAct iterations              |
| `plan`       | `plan_steps: str[]`                                                 | Plan-and-execute generated plan       |
| `plan_step`  | `content: str, step_number: int, step_total: int`                  | Each step of plan execution           |
| `tool_call`  | `tool_name: str, tool_args: dict, tool_source: "mcp" \| null`      | Before each tool invocation           |
| `tool_result`| `tool_name: str, content: str (max 500 chars), tool_source`        | After tool returns result             |
| `error`      | `message: str`                                                      | Exception in agent loop               |
| `done`       | (no additional fields)                                              | Stream complete                       |

`tool_source: "mcp"` is set when the Semantic Kernel plugin name starts with `"MCP_"`,
indicating the call went to a dynamically registered external MCP server.

`source` events may be emitted before, during, or after token events, but always before
`done`. The frontend accumulates sources in `streamSources[]` and attaches them to the
final `ChatMessage` on `finalizeStream()`.

### Chat WebSocket URL

```
ws://localhost:8000/ws/chat          (LOCAL_MODE)
wss://host/ws/chat?token={JWT}       (production, auth via query param)
```

---

## 13. Database Schema

### Master Database (`clientagent`)

Provisioned by Terraform. All containers use `/id` as partition key.

| Container      | Partition Key | Fields                                                                         |
|----------------|--------------|--------------------------------------------------------------------------------|
| `clients`      | `/id`        | `id, name, created_at, onedrive_path, metadata{}`                             |
| `mcp_servers`  | `/id`        | `id, name, endpoint, auth_type, auth_config{}, protocol, enabled, status, last_error, description, builtin` |
| `custom_tools` | `/id`        | `id, name, description, prompt_template, parameters[], created_at, updated_at` |
| `ingest_jobs`  | `/id`        | `id, client_name, mode, status, files_processed, files_total, created_at, updated_at` |

### Per-Client Databases (`client_{id}`)

Created dynamically on client onboarding. Each database is isolated — no cross-client
queries possible.

| Container               | Partition Key     | Key Fields                                                                                    |
|-------------------------|-------------------|-----------------------------------------------------------------------------------------------|
| `memories`              | `/id`             | `id, client_name, stakeholders[], engagements[], pain_points[], strategic_priorities[], key_facts{}, key_stakeholders[], communication_notes[]` |
| `doc_index`             | `/file_path`      | `file_path, content_hash, chunk_count, last_indexed, client_name`                           |
| `analyses`              | `/file_path`      | `id, file_path, stakeholders[], action_items[], risks[], dates[], classification, extracted_at` |
| `engagements`           | `/id`             | `id, name, description, status, phase, start_date, end_date, budget, owner`                 |
| `deliverables`          | `/engagement_id`  | `id, engagement_id, name, description, due_date, status, owner`                             |
| `risks`                 | `/engagement_id`  | `id, engagement_id, description, severity, probability, mitigation, status`                 |
| `status_updates`        | `/engagement_id`  | `id, engagement_id, content, author, created_at`                                            |
| `interactions`          | `/id`             | `id, type(meeting/call/email/workshop), date, attendees[], notes, client_name`              |
| `action_items`          | `/id`             | `id, description, owner, due_date, status, engagement_id, client_name`                     |
| `events`                | `/id`             | `id, type, payload{}, created_at` (event sourcing for timeline)                             |
| `emails`                | `/id`             | `id, client_name, message_id, subject, sender, recipients[], body_preview, body_full, received_at, folder, account, thread_id, has_attachment, attachment_names[], attribution_reason, classification{}, has_draft_reply` |
| `meetings`              | `/id`             | `id, client_name, subject, organizer, attendees[], start_time, end_time, location, is_teams_meeting, teams_join_url, online_meeting_id, global_id, my_response, transcript_summary, action_items_extracted[], classification{}` |
| `draft_replies`         | `/id`             | `id, client_name, email_id, subject, to[], cc[], body, status, created_at, pushed_at, outlook_entry_id, feedback` |
| `communication_config`  | `/id`             | `id, client_name, accounts[], domains[], contacts[], keywords[], scan_sent, auto_draft, scan_interval_minutes, updated_at` |

### Azure AI Search Index (`client-knowledge`)

```
Fields:
  id              (string, key)
  client_name     (string, filterable, facetable)
  file_path       (string, filterable)
  section_title   (string, searchable)
  content         (string, searchable — BM25 target)
  page_number     (int32, filterable)
  chunk_index     (int32)
  embedding       (Collection(Single), 3072 dims, HNSW, cosine similarity)

Index features:
  Semantic configuration: content as primary, section_title as secondary
  Vector profile: HNSW with cosine metric
  Scoring profile: BM25 + vector RRF merge
```

---

## 14. Infrastructure and Deployment

### Azure Resource Map

```
Azure Subscription
  |
  +-- Resource Group: rg-clientagent-{suffix}
        |
        +-- Container Registry (ACR)
        |     Basic SKU
        |     Images: clientagent-backend:{sha}, clientagent-frontend:{sha}
        |
        +-- Cosmos DB Account (serverless, multi-region capable)
        |     Database: clientagent (master)
        |       clients, mcp_servers, custom_tools, ingest_jobs
        |     Database: client_{id} (per client, created at runtime)
        |       all per-client containers
        |
        +-- Azure AI Search (Standard SKU)
        |     Index: client-knowledge
        |     Semantic ranker: enabled
        |
        +-- Azure OpenAI
        |     Deployment: gpt-4o         (chat, max_tokens=4096)
        |     Deployment: text-embedding-3-large (3072 dims)
        |
        +-- Application Insights + Log Analytics workspace
        |     OpenTelemetry SDK -> traces, metrics, custom events
        |
        +-- Container Apps Environment
              |
              +-- backend Container App
              |     Image: clientagent-backend:{sha}
              |     Scale: 1-3 replicas, 1 vCPU / 2Gi RAM
              |     Ingress: internal (fronted by frontend nginx proxy)
              |     Env: from Key Vault references (production)
              |
              +-- frontend Container App
                    Image: clientagent-frontend:{sha}
                    Scale: 1-2 replicas, 0.25 vCPU / 0.5Gi RAM
                    Ingress: external (HTTPS)
                    nginx proxies /api/* and /ws/* to backend
```

### Docker Build Strategy

**Backend** (`backend/Dockerfile`):
```
FROM python:3.11-slim AS base
  COPY requirements.txt .
  RUN pip install --no-cache-dir -r requirements.txt

FROM base AS final
  COPY app/ app/
  CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Frontend** (`frontend/Dockerfile`):
```
FROM node:20-alpine AS build
  COPY package*.json .
  RUN npm ci
  COPY src/ src/
  RUN npm run build          # Vite production build -> dist/

FROM nginx:alpine AS serve
  COPY --from=build /dist /usr/share/nginx/html
  COPY nginx.conf /etc/nginx/conf.d/default.conf
```

`nginx.conf` routes:
- `/api/*` -> `http://backend:8000`
- `/ws/*` -> `http://backend:8000` (WebSocket upgrade)
- `/*` -> `index.html` (SPA fallback)

### docker-compose (local dev)

`docker-compose.yml`: production-like networking, named volumes.
`docker-compose.override.yml`: volume mounts for hot reload, `LOCAL_MODE=true`,
`DISABLE_TELEMETRY=true`, Vite dev server on port 5173.

### CI/CD

```
CI (on PR to main): .github/workflows/ci.yml
  1. ruff (backend lint)
  2. mypy (backend type check)
  3. pytest (backend tests, LOCAL_MODE=true)
  4. eslint + tsc --noEmit (frontend)
  5. docker build (smoke — both services)
  6. terraform validate

CD (on push to main): .github/workflows/cd.yml
  1. azure/login@v2 (OIDC federated, no secrets)
  2. docker build + push to ACR (tagged with git SHA)
  3. terraform apply (requires GitHub Environments approval)
  4. curl /health + /ready on deployed services (smoke test)
```

---

## 15. Design System Tokens

### CSS Custom Properties (Tailwind theme extension)

```css
/* Backgrounds — dark-first palette */
--color-bg-primary:    #0d0d0d   /* App root background */
--color-bg-secondary:  #161616   /* Header, footer, sidebar rails */
--color-bg-panel:      #1a1a1a   /* Cards, input fields, dropdowns */
--color-bg-hover:      #222222   /* Hover state for list items */

/* Text */
--color-text-primary:  #f0f0f0
--color-text-secondary:#a0a0a0
--color-text-muted:    #666666

/* Brand accent */
--color-accent:        #86BC25   /* Deloitte Green — primary CTA, active tab, progress */
--color-accent-bright: #86EB22   /* Pulse animation, active upload indicators */
--color-accent-blue:   #00A3E0   /* MCP badges, source chips, hyperlinks */

/* Status */
--color-status-green:  #22c55e   /* Connected, active engagement */
--color-status-red:    #ef4444   /* Error, high-severity risk */
--color-status-amber:  #f59e0b   /* Warning, medium risk, overdue */

/* Borders */
--color-border-default:#2a2a2a

/* Typography */
--font-ui:   'DM Sans', system-ui, sans-serif
--font-mono: 'JetBrains Mono', 'Fira Code', monospace
```

### Layout Dimensions

| Element                     | Size                                |
|-----------------------------|-------------------------------------|
| Header                      | 48px (`h-12`)                       |
| Footer / status bar         | 32px (`h-8`)                        |
| Left panel default          | 280px, draggable 200–500px          |
| Right panel default         | 320px, draggable 200–500px          |
| Mobile breakpoint           | 768px (collapses to tab nav)        |
| Chat message max-width      | `prose` (65ch)                      |
| Reasoning steps max-height  | 200px (scrollable)                  |

### Component Tokens

```
MCP badge:        text-[9px] px-1.5 py-0.5 bg-accent-blue/10 text-accent-blue rounded
Category label:   text-[10px] uppercase tracking-wider text-text-muted
Code / JSON:      font-mono text-xs whitespace-pre-wrap
Source chip:      text-xs px-2 py-1 bg-bg-hover border border-border-default rounded
```

---

## 16. Extension Points

### 16.1 Adding a Semantic Kernel Plugin

1. Create a class in `backend/app/agent/`:

```python
from semantic_kernel.functions import kernel_function

class MyPlugin:
    @kernel_function(name="do_something", description="...")
    async def do_something(self, query: str) -> str:
        ...
        return result_string
```

2. Import and add to `plugins` dict in `dependencies.py`:

```python
from app.agent.my_plugin import MyPlugin
plugins = {
    ...
    "MyPlugin": MyPlugin(any_dependencies),
}
```

The plugin is automatically registered on the kernel and available to the ReAct loop
on the next startup.

### 16.2 Adding a Built-in MCP Tool

1. Add the tool definition to `TOOL_DEFINITIONS` in `mcp_server/server.py`:

```python
Tool(
    name="my_new_tool",
    description="...",
    inputSchema={
        "type": "object",
        "properties": {"param": {"type": "string"}},
        "required": ["param"],
    },
)
```

2. Add to `TOOL_CATEGORIES`:

```python
"my_new_tool": "Category Name",
```

3. Implement the handler in `mcp_server/tools/my_module.py`:

```python
async def my_new_tool(arguments: dict) -> dict:
    param = arguments.get("param", "")
    ...
    return {"result": ...}
```

4. Add to `_build_dispatch()` in `server.py`:

```python
from app.mcp_server.tools.my_module import my_new_tool
_TOOL_DISPATCH["my_new_tool"] = my_new_tool
```

The tool is immediately available via `/mcp/tools`, `/api/mcp/invoke`, and the SSE
session — no restart required once `_build_dispatch()` re-runs.

### 16.3 Connecting an External MCP Server

**Via UI**: Click the MCP label in the footer -> Add MCP Server -> fill name, endpoint,
auth type. `POST /api/mcp/servers` persists to Cosmos and calls
`MCPManager.add_server()` which connects immediately and registers per-tool functions
on the live kernel.

**Via API**:
```
POST /api/mcp/servers
{
  "name": "My Server",
  "endpoint": "https://my-mcp.example.com/sse",
  "protocol": "sse",
  "auth_type": "bearer",
  "auth_config": {"token": "..."}
}
```

**Test connectivity**: `POST /api/mcp/servers/{id}/test`

### 16.4 Creating a Custom Tool

**Via UI**: Tools tab -> Create Custom Tool -> name, description, prompt template with
`{{$input}}`.

**Via API**:
```
POST /api/tools/custom
{
  "name": "summarize_for_exec",
  "description": "Summarize client info for C-suite",
  "prompt_template": "Summarize for a C-suite executive in under 200 words:\n\n{{$input}}"
}
```

Custom tools are stored in `Cosmos clientagent/custom_tools`, loaded by `ToolManager`,
and registered as `KernelFunctionFromPrompt` on the kernel. Available to the agent
immediately without restart.

### 16.5 Adding a Document Parser

Add a branch in `ingestion/parser.py` `parse_document()`:

```python
elif ext == ".xyz":
    from my_parser import parse_xyz
    sections = parse_xyz(file_path)
    return ParsedDocument(sections=sections)
```

`ParsedDocument` expects `sections: list[Section(title, content, page_number)]`.

### 16.6 LOCAL_MODE Service Stubs

`dependencies.py` exposes three lazy-init functions for test/local runs:

```python
_local_cosmos_manager()    -> LocalCosmosClientManager  (in-memory dict store)
_local_search_service()    -> LocalSearchService        (keyword-only, no embeddings)
_local_embedding_service() -> LocalEmbeddingService     (returns zero vectors)
```

To add a stub for a new service: implement the same async interface as the real service,
return the stub from a `get_X()` factory when `settings.LOCAL_MODE` is true. The agent
and API handlers never call the factory directly — they receive the service via
`get_cosmos_manager()`, `get_search_service()`, etc., so the stub is transparent.
