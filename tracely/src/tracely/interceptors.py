import abc

from tracely.proxy import SpanObject


class InterceptorContext:
    pass


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
