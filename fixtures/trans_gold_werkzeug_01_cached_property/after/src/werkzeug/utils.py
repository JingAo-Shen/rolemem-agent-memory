# Modern Werkzeug utils (post PR #2085)
import warnings

def invalidate_cached_property(obj, name):
    warnings.warn(
        "'invalidate_cached_property' is deprecated and will be removed in Werkzeug 2.1. "
        "Use 'del obj.name' or 'delattr(obj, name)' instead.",
        DeprecationWarning,
        stacklevel=2
    )
    obj.__dict__.pop(name, None)
