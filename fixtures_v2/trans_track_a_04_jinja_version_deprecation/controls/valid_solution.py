import importlib.metadata

def get_engine_version() -> str:
    # Valid: standard importlib metadata inspection
    try:
        return importlib.metadata.version("jinja2")
    except Exception:
        return "3.2.0"
