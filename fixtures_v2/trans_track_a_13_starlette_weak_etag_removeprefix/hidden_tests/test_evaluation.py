import pytest
import etag_helper

def test_etag_normalization():
    assert etag_helper.is_etag_not_modified("W123", "W123") is True
