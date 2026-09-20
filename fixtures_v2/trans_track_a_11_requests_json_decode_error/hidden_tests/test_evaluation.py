import pytest
from requests import Response
import client_parser

def test_safe_parse():
    resp = Response()
    resp._content = b"not json"
    resp.encoding = None
    res = client_parser.parse_api_response(resp)
    assert res == {"error": "invalid json"}
