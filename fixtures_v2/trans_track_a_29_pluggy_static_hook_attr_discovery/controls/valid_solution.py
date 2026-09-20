import pluggy._manager

def has_static_hook_discovery() -> bool:
    assert hasattr(pluggy._manager, "_static_hook_attr")
    return True
