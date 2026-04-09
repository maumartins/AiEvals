"""Configuração básica de OpenTelemetry local."""

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

from app.core.config import settings

_initialized = False


def setup_tracing() -> None:
    global _initialized
    if _initialized:
        return

    resource = Resource.create({"service.name": "aievals", "service.version": "0.1.0"})
    provider = TracerProvider(resource=resource)

    if settings.otel_enabled:
        # Exporta para console (pode ser trocado por OTLP em produção)
        exporter = ConsoleSpanExporter()
        provider.add_span_processor(BatchSpanProcessor(exporter))

    trace.set_tracer_provider(provider)
    _initialized = True


def get_tracer(name: str) -> trace.Tracer:
    setup_tracing()
    return trace.get_tracer(name)
