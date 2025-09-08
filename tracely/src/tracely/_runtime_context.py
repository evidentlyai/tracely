from typing import Optional

from .proxy import SpanObject


class RuntimeContext:
    def __init__(self):
        self.span = None

    def set_current_span(self, span: Optional[SpanObject]):
        self.span = span

    def get_current_span(self) -> Optional[SpanObject]:
        return self.span

    def reset_span(self):
        self.span = None


_DEFAULT_CONTEXT = RuntimeContext()


def get_current_span(context: Optional[RuntimeContext] = None) -> Optional[SpanObject]:
    if context is None:
        return _DEFAULT_CONTEXT.get_current_span()
    return context.get_current_span()


def set_current_span(span: Optional[SpanObject], context: Optional[RuntimeContext] = None):
    if context is None:
        _DEFAULT_CONTEXT.set_current_span(span)
    else:
        context.set_current_span(span)


def reset_span(context: Optional[RuntimeContext] = None):
    if context is None:
        _DEFAULT_CONTEXT.reset_span()
    else:
        context.reset_span()
