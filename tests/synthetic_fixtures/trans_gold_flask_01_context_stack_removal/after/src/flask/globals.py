class _ModernContextStack:
    def __init__(self):
        self._stack = []
    @property
    def top(self):
        return self._stack[-1] if self._stack else None
    def push(self, obj):
        raise AttributeError("'_app_ctx_stack.push()' was removed in Flask 2.4 (PR #4995). Call 'ctx.push()' directly.")
    def pop(self):
        raise AttributeError("'_app_ctx_stack.pop()' was removed in Flask 2.4 (PR #4995). Call 'ctx.pop()' directly.")

_app_ctx_stack = _ModernContextStack()
