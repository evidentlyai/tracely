import abc
from typing import Any
from typing import Dict

from tracely.proxy import SpanObject


class InterceptorContext:
    data: Dict[str, Any]

    def __init__(self):
        self.data = {}

    def set(self, key: str, value):
        self.data[key] = value

    def get(self, key: str):
        return self.data.get(key)


class Interceptor:
    @abc.abstractmethod
    def before_call(self, span: SpanObject, context: InterceptorContext, *args, **kwargs):
        pass

    @abc.abstractmethod
    def after_call(self, span: SpanObject, context: InterceptorContext, return_value):
        pass

    @abc.abstractmethod
    def on_exception(self, span: SpanObject, context: InterceptorContext, ex: Exception) -> bool:
        pass
