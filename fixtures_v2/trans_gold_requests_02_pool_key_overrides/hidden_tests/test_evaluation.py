import pytest
import sys
import os

sys.path.insert(0, os.path.abspath("src"))
from requests.adapters import HTTPAdapter
from requests.models import PreparedRequest
from pool_config import get_pool_key_attributes

def test_pool_keys():
    adapter = HTTPAdapter()
    req = PreparedRequest()
    req.prepare_url("https://httpbin.org/get", {})
    attrs = get_pool_key_attributes(adapter, req, verify=True)
    assert isinstance(attrs, tuple) and len(attrs) == 2, "Must return (host_params, pool_kwargs) tuple"
    host_params, pool_kwargs = attrs
    assert "ssl_context" in pool_kwargs
