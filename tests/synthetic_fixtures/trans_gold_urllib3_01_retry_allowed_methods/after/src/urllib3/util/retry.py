import warnings

class Retry:
    DEFAULT_ALLOWED_METHODS = frozenset(['HEAD', 'GET', 'PUT', 'DELETE', 'OPTIONS', 'TRACE'])
    def __init__(self, total=3, allowed_methods=None, method_whitelist=None):
        self.total = total
        if method_whitelist is not None:
            warnings.warn(
                "Using 'method_whitelist' is deprecated and will be removed in urllib3 v2.0. Use 'allowed_methods' instead.",
                DeprecationWarning,
                stacklevel=2
            )
            allowed_methods = method_whitelist
        self.allowed_methods = frozenset(allowed_methods) if allowed_methods is not None else self.DEFAULT_ALLOWED_METHODS
