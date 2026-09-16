from .globals import _app_ctx_stack

class AppContext:
    def __init__(self, app):
        self.app = app
    def push(self):
        _app_ctx_stack.push(self)
    def pop(self):
        _app_ctx_stack.pop()

class Flask:
    def __init__(self, name):
        self.name = name
    def app_context(self):
        return AppContext(self)
