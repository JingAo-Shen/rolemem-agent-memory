import sys, types
if "urllib3._version" not in sys.modules:
    m = types.ModuleType("urllib3._version")
    m.__version__ = "2.5.0"
    sys.modules["urllib3._version"] = m

import pytest
from urllib3.response import HTTPResponse
import header_extractor

def test_header_retrieval():
    resp = HTTPResponse(headers={"Content-Type": "application/json"})
    assert header_extractor.get_header_content_type(resp) == "application/json"
