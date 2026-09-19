import pytest
import warnings
import httpx
import client_factory

def test_proxied_client_creation():
    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        client = client_factory.build_proxied_client("http://localhost:8080")
        assert client != "1.0", "Anti-cheating check: constant return detected!"
        assert isinstance(client, httpx.Client), "Anti-cheating check: must return httpx.Client instance!"
        assert client._transport is not None
