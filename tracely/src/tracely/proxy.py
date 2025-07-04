import typing
from typing import Dict
from typing import Optional
from typing import Union

import opentelemetry.trace
from tracely._tracer_provider import _data_context

if typing.TYPE_CHECKING:
    from openai.types.responses import ResponseUsage


class _ProxySpanObject:
    def __init__(self, span: Optional[opentelemetry.trace.Span] = None):
        if span is None:
            self.span = opentelemetry.trace.get_current_span()
        else:
            self.span = span

    def set_attribute(self, name, value):
        self.span.set_attribute(name, value)

    def set_result(self, value, parse_output: bool = True):
        set_result(self.span, value, parse_output=parse_output)

    def update_usage(
        self,
        usage: Optional["ResponseUsage"] = None,
        *,
        tokens: Optional[Dict[str, int]] = None,
        costs: Optional[Dict[str, float]] = None,
    ):
        if usage is not None:
            if tokens is not None or costs is not None:
                raise ValueError("Cannot specify both usage and tokens+costs, use only one instead")
            self._update_usage_openai(usage)
        else:
            if tokens is None:
                raise ValueError("Must specify either tokens or usage")
            self._update_usage(tokens=tokens, costs=costs)

    def _update_usage(
        self,
        *,
        tokens: Dict[str, int],
        costs: Optional[Dict[str, float]] = None,
    ):
        for k, v in tokens.items():
            self.set_attribute(f"tokens.{k}", v)
        if costs:
            for k, cost_value in costs.items():
                self.set_attribute(f"cost.{k}", cost_value)
        usage_details = _data_context.get_model_usage_details("default")
        if usage_details:
            for k, v in tokens.items():
                cost = usage_details.cost_per_token.get(k)
                if cost:
                    self.set_attribute(f"cost.{k}", cost * v)

    def _update_usage_openai(self, usage: "ResponseUsage"):
        self._update_usage(
            tokens={
                "total_input": usage.input_tokens,
                "input": usage.input_tokens - usage.input_tokens_details.cached_tokens,
                "cached_input": usage.input_tokens_details.cached_tokens,
                "output": usage.output_tokens,
            },
        )


def get_current_span():
    return _ProxySpanObject()


def set_result(span, result, parse_output: bool):
    if parse_output and isinstance(result, dict):
        value: Union[str, int, float]
        for k, v in result.items():
            if isinstance(v, (int, float)):
                value = v
            else:
                value = str(v)
            span.set_attribute(f"result.{k}", value)
    elif parse_output and isinstance(result, (tuple, list)):
        for idx, item in enumerate(result):
            span.set_attribute(f"result.{idx}", str(item))
    elif isinstance(result, (int, float)):
        span.set_attribute("result", result)
    else:
        span.set_attribute("result", str(result))
