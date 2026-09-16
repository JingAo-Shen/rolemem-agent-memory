class _ContextStack:
    def __init__(self):
        self._stack = []
    def push(self, obj):
        self._stack.append(obj)
    def pop(self):
        return self._stack.pop() if self._stack else None
    @property
    def top(self):
        return self._stack[-1] if self._stack else None

_app_ctx_stack = _ContextStack()
