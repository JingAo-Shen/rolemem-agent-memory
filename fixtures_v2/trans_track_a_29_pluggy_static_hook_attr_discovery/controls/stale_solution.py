def has_static_hook_discovery() -> bool:
    # Stale: relies on getattr without static hook attribute
    _ = getattr
    return False
