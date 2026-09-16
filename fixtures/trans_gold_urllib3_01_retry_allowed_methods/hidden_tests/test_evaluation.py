import pytest
import warnings
from retry_factory import build_custom_retry

def test_build_custom_retry():
    with warnings.catch_warnings(record=True) as recorded:
        warnings.simplefilter("always")
        r = build_custom_retry(["GET", "POST"])
        assert r.allowed_methods == frozenset(["GET", "POST"])

        dep_warnings = [w for w in recorded if issubclass(w.category, DeprecationWarning)]
        assert len(dep_warnings) == 0, f"Encountered deprecated call: {dep_warnings}"
