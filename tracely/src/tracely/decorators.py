from functools import wraps
from inspect import BoundArguments, iscoroutinefunction, Parameter, Signature
from typing import Any, Callable, List, Optional

from opentelemetry.trace import Span
from opentelemetry.trace import StatusCode

from . import _tracer_provider


def _fill_span_from_signature(
    track_args: Optional[List[str]],
    ignore_args: Optional[List[str]],
    sign: Signature,
    bind: BoundArguments,
    span: Span,
):
    final_args = track_args
    if track_args is None:
        final_args = list(sign.parameters.keys())
    if ignore_args is not None:
        final_args = [item for item in final_args if item not in ignore_args]
    for tracked in final_args:
        if tracked in bind.arguments:
            value = bind.arguments[tracked]
        elif (
            tracked in sign.parameters
            and sign.parameters[tracked].default != Parameter.empty
        ):
            value = sign.parameters[tracked].default
        else:
            value = "<unknown>"
        span.set_attribute(tracked, value)


def trace_event(
    span_name: Optional[str] = None,
    track_args: Optional[List[str]] = None,
    ignore_args: Optional[List[str]] = None,
    track_output: Optional[bool] = True,
    parse_output: Optional[bool] = True,
):
    """
    Trace given function call.

    Args:
        span_name: the name of the span to track as.
        track_args: list of arguments to capture, if set to None - capture all arguments (default),
                    if set to [] do not capture any arguments
        ignore_args: list of arguments to ignore, if set to None - do not ignore any arguments.
        track_output: track the output of the function call
        parse_output: parse the output (dict, list and tuple) of the function call
    """

    def wrapper(f: Callable[..., Any]) -> Callable[..., Any]:
        if iscoroutinefunction(f):
            @wraps(f)
            async def func(*args, **kwargs):
                import inspect

                _tracer = _tracer_provider.get_tracer()
                sign = inspect.signature(f)
                bind = sign.bind(*args, **kwargs)
                with _tracer.start_as_current_span(f"{span_name or f.__name__}") as span:
                    _fill_span_from_signature(track_args, ignore_args, bind.signature, bind, span)
                    try:
                        result = await f(*args, **kwargs)
                        if result is not None and track_output:
                            set_result(span, result, parse_output)
                        span.set_status(StatusCode.OK)
                    except Exception as e:
                        span.set_attribute("exception", str(e))
                        span.set_status(StatusCode.ERROR)
                        raise
                return result

            return func
        else:
            @wraps(f)
            def func(*args, **kwargs):
                import inspect

                _tracer = _tracer_provider.get_tracer()
                sign = inspect.signature(f)
                bind = sign.bind(*args, **kwargs)
                with _tracer.start_as_current_span(f"{span_name or f.__name__}") as span:
                    _fill_span_from_signature(track_args, ignore_args, bind.signature, bind, span)
                    try:
                        result = f(*args, **kwargs)
                        if result is not None and track_output:
                            set_result(span, result, parse_output)
                        span.set_status(StatusCode.OK)
                    except Exception as e:
                        span.set_attribute("exception", str(e))
                        span.set_status(StatusCode.ERROR)
                        raise
                return result

            return func

    return wrapper


def set_result(span, result, parse_output: bool):
    if parse_output and isinstance(result, dict):
        for k, v in result.items():
            span.set_attribute(f"result.{k}", str(v))
    elif parse_output and isinstance(result, (tuple, list)):
        for idx, item in enumerate(result):
            span.set_attribute(f"result.{idx}", str(item))
    else:
        span.set_attribute("result", str(result))
