from contextlib import contextmanager
from typing import Any, Optional

import opentelemetry.sdk.trace

from . import _tracer_provider
from .decorators import set_result


class _SpanObject:
    def __init__(self):
        self.attributes = {}
        self.result: Optional[Any] = None

    def set_attribute(self, name, value):
        """
        set attribute for the span
        Args:
            name: attribute name
            value: attribute value
        """
        self.attributes[name] = value

    def set_result(self, result: Any):
        """
        set result for the span. Span can have only one result
        Args:
            result: object to set as a result for the span.
        """
        self.result = result


@contextmanager
def create_trace_event(name: str, parse_output: bool = True, **params):
    """
    Create a span with given name.

    Args:
        name: name of the span
        parse_output: do parse result if set in span
        **params: attributes to set for span

    Returns:
        span object to work with
    """
    _tracer = _tracer_provider.get_tracer()
    with _tracer.start_as_current_span(f"{name}") as span:
        obj = _SpanObject()
        try:
            yield obj
        finally:
            for attr, value in params.items():
                span.set_attribute(attr, value)
            for attr, value in obj.attributes.items():
                span.set_attribute(attr, value)
            if obj.result is not None:
                set_result(span, obj.result, parse_output)


@contextmanager
def bind_to_trace(trace_id: int, parent_span_id: Optional[int] = None):
    context = _tracer_provider.create_context(trace_id, parent_span_id)
    token = opentelemetry.sdk.trace.context_api.attach(context)
    try:
        yield
    finally:
        opentelemetry.sdk.trace.context_api.detach(token)
