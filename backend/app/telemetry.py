# backend/app/telemetry.py
import logging
from opentelemetry import trace

logger = logging.getLogger(__name__)
_tracer: trace.Tracer | None = None


def init_telemetry(app=None):
    global _tracer
    from app.config import get_settings
    settings = get_settings()

    if settings.DISABLE_TELEMETRY or not settings.APPLICATIONINSIGHTS_CONNECTION_STRING:
        logger.info("Telemetry disabled")
        _tracer = trace.get_tracer("client-intelligence-agent")
        return

    try:
        from azure.monitor.opentelemetry import configure_azure_monitor
        configure_azure_monitor(
            connection_string=settings.APPLICATIONINSIGHTS_CONNECTION_STRING,
        )
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
