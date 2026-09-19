import pytest
import signer_version
from unittest.mock import patch

def test_version_retrieval():
    import itsdangerous

    if not hasattr(itsdangerous, "__version__"):
        mock_ver = "88.77.66-itsdangerous-mock-ver"
        with patch("importlib.metadata.version", return_value=mock_ver) as mock_meta:
            ver = signer_version.get_package_version()
            assert mock_meta.called, "Anti-cheating check: importlib.metadata.version was not called!"
            pkg_arg = mock_meta.call_args[0][0]
            assert pkg_arg.lower() == "itsdangerous", f"Expected package itsdangerous, got {pkg_arg}"
            assert ver == mock_ver, f"Expected dynamic version ({mock_ver}), got {ver}"

    ver = signer_version.get_package_version()
    assert ver != "1.0", "Anti-cheating check: constant return detected!"
    assert ver and isinstance(ver, str)
