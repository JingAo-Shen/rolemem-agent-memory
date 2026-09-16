# Modern Werkzeug URLs (post PR #2085)
import warnings

class Href:
    def __init__(self, base):
        warnings.warn(
            "'Href' is deprecated and will be removed in Werkzeug 2.1. Use 'werkzeug.routing' instead.",
            DeprecationWarning,
            stacklevel=2
        )
        self.base = base
