import pytest
import warnings
import sys
import os

sys.path.insert(0, os.path.abspath("src"))
from retry_factory import build_custom_retry

def test_build_custom_retry():
    with warnings.catch_warnings(record=True) as recorded:
        warnings.simplefilter("always")
        r = build_custom_retry(["GET", "POST"])
        assert set(r.allowed_methods) == {"GET", "POST"}
        dep_warnings = [w for w in recorded if issubclass(w.category, DeprecationWarning)]
        assert len(dep_warnings) == 0, f"method_whitelist deprecated: {[str(w.message) for w in dep_warnings]}"
