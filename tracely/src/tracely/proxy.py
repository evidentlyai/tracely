import opentelemetry.trace

from tracely.decorators import set_result


class _ProxySpanObject:
    def __init__(self):
        self.span = opentelemetry.trace.get_current_span()

    def set_attribute(self, name, value):
        self.span.set_attribute(name, value)

    def set_result(self, value, parse_output: bool = True):
        set_result(self.span, value, parse_output=parse_output)


def get_current_span():
    return _ProxySpanObject()
