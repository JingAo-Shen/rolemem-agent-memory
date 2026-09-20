import pytest
import debug_dumper

def test_export():
    assert debug_dumper.check_marshmallow_export() is True
