import pytest
import warnings
import spec_helper

def test_varnames_extraction():
    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        args, kwargs = spec_helper.extract_spec_varnames()
        assert len(args) >= 2
