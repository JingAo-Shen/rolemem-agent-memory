import pytest
import warnings
from property_helper import reset_cached_attribute

class MockResource:
    def __init__(self):
        self._computed = 0

    @property
    def data(self):
        self._computed += 1
        return 42

def test_reset_cached_attribute_success():
    res = MockResource()
    # Cache a value
    res.__dict__["data"] = 999
    assert res.__dict__["data"] == 999

    with warnings.catch_warnings(record=True) as recorded:
        warnings.simplefilter("always")
        reset_cached_attribute(res, "data")
        assert "data" not in res.__dict__

        # Assert no DeprecationWarning from legacy invalidate_cached_property
        dep_warnings = [w for w in recorded if issubclass(w.category, DeprecationWarning)]
        assert len(dep_warnings) == 0, f"Encountered deprecated call: {dep_warnings}"
