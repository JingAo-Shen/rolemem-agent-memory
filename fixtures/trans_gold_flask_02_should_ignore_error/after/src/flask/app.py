import warnings

class Flask:
    def __init__(self, name):
        self.name = name
        self.error_handlers = {}
    def should_ignore_error(self, error):
        warnings.warn(
            "'should_ignore_error' is deprecated and will be removed in Flask 3.2. Register explicit error handlers instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return False
    def errorhandler(self, exc_class):
        def decorator(fn):
            self.error_handlers[exc_class] = fn
            return fn
        return decorator
    def handle_exception(self, e):
        handler = self.error_handlers.get(type(e))
        if handler:
            return handler(e)
        raise e
