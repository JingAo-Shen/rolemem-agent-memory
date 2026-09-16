class Retry:
    DEFAULT_METHOD_WHITELIST = frozenset(['HEAD', 'GET', 'PUT', 'DELETE', 'OPTIONS', 'TRACE'])
    def __init__(self, total=3, method_whitelist=None):
        self.total = total
        self.method_whitelist = frozenset(method_whitelist) if method_whitelist is not None else self.DEFAULT_METHOD_WHITELIST
