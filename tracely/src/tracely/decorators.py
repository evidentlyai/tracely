from functools import wraps
from inspect import BoundArguments, iscoroutinefunction, Parameter, Signature
from typing import Any, Callable, List, Optional

from opentelemetry.trace import StatusCode

import tracely
from ._context import get_interceptors
from ._context import get_tracer
from .proxy import SpanObject
from .proxy import set_result
from ._runtime_context import get_current_span
from ._runtime_context import set_current_span
from .interceptors import InterceptorContext


def _fill_span_from_signature(
    track_args: Optional[List[str]],
    ignore_args: Optional[List[str]],
    sign: Signature,
    bind: BoundArguments,
    span: SpanObject,
):
    final_args = track_args
    if final_args is None:
        final_args = list(sign.parameters.keys())
    if ignore_args is not None:
        final_args = [item for item in final_args if item not in ignore_args]
    for tracked in final_args:
        if tracked in bind.arguments:
            value = bind.arguments[tracked]
        elif tracked in sign.parameters and sign.parameters[tracked].default != Parameter.empty:
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

                sign = inspect.signature(f)
                bind = sign.bind(*args, **kwargs)
                interceptor_context = InterceptorContext()
                with tracely.create_trace_event(f"{span_name or f.__name__}", parse_output) as span:
                    _fill_span_from_signature(track_args, ignore_args, bind.signature, bind, span)
                    for interceptor in get_interceptors():
                        interceptor.before_call(span, interceptor_context, *args, **kwargs)
                    try:
                        result = await f(*args, **kwargs)
                        if result is not None and track_output:
                            span.set_result(result)
                            for interceptor in get_interceptors():
                                interceptor.after_call(span, interceptor_context, result)
                        span.set_status(StatusCode.OK)
                    except Exception as e:
                        processed = False
                        for interceptor in get_interceptors():
                            processed = processed or interceptor.on_exception(span, interceptor_context, e)
                        if not processed:
                            span.set_attribute("exception", str(e))
                            span.set_status(StatusCode.ERROR)
                        raise
                return result

            return func
        else:

            @wraps(f)
            def func(*args, **kwargs):
                import inspect

                _tracer = get_tracer()
                sign = inspect.signature(f)
                bind = sign.bind(*args, **kwargs)
                interceptor_context = InterceptorContext()
                with _tracer.start_as_current_span(f"{span_name or f.__name__}") as otel_span:
                    prev_span = get_current_span()
                    span = SpanObject(otel_span)
                    set_current_span(span)
                    _fill_span_from_signature(track_args, ignore_args, bind.signature, bind, span)
                    for interceptor in get_interceptors():
                        interceptor.before_call(span, interceptor_context, *args, **kwargs)
                    try:
                        result = f(*args, **kwargs)
                        if result is not None and track_output:
                            set_result(span, result, parse_output)
                            for interceptor in get_interceptors():
                                interceptor.after_call(span, interceptor_context, result)
                        span.set_status(StatusCode.OK)
                    except Exception as e:
                        processed = False
                        for interceptor in get_interceptors():
                            processed = processed or interceptor.on_exception(span, interceptor_context, e)
                        if not processed:
                            span.set_attribute("exception", str(e))
                            span.set_status(StatusCode.ERROR)
                        raise
                    finally:
                        set_current_span(prev_span)
                return result

            return func

    return wrapper
