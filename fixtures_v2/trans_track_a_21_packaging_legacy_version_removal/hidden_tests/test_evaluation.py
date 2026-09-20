import pytest
import version_parser

def test_parse_version_safely():
    assert version_parser.parse_version_safely("1.2.3") == "1.2.3"
