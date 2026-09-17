import os
import sys
import pathlib
import warnings
import pytest

sys.path.insert(0, os.path.abspath("src"))
from test_workspace_helper import setup_test_workspace

def test_setup_test_workspace(tmp_path):
    with warnings.catch_warnings(record=True) as recorded:
        warnings.simplefilter("always")
        res = setup_test_workspace(tmp_path)
        assert res is not None
        dep_warnings = [w for w in recorded if issubclass(w.category, DeprecationWarning) and "isolated_filesystem" in str(w.message)]
        assert len(dep_warnings) == 0, f"Deprecated isolated_filesystem was called: {[str(w.message) for w in dep_warnings]}"
        p = pathlib.Path(res)
        assert p.exists() or str(p).startswith(str(tmp_path))
