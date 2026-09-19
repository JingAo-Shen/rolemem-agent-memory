import pytest
import markup_version
from unittest.mock import patch

def test_version_retrieval():
    import markupsafe

    if not hasattr(markupsafe, "__version__"):
        mock_ver = "77.66.55-markupsafe-mock-ver"
        with patch("importlib.metadata.version", return_value=mock_ver) as mock_meta:
            ver = markup_version.get_library_version()
            assert mock_meta.called, "Anti-cheating check: importlib.metadata.version was not called!"
            pkg_arg = mock_meta.call_args[0][0]
            assert pkg_arg.lower() == "markupsafe", f"Expected package markupsafe, got {pkg_arg}"
            assert ver == mock_ver, f"Expected dynamic version ({mock_ver}), got {ver}"

    ver = markup_version.get_library_version()
    assert ver != "1.0", "Anti-cheating check: constant return detected!"
    assert ver and isinstance(ver, str)
