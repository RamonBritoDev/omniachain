"""OmniaChain — Tracer: trace completo de cada execução."""

from __future__ import annotations

import time
import uuid
from typing import Any, Optional

from pydantic import BaseModel, Field


class Span(BaseModel):
    """Um span individual dentro de um trace."""
    span_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    start_time: float = 0.0
    end_time: float = 0.0
    duration_ms: float = 0.0
    status: str = "ok"
    attributes: dict[str, Any] = Field(default_factory=dict)
    events: list[dict[str, Any]] = Field(default_factory=list)
    parent_id: Optional[str] = None


class Trace(BaseModel):
    """Trace completo de uma execução."""
    trace_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:16])
    spans: list[Span] = Field(default_factory=list)
    start_time: float = Field(default_factory=time.time)
    metadata: dict[str, Any] = Field(default_factory=dict)


class Tracer:
    """Sistema de tracing para execuções do OmniaChain.

    Exemplo::

        tracer = Tracer()
        with tracer.span("llm_call") as span:
            result = await provider.complete(messages)
            span.attributes["model"] = result.model
            span.attributes["tokens"] = result.usage.total_tokens
    """

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled
        self._traces: list[Trace] = []
        self._current_trace: Optional[Trace] = None

    def start_trace(self, metadata: Optional[dict[str, Any]] = None) -> Trace:
        """Inicia um novo trace."""
        trace = Trace(metadata=metadata or {})
        self._current_trace = trace
        self._traces.append(trace)
        return trace

    def span(self, name: str, parent_id: Optional[str] = None) -> SpanContext:
        """Cria um span context manager."""
        return SpanContext(self, name, parent_id)

    def add_span(self, span: Span) -> None:
        """Adiciona um span ao trace atual."""
        if self._current_trace:
            self._current_trace.spans.append(span)

    def get_traces(self, limit: int = 100) -> list[Trace]:
        """Retorna os últimos traces."""
        return self._traces[-limit:]

    def get_current_trace(self) -> Optional[Trace]:
        return self._current_trace

    def export_json(self) -> list[dict[str, Any]]:
        """Exporta traces em formato JSON."""
        return [t.model_dump() for t in self._traces]


class SpanContext:
    """Context manager para spans."""

    def __init__(self, tracer: Tracer, name: str, parent_id: Optional[str] = None) -> None:
        self.tracer = tracer
        self.span = Span(name=name, parent_id=parent_id)

    def __enter__(self) -> Span:
        self.span.start_time = time.time()
        return self.span

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.span.end_time = time.time()
        self.span.duration_ms = (self.span.end_time - self.span.start_time) * 1000
        if exc_type:
            self.span.status = "error"
            self.span.events.append({"type": "error", "error": str(exc_val)})
        self.tracer.add_span(self.span)
