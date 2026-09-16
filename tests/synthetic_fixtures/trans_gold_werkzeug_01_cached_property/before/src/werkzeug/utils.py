# Legacy Werkzeug utils
def invalidate_cached_property(obj, name):
    """Legacy property invalidation helper."""
    obj.__dict__.pop(name, None)
