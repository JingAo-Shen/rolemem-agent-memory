def extract_wsgi_header(environ: dict, header_name: str) -> str:
    # Valid pattern: direct dictionary access on WSGI environ mapping
    key = "HTTP_" + header_name.upper().replace("-", "_")
    return environ.get(key, environ.get(header_name, ""))
