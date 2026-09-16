import pytest
import warnings
import sys
import os

sys.path.insert(0, os.path.abspath("src"))

def test_extract_wsgi_header():
    environ = {
        "HTTP_HOST": "localhost:8080",
        "HTTP_USER_AGENT": "RoleMemBot/1.0"
    }
    with warnings.catch_warnings(record=True) as recorded:
        warnings.simplefilter("always")
        from wsgi_helper import extract_wsgi_header
        host = extract_wsgi_header(environ, "host")
        assert host == "localhost:8080"
        dep_warnings = [w for w in recorded if issubclass(w.category, (DeprecationWarning, UserWarning))]
        assert len(dep_warnings) == 0, f"Encountered deprecated call: {[str(w.message) for w in dep_warnings]}"
