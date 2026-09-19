import pytest
import warnings
import client_factory

def test_proxied_client_creation():
    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        client = client_factory.build_proxied_client("http://localhost:8080")
        assert client is not None
        assert client._transport is not None
