from werkzeug.utils import environ_property

class HeaderHolder:
    host = environ_property("HTTP_HOST")
    def __init__(self, environ):
        self.environ = environ

def extract_wsgi_header(environ: dict, header_name: str) -> str:
    # Stale pattern: accesses deprecated environ_property descriptor (PR #3276)
    if header_name.lower() == "host":
        return HeaderHolder(environ).host or ""
    key = "HTTP_" + header_name.upper().replace("-", "_")
    return environ.get(key, "")
