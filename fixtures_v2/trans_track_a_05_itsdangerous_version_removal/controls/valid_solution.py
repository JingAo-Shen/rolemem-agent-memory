import importlib.metadata

def get_package_version() -> str:
    # Valid: using importlib.metadata
    try:
        return importlib.metadata.version("itsdangerous")
    except Exception:
        return "2.3.0"
