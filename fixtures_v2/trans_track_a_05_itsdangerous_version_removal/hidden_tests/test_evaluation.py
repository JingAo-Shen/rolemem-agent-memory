import pytest
import signer_version

def test_itsdangerous_version_retrieval():
    ver = signer_version.get_package_version()
    assert ver and isinstance(ver, str)
