import json
import logging
import os
import sys
import time
import traceback
import uuid
from logging.handlers import RotatingFileHandler
from typing import Any

_file_handler_initialized = False
_file_logger = logging.getLogger("mcp_server_file")


def init_mcp_logger() -> None:
    """Initialize the rotating file log sink. Called once at app startup."""
    global _file_handler_initialized
    if _file_handler_initialized:
        return

    log_dir = os.getenv("MCP_LOG_DIR", "./logs/mcp")
    os.makedirs(log_dir, exist_ok=True)

    handler = RotatingFileHandler(
        filename=os.path.join(log_dir, "mcp-server.log"),
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter("%(message)s"))
    _file_logger.addHandler(handler)
    _file_logger.setLevel(logging.DEBUG)
    _file_logger.propagate = False
    _file_handler_initialized = True


class MCPLogger:
    def log_event(
        self,
        event: str,
        *,
        tool: str | None = None,
        trace_id: str | None = None,
        caller: dict | None = None,
        input_data: dict | None = None,
        duration_ms: float | None = None,
        error: Exception | None = None,
        level: str = "INFO",
    ) -> None:
        if error is not None:
            level = "ERROR"

        record: dict[str, Any] = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "level": level,
            "event": event,
        }
        if tool:
            record["tool"] = tool
        if trace_id:
            record["trace_id"] = trace_id
        if caller:
            record["agent"] = {
                "id": caller.get("oid", "unknown"),
                "upn": caller.get("upn", "unknown"),
            }
        if input_data is not None:
            record["request"] = {
                "input": input_data,
                "input_size_bytes": len(json.dumps(input_data, default=str)),
            }
        if duration_ms is not None:
            record["performance"] = {"duration_ms": round(duration_ms, 2)}
        if error is not None:
            record["error"] = {
                "type": type(error).__name__,
                "message": str(error),
                "stack_trace": traceback.format_exc(),
            }

        line = json.dumps(record, default=str)

        # Sink 1: JSON stdout
        print(line, flush=True)

        # Sink 2: Rotating file
        if _file_handler_initialized:
            _file_logger.info(line)

        # Sink 3: App Insights via existing telemetry
        try:
            from app.telemetry import track_event
            attrs: dict[str, str] = {}
            for k in ("event", "tool", "trace_id", "level"):
                if record.get(k):
                    attrs[f"mcp.{k}"] = str(record[k])
            if duration_ms is not None:
                attrs["mcp.duration_ms"] = str(round(duration_ms, 2))
            if error is not None:
                attrs["mcp.error_type"] = type(error).__name__
                attrs["mcp.error_message"] = str(error)[:500]
            span_name = f"mcp.tool.{tool}" if tool else "mcp.server"
            track_event(span_name, attrs)
        except Exception:
            pass


mcp_logger = MCPLogger()
