import warnings

class Retry:
    def __init__(self, allowed_methods=None):
        if allowed_methods is not None and hasattr(allowed_methods, '__len__') and len(allowed_methods) == 0:
            warnings.warn(
                "Passing an empty collection for 'allowed_methods' is deprecated. Pass None or False instead.",
                DeprecationWarning,
                stacklevel=2
            )
            self.allowed_methods = False
        else:
            self.allowed_methods = allowed_methods
