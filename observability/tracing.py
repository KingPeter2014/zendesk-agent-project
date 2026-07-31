"""OpenTelemetry tracing setup — sends spans to Jaeger via OTLP."""

from __future__ import annotations

import functools
import os
from typing import Any, Callable

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

_tracer: trace.Tracer | None = None


def init_tracing(
    service_name: str = "zendesk-agent",
    otlp_endpoint: str | None = None,
) -> trace.Tracer:
    global _tracer
    if _tracer is not None:
        return _tracer

    endpoint = otlp_endpoint or os.getenv("OTLP_ENDPOINT", "http://localhost:4318/v1/traces")
    resource = Resource(attributes={"service.name": service_name})
    provider = TracerProvider(resource=resource)

    try:
        exporter = OTLPSpanExporter(endpoint=endpoint)
        provider.add_span_processor(BatchSpanProcessor(exporter))
    except Exception:
        # Fall back to console exporter if Jaeger is not running
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

    trace.set_tracer_provider(provider)
    _tracer = trace.get_tracer(service_name)
    return _tracer


def get_tracer() -> trace.Tracer:
    global _tracer
    if _tracer is None:
        return init_tracing()
    return _tracer


def traced(span_name: str | None = None) -> Callable:
    """Decorator that wraps a function in an OpenTelemetry span."""
    def decorator(fn: Callable) -> Callable:
        name = span_name or fn.__qualname__

        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            tracer = get_tracer()
            with tracer.start_as_current_span(name) as span:
                try:
                    result = fn(*args, **kwargs)
                    span.set_status(trace.StatusCode.OK)
                    return result
                except Exception as exc:
                    span.record_exception(exc)
                    span.set_status(trace.StatusCode.ERROR, str(exc))
                    raise

        return wrapper
    return decorator
