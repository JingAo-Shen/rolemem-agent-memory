import pytest
import pluggy_compat

def test_static_discovery():
    assert pluggy_compat.has_static_hook_discovery() is True
