import urllib.parse
import uuid
from typing import Dict
from typing import List
from typing import Optional
from typing import Union

import opentelemetry.trace
import requests
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SpanExporter, SimpleSpanProcessor
from opentelemetry.trace import NonRecordingSpan
from opentelemetry.trace import SpanContext
from opentelemetry.trace import TraceFlags

from ._context import UsageDetails
from ._context import _data_context
from ._context import set_tracer
from ._env import (
    _EVIDENTLY_API_KEY,
    _TRACE_COLLECTOR_ADDRESS,
    _TRACE_COLLECTOR_API_KEY,
    _TRACE_COLLECTOR_EXPORT_NAME,
    _TRACE_COLLECTOR_TYPE,
    _TRACE_COLLECTOR_PROJECT_ID,
)
from .evidently_cloud_client import EvidentlyCloudClient
from .interceptors import Interceptor


def _create_tracer_provider(
    address: Optional[str] = None,
    exporter_type: Optional[str] = None,
    processor_type: str = "batch",
    api_key: Optional[str] = None,
    project_id: Optional[Union[str, uuid.UUID]] = None,
    export_name: Optional[str] = None,
    default_usage_details: Optional[UsageDetails] = None,
    usage_details_by_model_id: Optional[Dict[str, UsageDetails]] = None,
    interceptors: Optional[List[Interceptor]] = None,
) -> trace.TracerProvider:
    """
    Creates Evidently telemetry tracer provider which would be used for sending traces.
    Args:
        address: address of collector service
        exporter_type: type of exporter to use "grpc" or "http"
        api_key: authorization api key for Evidently tracing
        project_id: id of project in Evidently Cloud
        export_name: string name of exported data, all data with same id would be grouped into single dataset
    """

    _address = address or _TRACE_COLLECTOR_ADDRESS
    if len(_address) == 0:
        raise ValueError(
            "You need to provide valid trace collector address with "
            "argument address or EVIDENTLY_TRACE_COLLECTOR env variable"
        )
    _exporter_type = exporter_type or _TRACE_COLLECTOR_TYPE
    _api_key = api_key or _TRACE_COLLECTOR_API_KEY or _EVIDENTLY_API_KEY
    _export_name = export_name or _TRACE_COLLECTOR_EXPORT_NAME
    if len(_export_name) == 0:
        raise ValueError(
            "You need to provide export name with export_name argument"
            " or EVIDENTLY_TRACE_COLLECTOR_EXPORT_NAME env variable"
        )
    _project_id = project_id or _TRACE_COLLECTOR_PROJECT_ID
    try:
        if project_id is None and _TRACE_COLLECTOR_PROJECT_ID != "":
            _project_id = str(uuid.UUID(_TRACE_COLLECTOR_PROJECT_ID))
        elif isinstance(project_id, uuid.UUID):
            _project_id = str(project_id)
        elif isinstance(project_id, str):
            _project_id = str(uuid.UUID(_project_id)) if isinstance(_project_id, str) else str(_project_id)
        else:
            raise ValueError()
    except ValueError:
        raise ValueError(
            "You need provide valid project ID with project_id argument"
            "or EVIDENTLY_TRACE_COLLECTOR_PROJECT_ID env variable"
        )

    if _exporter_type not in ("console", "inmemory"):
        cloud = EvidentlyCloudClient(_address, _api_key)
        datasets_response: requests.Response = cloud.request(
            "/api/datasets",
            "GET",
            query_params={"project_id": _project_id, "source_type": ["tracing"]},
        )
        datasets = datasets_response.json()["datasets"]
        _export_id = None
        for dataset in datasets:
            if dataset["name"] == _export_name:
                _export_id = dataset["id"]
                break
        if _export_id is None:
            resp: requests.Response = cloud.request(
                "/api/datasets/tracing",
                "POST",
                query_params={"project_id": _project_id},
                body={"name": _export_name},
            )

            _export_id = resp.json()["dataset_id"]
            _data_context.export_id = uuid.UUID(_export_id)
    else:
        _data_context.export_id = "<not_set>"
    _data_context.project_id = uuid.UUID(_project_id)
    _data_context.default_usage_details = default_usage_details
    _data_context.usage_details_by_model_id = usage_details_by_model_id
    _data_context.interceptors = interceptors or []

    tracer_provider = TracerProvider(
        resource=Resource.create(
            {
                "evidently.export_id": str(_data_context.export_id),
                "evidently.project_id": str(_data_context.export_id),
            }
        )
    )

    exporter: SpanExporter
    if _exporter_type == "grpc":
        from opentelemetry.exporter.otlp.proto.grpc import trace_exporter as grpc_exporter

        exporter = grpc_exporter.OTLPSpanExporter(
            _address,
            headers=[] if _api_key is None else [("authorization", _api_key)],
        )
    elif _exporter_type == "http":
        from opentelemetry.exporter.otlp.proto.http import trace_exporter as http_exporter

        exporter = http_exporter.OTLPSpanExporter(
            urllib.parse.urljoin(_address, "/api/v1/traces"),
            session=cloud.session(),
        )
    elif _exporter_type == "console":
        from opentelemetry.sdk.trace.export import ConsoleSpanExporter

        exporter = ConsoleSpanExporter()
    elif _exporter_type == "memory":
        from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

        exporter = InMemorySpanExporter()
    else:
        raise ValueError("Unexpected value of exporter type")
    if processor_type == "batch":
        tracer_provider.add_span_processor(BatchSpanProcessor(exporter))
    elif processor_type == "simple":
        tracer_provider.add_span_processor(SimpleSpanProcessor(exporter))
    else:
        raise ValueError(f"Unexpected processor type: {processor_type}. Expected values: batch or simple")
    set_tracer(tracer_provider.get_tracer("evidently"))
    return tracer_provider


def init_tracing(
    address: Optional[str] = None,
    exporter_type: Optional[str] = None,
    api_key: Optional[str] = None,
    project_id: Optional[Union[str, uuid.UUID]] = None,
    export_name: Optional[str] = None,
    *,
    as_global: bool = True,
    processor_type: str = "batch",
    default_usage_details: Optional[UsageDetails] = None,
    usage_details_by_model_id: Optional[Dict[str, UsageDetails]] = None,
    interceptors: Optional[List[Interceptor]] = None,
) -> trace.TracerProvider:
    """
    Initialize Evidently tracing
    Args:
        address: address of collector service
        exporter_type: type of exporter to use "grpc" or "http"
        api_key: authorization api key for Evidently tracing
        project_id: id of project in Evidently Cloud
        export_name: string name of exported data, all data with same id would be grouped into single dataset
        as_global: indicated when to register provider globally for opentelemetry of use local one
                   Can be useful when you don't want to mix already existing OpenTelemetry tracing with Evidently one,
                   but may require additional configuration
        processor_type: (default: batch) type of processor to use:
                        'batch' - upload traces in batches once in several seconds in separate thread
                        'simple' - upload traces synchronously as it is reported, can cause performance issues.
        default_usage_details: usage data for tokens
        usage_details_by_model_id: usage data for tokens by model id (if provided)
        interceptors: list of interceptors to use

    """
    provider = _create_tracer_provider(
        address,
        exporter_type,
        processor_type,
        api_key,
        project_id,
        export_name,
        default_usage_details,
        usage_details_by_model_id,
        interceptors,
    )

    if as_global:
        trace.set_tracer_provider(provider)
        set_tracer(trace.get_tracer("evidently"))
    else:
        set_tracer(provider.get_tracer("evidently"))
    return provider


def create_context(trace_id: int, parent_span_id: Optional[int]):
    if parent_span_id is None:
        generator = opentelemetry.sdk.trace.RandomIdGenerator()
        parent_span_id = generator.generate_span_id()
    span_context = SpanContext(trace_id=trace_id, span_id=parent_span_id, is_remote=True, trace_flags=TraceFlags(0x01))
    context = opentelemetry.trace.set_span_in_context(NonRecordingSpan(span_context))
    return context
