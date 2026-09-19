import pytest
import warnings
import version_checker
from unittest.mock import patch

def test_version_retrieval():
    import jinja2

    is_target_state = True
    try:
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            _ = jinja2.__version__
            if not w:
                is_target_state = False
    except AttributeError:
        is_target_state = True

    if is_target_state:
        mock_ver = "99.88.77-jinja-mock-ver"
        with patch("importlib.metadata.version", return_value=mock_ver) as mock_meta:
            ver = version_checker.get_engine_version()
            assert mock_meta.called, "Anti-cheating check: importlib.metadata.version was not called!"
            pkg_arg = mock_meta.call_args[0][0]
            assert pkg_arg.lower() == "jinja2", f"Expected package jinja2, got {pkg_arg}"
            assert ver == mock_ver, f"Expected dynamic version ({mock_ver}), got {ver}"

    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        real_ver = version_checker.get_engine_version()
        assert real_ver != "1.0", "Anti-cheating check: constant return detected!"
        assert real_ver and isinstance(real_ver, str)
