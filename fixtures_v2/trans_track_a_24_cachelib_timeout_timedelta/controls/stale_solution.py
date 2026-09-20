def normalize_timeout_value(cache, timeout):
    # Stale workaround assuming BaseCache lacks _normalize_timeout
    return getattr(cache, "default_timeout", 300)
