import dataclasses
import typing
import uuid
from typing import Dict
from typing import List
from typing import Optional
from typing import Union

import opentelemetry
from opentelemetry import trace
from opentelemetry.context import Context
from opentelemetry.trace import NonRecordingSpan
from opentelemetry.trace import SpanContext
from opentelemetry.trace import TraceFlags

if typing.TYPE_CHECKING:
    from .interceptors import Interceptor


@dataclasses.dataclass
class UsageDetails:
    cost_per_token: Dict[str, float]


class DataContext:
    export_id: Union[str, uuid.UUID]
    project_id: Union[str, uuid.UUID]
    default_usage_details: Optional[UsageDetails]
    usage_details_by_model_id: Optional[Dict[str, UsageDetails]]
    interceptors: List["Interceptor"]

    def __init__(
        self,
        export_id: str,
        project_id: str,
        default_usage_details: Optional[UsageDetails] = None,
        usage_details_by_model_id: Optional[Dict[str, UsageDetails]] = None,
        interceptors: Optional[List["Interceptor"]] = None,
    ):
        self.export_id = export_id
        self.project_id = project_id
        self.default_usage_details = default_usage_details
        self.usage_details_by_model_id = usage_details_by_model_id
        self.interceptors = interceptors or []

    def get_model_usage_details(self, model_id: str) -> Optional[UsageDetails]:
        if self.usage_details_by_model_id is None:
            return self.default_usage_details
        return self.usage_details_by_model_id.get(model_id, self.default_usage_details)


_tracer: Optional[trace.Tracer] = None
_context: Optional[Context] = None
_data_context: DataContext = DataContext("<not_set>", "<not_set>")


def set_tracer(new_tracer: trace.Tracer) -> None:
    global _tracer
    _tracer = new_tracer


def get_tracer() -> Optional[trace.Tracer]:
    return _tracer


def get_info():
    return {
        "export_id": _data_context.export_id,
        "project_id": _data_context.project_id,
    }


def get_interceptors() -> List["Interceptor"]:
    return _data_context.interceptors


def create_context(trace_id: int, parent_span_id: Optional[int]):
    if parent_span_id is None:
        generator = opentelemetry.sdk.trace.RandomIdGenerator()
        parent_span_id = generator.generate_span_id()
    span_context = SpanContext(trace_id=trace_id, span_id=parent_span_id, is_remote=True, trace_flags=TraceFlags(0x01))
    context = opentelemetry.trace.set_span_in_context(NonRecordingSpan(span_context))
    return context
