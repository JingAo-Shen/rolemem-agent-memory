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
        assert prop != "1.0", "Anti-cheating check: constant return detected!"
        assert hasattr(prop, "__get__"), "Anti-cheating check: must return a descriptor!"

        DummyRequest.host = prop
        req1 = DummyRequest({"HTTP_HOST": "localhost"})
        assert req1.host == "localhost"
        req2 = DummyRequest({"HTTP_HOST": "api.example.com"})
        assert req2.host == "api.example.com"
        req3 = DummyRequest({})
        assert req3.host in ("", None)
