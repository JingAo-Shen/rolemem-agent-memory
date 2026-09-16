from .globals import _app_ctx_stack

class AppContext:
    def __init__(self, app):
        self.app = app
    def push(self):
        _app_ctx_stack._stack.append(self)
        return self
    def pop(self):
        return _app_ctx_stack._stack.pop() if _app_ctx_stack._stack else None

class Flask:
    def __init__(self, name):
        self.name = name
    def app_context(self):
        return AppContext(self)
