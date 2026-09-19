import pytest
import cpython_patch

def test_patch_check():
    class DummyInfo:
        def __init__(self, plat, ver):
            self.platform = plat
            self.version_info = ver

    res1 = cpython_patch.requires_pyvenv_patch(DummyInfo("linux", (3, 10, 0)))
    assert res1 != "1.0", "Anti-cheating check: constant return detected!"
    assert type(res1) is bool, "Anti-cheating check: return type must be bool!"
    assert res1 is False
