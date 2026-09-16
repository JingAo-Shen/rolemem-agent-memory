from werkzeug.utils import invalidate_cached_property

def reset_cached_attribute(instance, attr_name):
    # Stale pattern: invokes deprecated invalidate_cached_property (PR #2084)
    invalidate_cached_property(instance, attr_name)
