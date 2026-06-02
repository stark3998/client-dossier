# backend/app/telemetry.py
import logging
from opentelemetry import trace

logger = logging.getLogger(__name__)
_tracer: trace.Tracer | None = None


def _is_valid_connection_string(cs: str) -> bool:
    """Check that the connection string contains a UUID instrumentation key."""
    import re, uuid as _uuid
    m = re.search(r'InstrumentationKey=([^;]+)', cs, re.IGNORECASE)
    if not m:
        return False
    try:
        _uuid.UUID(m.group(1).strip())
        return True
    except ValueError:
        return False


def init_telemetry(app=None):
    global _tracer
    from app.config import get_settings
    settings = get_settings()

    cs = settings.APPLICATIONINSIGHTS_CONNECTION_STRING
    if settings.DISABLE_TELEMETRY or not cs or not _is_valid_connection_string(cs):
        if cs and not settings.DISABLE_TELEMETRY:
            logger.debug("Telemetry skipped: APPLICATIONINSIGHTS_CONNECTION_STRING is not a valid connection string")
        else:
            logger.info("Telemetry disabled")
        _tracer = trace.get_tracer("client-intelligence-agent")
        return

    try:
        from azure.monitor.opentelemetry import configure_azure_monitor
        configure_azure_monitor(connection_string=cs)
        logger.info("Azure Monitor telemetry configured")
    except Exception as e:
        logger.warning("Failed to configure Azure Monitor: %s", e)

    _tracer = trace.get_tracer("client-intelligence-agent")

    if app is not None:
        try:
            from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
            FastAPIInstrumentor.instrument_app(app)
        except Exception as e:
            logger.warning("Failed to instrument FastAPI: %s", e)

        try:
            from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
            HTTPXClientInstrumentor().instrument()
        except Exception as e:
            logger.warning("Failed to instrument httpx: %s", e)


def get_tracer() -> trace.Tracer:
    if _tracer is None:
        return trace.get_tracer("client-intelligence-agent")
    return _tracer


def track_event(name: str, attributes: dict | None = None):
    tracer = get_tracer()
    with tracer.start_as_current_span(name) as span:
        if attributes:
            for k, v in attributes.items():
                span.set_attribute(k, str(v))
