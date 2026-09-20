def build_doctest_args(enabled: bool):
    if enabled:
        return ["--doctest"]
    return []
