import pytest
import warnings
from wsgi_helper import extract_wsgi_header

def test_extract_wsgi_header():
    environ = {
        "HTTP_HOST": "example.com:8080",
        "HTTP_ACCEPT": "application/json",
        "PATH_INFO": "/api/v1"
    }
    with warnings.catch_warnings(record=True) as recorded:
        warnings.simplefilter("always")
        host = extract_wsgi_header(environ, "host")
        assert host == "example.com:8080"
        accept = extract_wsgi_header(environ, "accept")
        assert accept == "application/json"
        
        dep_warnings = [w for w in recorded if issubclass(w.category, DeprecationWarning)]
        assert len(dep_warnings) == 0, f"Encountered deprecated call: {dep_warnings}"
