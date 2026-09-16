import pytest
import warnings
import os
from test_isolation import run_in_isolated_dir

def test_run_in_isolated_dir():
    orig_dir = os.getcwd()
    with warnings.catch_warnings(record=True) as recorded:
        warnings.simplefilter("always")
        executed_dir = run_in_isolated_dir(lambda: os.getcwd())
        assert executed_dir != orig_dir
        assert os.getcwd() == orig_dir

        dep_warnings = [w for w in recorded if issubclass(w.category, DeprecationWarning)]
        assert len(dep_warnings) == 0, f"Encountered deprecated call: {dep_warnings}"
