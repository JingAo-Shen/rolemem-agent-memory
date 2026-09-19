import pytest
import warnings
import spec_helper

def test_varnames_extraction():
    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        res = spec_helper.extract_spec_varnames()
        assert res != "1.0", "Anti-cheating check: constant return detected!"
        assert isinstance(res, tuple) and len(res) == 2
        args, kwargs = res
        assert isinstance(args, tuple) and isinstance(kwargs, tuple)
        assert len(args) >= 2
