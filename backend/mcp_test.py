import asyncio, json

async def run_e2e():
    from mcp.client.session import ClientSession
    from mcp.client.sse import sse_client

    async with sse_client("http://localhost:8000/mcp/sse", headers={"Authorization": "Bearer local"}) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            print(f"=== MCP Session established. Tools: {len(tools.tools)} ===\n")

            tests = [
                ("search_client_documents",    {"query": "project status update"}),
                ("ingest_documents",           {"client_name": "AcmeCorp", "mode": "incremental", "dry_run": True}),
                ("read_client_memory",         {"client_name": "AcmeCorp"}),
                ("write_client_memory",        {"client_name": "AcmeCorp", "field": "pain_points", "value": "budget pressure"}),
                ("list_indexed_files",         {"client_name": "AcmeCorp"}),
                ("generate_insights",          {"client_name": "AcmeCorp"}),
                ("get_client_communications",  {"client_name": "AcmeCorp", "comm_type": "all", "limit": 5}),
                ("get_engagements",            {"client_name": "AcmeCorp", "include_risks": True}),
                ("get_client_timeline",        {"client_name": "AcmeCorp", "limit": 5}),
                ("get_action_items",           {"client_name": "AcmeCorp", "status": "open"}),
                ("get_client_health",          {"client_name": "AcmeCorp"}),
                ("generate_briefing",          {"client_name": "AcmeCorp"}),
            ]

            for tool_name, args in tests:
                try:
                    result = await session.call_tool(tool_name, args)
                    text = result.content[0].text if result.content else "{}"
                    parsed = json.loads(text)
                    is_error = "error" in parsed
                    status = "FAIL" if is_error else "PASS"
                    preview = json.dumps(parsed)[:120]
                    print(f"{status}  {tool_name}")
                    if is_error:
                        err = parsed["error"]
                        print(f"     ERROR: {err}")
                    else:
                        print(f"     {preview}")
                except Exception as e:
                    print(f"FAIL  {tool_name}")
                    print(f"     EXCEPTION: {type(e).__name__}: {e}")

asyncio.run(run_e2e())
