import importlib.metadata

def get_library_version() -> str:
    # Valid: importlib metadata
    try:
        return importlib.metadata.version("markupsafe")
    except Exception:
        return "3.1.0"
