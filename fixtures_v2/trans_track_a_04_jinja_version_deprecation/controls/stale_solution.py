import jinja2

def get_engine_version() -> str:
    # Stale: accessing __version__ attribute
    return str(jinja2.__version__)
