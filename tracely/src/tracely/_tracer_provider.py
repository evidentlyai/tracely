import urllib.parse
import uuid
from typing import Optional

import requests
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SpanExporter

from ._env import (
    _TRACE_COLLECTOR_ADDRESS,
    _TRACE_COLLECTOR_API_KEY,
    _TRACE_COLLECTOR_EXPORT_NAME,
    _TRACE_COLLECTOR_TEAM_ID,
    _TRACE_COLLECTOR_TYPE,
)
from .evidently_cloud_client import EvidentlyCloudClient

_tracer: Optional[trace.Tracer] = None


def _create_tracer_provider(
    address: Optional[str] = None,
    exporter_type: Optional[str] = None,
    api_key: Optional[str] = None,
    team_id: Optional[str] = None,
    export_name: Optional[str] = None,
) -> trace.TracerProvider:
    """
    Creates Evidently telemetry tracer provider which would be used for sending traces.
    Args:
        address: address of collector service
        exporter_type: type of exporter to use "grpc" or "http"
        api_key: authorization api key for Evidently tracing
        team_id: id of team in Evidently Cloud
        export_name: string name of exported data, all data with same id would be grouped into single dataset
    """
    global _tracer  # noqa: PLW0603

    _address = address or _TRACE_COLLECTOR_ADDRESS
    if len(_address) == 0:
        raise ValueError(
            "You need to provide valid trace collector address with "
            "argument address or EVIDENTLY_TRACE_COLLECTOR env variable"
        )
    _exporter_type = exporter_type or _TRACE_COLLECTOR_TYPE
    if _exporter_type != "http":
        raise ValueError("Only 'http' exporter_type is supported")
    _api_key = api_key or _TRACE_COLLECTOR_API_KEY
    _export_name = export_name or _TRACE_COLLECTOR_EXPORT_NAME
    if len(_export_name) == 0:
        raise ValueError(
            "You need to provide export name with export_name argument"
            " or EVIDENTLY_TRACE_COLLECTOR_EXPORT_NAME env variable"
        )
    _team_id = team_id or _TRACE_COLLECTOR_TEAM_ID
    try:
        uuid.UUID(_team_id)
    except ValueError:
        raise ValueError(
            "You need provide valid team ID with team_id argument" "or EVIDENTLY_TRACE_COLLECTOR_TEAM_ID env variable"
        )

    cloud = EvidentlyCloudClient(_address, _api_key)
    datasets_response: requests.Response = cloud.request("/api/datasets", "GET")
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
            query_params={"team_id": _team_id},
            body={"name": _export_name},
        )

        _export_id = resp.json()["dataset_id"]

    tracer_provider = TracerProvider(
        resource=Resource.create(
            {
                "evidently.export_id": _export_id,
                "evidently.team_id": _team_id,
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
    else:
        raise ValueError("Unexpected value of exporter type")
    tracer_provider.add_span_processor(BatchSpanProcessor(exporter))
    _tracer = tracer_provider.get_tracer("evidently")
    return tracer_provider


def init_tracing(
    address: Optional[str] = None,
    exporter_type: Optional[str] = None,
    api_key: Optional[str] = None,
    team_id: Optional[str] = None,
    export_name: Optional[str] = None,
    *,
    as_global: bool = True,
) -> trace.TracerProvider:
    """
    Initialize Evidently tracing
    Args:
        address: address of collector service
        exporter_type: type of exporter to use "grpc" or "http"
        api_key: authorization api key for Evidently tracing
        team_id: id of team in Evidently Cloud
        export_name: string name of exported data, all data with same id would be grouped into single dataset
        as_global: indicated when to register provider globally for opentelemetry of use local one
                   Can be useful when you don't want to mix already existing OpenTelemetry tracing with Evidently one,
                   but may require additional configuration
    """
    global _tracer  # noqa: PLW0603
    provider = _create_tracer_provider(address, exporter_type, api_key, team_id, export_name)

    if as_global:
        trace.set_tracer_provider(provider)
        _tracer = trace.get_tracer("evidently")
    else:
        _tracer = provider.get_tracer("evidently")
    return provider


def get_tracer() -> trace.Tracer:
    if _tracer is None:
        raise ValueError("TracerProvider not initialized, use init_tracer()")
    return _tracer
