import pytest
import warnings
from requests.adapters import HTTPAdapter

class DummyReq:
    def __init__(self, url):
        self.url = url

def test_get_adapter_connection():
    from adapter_helper import get_adapter_connection
    adapter = HTTPAdapter()
    req = DummyReq("https://api.github.com")

    with warnings.catch_warnings(record=True) as recorded:
        warnings.simplefilter("always")
        conn = get_adapter_connection(adapter, req, verify=True)
        assert conn is not None
        assert "ConnTLS" in str(conn)

        dep_warnings = [w for w in recorded if issubclass(w.category, DeprecationWarning)]
        assert len(dep_warnings) == 0, f"Encountered deprecated call: {dep_warnings}"
