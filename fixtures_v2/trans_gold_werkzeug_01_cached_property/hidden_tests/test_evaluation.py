import pytest
import warnings
import sys
import os

sys.path.insert(0, os.path.abspath("src"))
from werkzeug.utils import cached_property
from property_helper import reset_cached_attribute

class DummyTarget:
    def __init__(self):
        self.computations = 0

    @cached_property
    def value(self):
        self.computations += 1
        return 42

def test_reset_cached_attribute():
    target = DummyTarget()
    assert target.value == 42
    assert target.computations == 1

    with warnings.catch_warnings(record=True) as recorded:
        warnings.simplefilter("always")
        reset_cached_attribute(target, "value")
        dep_warnings = [w for w in recorded if issubclass(w.category, DeprecationWarning)]
        assert len(dep_warnings) == 0, f"Encountered deprecated call: {[str(w.message) for w in dep_warnings]}"

    assert "value" not in target.__dict__
    assert target.value == 42
    assert target.computations == 2
