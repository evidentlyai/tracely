from tracely import Interceptor
from tracely import init_tracing
from tracely import trace_event


class ExampleInterceptor(Interceptor):
    def before_call(self, span, context, *args, **kwargs):
        span.set_attribute("custom_attribute", 1)

    def after_call(self, span, context, *args, **kwargs):
        pass

    def on_exception(self, span, context, exception) -> bool:
        pass


init_tracing(exporter_type="console", interceptors=[ExampleInterceptor()])


@trace_event()
def func(data: str) -> str:
    return data
