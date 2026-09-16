import pytest
import warnings
import sys
import os

sys.path.insert(0, os.path.abspath("src"))
from retry_factory import create_all_verbs_retry

def test_create_all_verbs_retry():
    with warnings.catch_warnings(record=True) as recorded:
        warnings.simplefilter("always")
        r = create_all_verbs_retry()
        assert r.allowed_methods is None or r.allowed_methods is False
        fut_warnings = [w for w in recorded if issubclass(w.category, (FutureWarning, DeprecationWarning))]
        assert len(fut_warnings) == 0, f"empty collection allowed_methods warning: {[str(w.message) for w in fut_warnings]}"
