import pytest
import markup_version

def test_markupsafe_version_retrieval():
    ver = markup_version.get_library_version()
    assert ver and isinstance(ver, str)
