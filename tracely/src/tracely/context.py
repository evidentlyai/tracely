from contextlib import contextmanager
from typing import Optional
from typing import Generator

import opentelemetry.sdk.trace

from ._context import get_tracer
from ._context import create_context
from .proxy import SpanObject


@contextmanager
def create_trace_event(name: str, **params) -> Generator[SpanObject, None, None]:
    """
    Create a span with given name.

    Args:
        name: name of the span
        **params: attributes to set for span

    Returns:
        span object to work with
    """
    _tracer = get_tracer()
    with _tracer.start_as_current_span(f"{name}") as span:
        obj = SpanObject(span)
        try:
            yield obj
        finally:
            for attr, value in params.items():
                span.set_attribute(attr, value)


@contextmanager
def bind_to_trace(trace_id: int, parent_span_id: Optional[int] = None):
    context = create_context(trace_id, parent_span_id)
    token = opentelemetry.sdk.trace.context_api.attach(context)
    try:
        yield
    finally:
        opentelemetry.sdk.trace.context_api.detach(token)
