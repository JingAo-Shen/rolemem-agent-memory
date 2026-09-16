def reset_cached_attribute(instance, attr_name):
    # Valid pattern: standard Python descriptor deletion del obj.prop / delattr
    try:
        delattr(instance, attr_name)
    except AttributeError:
        pass
