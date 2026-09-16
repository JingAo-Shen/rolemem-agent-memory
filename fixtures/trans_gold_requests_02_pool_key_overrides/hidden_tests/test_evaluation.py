import pytest
from pool_config import build_custom_adapter_pool

def test_build_custom_adapter_pool():
    adapter = build_custom_adapter_pool(connections=20, maxsize=20, block=True)
    assert adapter.poolmanager["connections"] == 20
    assert adapter.poolmanager["maxsize"] == 20
    assert adapter.poolmanager.get("block") is True
