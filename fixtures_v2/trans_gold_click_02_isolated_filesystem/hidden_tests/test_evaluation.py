import pytest
import warnings
import os
import sys

sys.path.insert(0, os.path.abspath("src"))
from test_isolation import run_in_isolated_dir

def test_run_in_isolated_dir():
    orig_cwd = os.getcwd()
    with warnings.catch_warnings(record=True) as recorded:
        warnings.simplefilter("always")
        res_cwd = run_in_isolated_dir(lambda: os.getcwd())
        assert res_cwd != orig_cwd
        assert os.getcwd() == orig_cwd
        dep_warnings = [w for w in recorded if issubclass(w.category, DeprecationWarning)]
        assert len(dep_warnings) == 0, f"isolated_filesystem deprecated: {[str(w.message) for w in dep_warnings]}"
