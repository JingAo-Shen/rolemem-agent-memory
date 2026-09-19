import pytest
import warnings
import header_proxy

class DummyRequest:
    def __init__(self, env):
        self.environ = env

def test_environ_property_creation():
    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        prop = header_proxy.create_header_property("HTTP_HOST")
        DummyRequest.host = prop
        req = DummyRequest({"HTTP_HOST": "localhost"})
        assert req.host == "localhost"
