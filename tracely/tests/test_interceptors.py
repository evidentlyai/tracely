from uuid import UUID

import pytest
import opentelemetry
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from tracely import init_tracing
from tracely import trace_event
from tracely.interceptors import Interceptor


class AddAttributeBeforeCallInterceptor(Interceptor):
    def before_call(self, span, context, *args, **kwargs):
        span.set_attribute("custom_attribute", 1)

    def after_call(self, span, context, *args, **kwargs):
        pass

    def on_exception(self, span, context, exception) -> bool:
        pass


@pytest.fixture
def exporter():
    provider = init_tracing(
        exporter_type="console",
        project_id=UUID(int=0),
        export_name="test",
        as_global=False,
        interceptors=[AddAttributeBeforeCallInterceptor()],
    )
    exporter = InMemorySpanExporter()
    if isinstance(provider, opentelemetry.sdk.trace.TracerProvider):
        provider.add_span_processor(SimpleSpanProcessor(exporter))
    return exporter


@trace_event(track_output=True)
def trace_func_with_output():
    return 100


def test_trace_func_with_output(exporter):
    result = trace_func_with_output()

    spans = exporter.get_finished_spans()
    assert len(spans) == 1
    span = spans[0]
    assert span.name == "trace_func_with_output"
    assert span.attributes["custom_attribute"] == 1
    assert span.attributes["result"] == result
