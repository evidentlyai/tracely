from uuid import UUID

import opentelemetry.sdk.trace
import pytest
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

import tracely
from tracely import init_tracing
from tracely import trace_event
from tracely import UsageDetails


@trace_event(track_output=True)
def trace_func_with_output():
    return 100


@trace_event(track_output=True)
async def async_trace_func_with_output():
    return 100


@trace_event(track_output=True, parse_output=True)
def trace_func_with_output_struct():
    return {
        "f1": "r1",
        "f2": 100,
    }


@trace_event()
def trace_func_with_inner_trace():
    return trace_func_with_output()


@trace_event(track_output=True, parse_output=True)
def trace_func_with_tokens():
    span = tracely.get_current_span()
    span.update_usage(
        tokens={
            "input": 100,
            "output": 200,
        }
    )
    return {
        "f1": "r1",
        "f2": "r2",
    }


@pytest.fixture
def exporter():
    provider = init_tracing(
        exporter_type="console",
        project_id=UUID(int=0),
        export_name="test",
        as_global=False,
        default_usage_details=UsageDetails(cost_per_token={"input": 0.001, "output": 0.005}),
    )
    exporter = InMemorySpanExporter()
    if isinstance(provider, opentelemetry.sdk.trace.TracerProvider):
        provider.add_span_processor(SimpleSpanProcessor(exporter))
    return exporter


@pytest.fixture
def exporter_without_costs():
    provider = init_tracing(
        exporter_type="console",
        project_id=UUID(int=0),
        export_name="test",
        as_global=False,
    )
    exporter = InMemorySpanExporter()
    if isinstance(provider, opentelemetry.sdk.trace.TracerProvider):
        provider.add_span_processor(SimpleSpanProcessor(exporter))
    return exporter


def test_context(exporter):
    with tracely.create_trace_event("test_name") as span:
        span.set_result(42)

    spans = exporter.get_finished_spans()
    assert len(spans) == 1
    span = spans[0]
    assert span.name == "test_name"
    assert span.attributes["result"] == 42


def test_context_with_usage(exporter):
    with tracely.create_trace_event("test_name") as span:
        span.update_usage(tokens={"input": 100, "output": 200})
        span.set_result(42)

    spans = exporter.get_finished_spans()
    assert len(spans) == 1
    span = spans[0]
    assert span.name == "test_name"
    assert span.attributes["result"] == 42
    assert span.attributes["tokens.input"] == 100
    assert span.attributes["tokens.output"] == 200
    assert span.attributes["cost.input"] == 0.1
    assert span.attributes["cost.output"] == 1.0


def test_context_with_usage_without_cost(exporter_without_costs):
    with tracely.create_trace_event("test_name") as span:
        span.update_usage(tokens={"input": 100, "output": 200})
        span.set_result(42)

    spans = exporter_without_costs.get_finished_spans()
    assert len(spans) == 1
    span = spans[0]
    assert span.name == "test_name"
    assert span.attributes["result"] == 42
    assert span.attributes["tokens.input"] == 100
    assert span.attributes["tokens.output"] == 200
    assert "cost.input" not in span.attributes
    assert "cost.input" not in span.attributes


def test_context_with_params(exporter):
    with tracely.create_trace_event("test_name", p1=43) as span:
        span.set_result(42)

    spans = exporter.get_finished_spans()
    assert len(spans) == 1
    span = spans[0]
    assert span.name == "test_name"
    assert span.attributes["p1"] == 43
    assert span.attributes["result"] == 42


def test_trace_func_with_output(exporter):
    result = trace_func_with_output()

    spans = exporter.get_finished_spans()
    assert len(spans) == 1
    span = spans[0]
    assert span.name == "trace_func_with_output"
    assert span.attributes["result"] == result


@pytest.mark.asyncio
async def test_async_trace_func_with_output(exporter):
    result = await async_trace_func_with_output()

    spans = exporter.get_finished_spans()
    assert len(spans) == 1
    span = spans[0]
    assert span.name == "async_trace_func_with_output"
    assert span.attributes["result"] == result


def test_trace_func_with_output_struct(exporter):
    trace_func_with_output_struct()

    spans = exporter.get_finished_spans()
    assert len(spans) == 1
    span = spans[0]
    assert span.name == "trace_func_with_output_struct"
    assert span.attributes["result.f1"] == "r1"
    assert span.attributes["result.f2"] == 100


def test_trace_func_with_tokens(exporter):
    trace_func_with_tokens()

    spans = exporter.get_finished_spans()
    assert len(spans) == 1
    span = spans[0]
    assert span.name == "trace_func_with_tokens"
    assert span.attributes["tokens.input"] == 100
    assert span.attributes["tokens.output"] == 200
    assert span.attributes["cost.input"] == 0.1
    assert span.attributes["cost.output"] == 1.0


def test_trace_func_with_inner_trace(exporter):
    trace_func_with_inner_trace()

    spans = exporter.get_finished_spans()
    assert len(spans) == 2
    assert spans[0].name == "trace_func_with_output"
    assert spans[1].name == "trace_func_with_inner_trace"
