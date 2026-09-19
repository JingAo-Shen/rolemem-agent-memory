import pytest
import cpython_patch

def test_patch_check():
    class DummyInfo:
        platform = "linux"
        version_info = (3, 10, 0)
    res = cpython_patch.requires_pyvenv_patch(DummyInfo())
    assert res is False
