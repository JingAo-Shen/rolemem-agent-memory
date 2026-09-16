import pytest
import warnings
from retry_factory import create_all_verbs_retry

def test_create_all_verbs_retry():
    with warnings.catch_warnings(record=True) as recorded:
        warnings.simplefilter("always")
        r = create_all_verbs_retry()
        assert r.allowed_methods is None or r.allowed_methods is False

        dep_warnings = [w for w in recorded if issubclass(w.category, DeprecationWarning)]
        assert len(dep_warnings) == 0, f"Encountered deprecated call: {dep_warnings}"
