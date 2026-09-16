import pytest
import warnings
import sys
import os

sys.path.insert(0, os.path.abspath("src"))
from requests.adapters import HTTPAdapter
from requests.models import PreparedRequest
from adapter_helper import get_adapter_connection

def test_get_conn():
    adapter = HTTPAdapter()
    req = PreparedRequest()
    req.prepare_url("https://httpbin.org/get", {})
    with warnings.catch_warnings(record=True) as recorded:
        warnings.simplefilter("always")
        conn = get_adapter_connection(adapter, req, verify=True)
        assert conn is not None
        dep_warnings = [w for w in recorded if issubclass(w.category, DeprecationWarning)]
        assert len(dep_warnings) == 0, f"get_connection deprecated: {[str(w.message) for w in dep_warnings]}"
