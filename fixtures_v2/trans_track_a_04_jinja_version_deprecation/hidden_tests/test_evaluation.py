import pytest
import warnings
import version_checker

def test_jinja_version():
    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        ver = version_checker.get_engine_version()
        assert ver and isinstance(ver, str)
