from functools import wraps
from uuid import UUID

import pytest
import opentelemetry
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from tracely import init_tracing
from tracely import trace_event
from tracely import get_current_span
from tracely.interceptors import Interceptor


class MyException(Exception):
    message = "Exception message"

    def __init__(self, value):
        self.message = value


class AddAttributeBeforeCallInterceptor(Interceptor):
    def before_call(self, span, context, *args, **kwargs):
        pass

    def after_call(self, span, context, *args, **kwargs):
        value = span.get_context_value("deco")
        if value is not None:
            span.set_attribute("deco", value)
            span.set_attribute("status", "passed")

    def on_exception(self, span, context, exception) -> bool:
        value = span.get_context_value("deco")
        if value is not None:
            if isinstance(exception, MyException):
                span.set_attribute("deco", value)
                span.set_attribute("status", "failed")
                span.set_attribute("error", exception.message)
                return True
        return False


@pytest.fixture
def exporter():
    provider = init_tracing(
        exporter_type="console",
        processor_type="simple",
        project_id=UUID(int=0),
        export_name="test",
        as_global=False,
        interceptors=[AddAttributeBeforeCallInterceptor()],
    )
    exporter = InMemorySpanExporter()
    if isinstance(provider, opentelemetry.sdk.trace.TracerProvider):
        provider.add_span_processor(SimpleSpanProcessor(exporter))
    return exporter


def stub_deco(fail, message):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            span = get_current_span()
            if span:
                span.set_context_value("deco", "test_deco")
            if fail:
                raise MyException(message)
            return func(*args, **kwargs)
        return wrapper
    return decorator


@trace_event(track_output=True)
@stub_deco(False, "message")
def trace_func_with_output():
    return 100


@trace_event(track_output=True)
@stub_deco(True, "message")
def trace_func_with_output_failed_deco():
    return 100


def test_trace_func_with_output(exporter):
    result = trace_func_with_output()

    spans = exporter.get_finished_spans()
    assert len(spans) == 1
    span = spans[0]
    assert span.name == "trace_func_with_output"
    assert span.attributes["deco"] == "test_deco"
    assert span.attributes["status"] == "passed"
    assert span.attributes["result"] == result


def test_trace_func_with_output_failed_deco(exporter):
    with pytest.raises(MyException):
        result = trace_func_with_output_failed_deco()

    spans = exporter.get_finished_spans()
    assert len(spans) == 1
    span = spans[0]
    assert span.name == "trace_func_with_output_failed_deco"
    assert span.attributes["deco"] == "test_deco"
    assert span.attributes["status"] == "failed"
    assert span.attributes["error"] == "message"
