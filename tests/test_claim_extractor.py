"""
tests/test_claim_extractor.py

Unit tests for DeterministicClaimExtractor.
"""

import pytest
from src.claim_validity.claim_extractor import DeterministicClaimExtractor
from src.claim_validity.types import ClaimType


@pytest.fixture
def extractor():
    return DeterministicClaimExtractor()


def test_extract_symbol_exists(extractor):
    raw = "Symbol `get_binary_stream` is available directly in `src/click/utils.py`."
    c = extractor.extract(raw, symbol="get_binary_stream", file_path="src/click/utils.py")
    assert c.claim_type == ClaimType.SYMBOL_EXISTS
    assert c.subject == "get_binary_stream"
    assert c.claim_parse_status == "PARSED"


def test_extract_attribute_exists(extractor):
    raw = "BaseHTTPResponse instances provide getheaders() method returning list of header tuples."
    c = extractor.extract(raw, symbol="BaseHTTPResponse")
    assert c.claim_type == ClaimType.ATTRIBUTE_EXISTS
    assert c.subject == "BaseHTTPResponse"
    assert c.object == "getheaders"
    assert c.claim_parse_status == "PARSED"


def test_extract_import_path(extractor):
    raw = "marshmallow exports pprint in __all__ at top level."
    c = extractor.extract(raw, symbol="pprint")
    assert c.claim_type == ClaimType.IMPORT_PATH_VALID
    assert c.claim_parse_status == "PARSED"


def test_extract_deprecation_status(extractor):
    raw = "Symbol `old_func` is deprecated and will be removed."
    c = extractor.extract(raw, symbol="old_func")
    assert c.claim_type == ClaimType.DEPRECATION_STATUS
    assert c.subject == "old_func"
    assert c.claim_parse_status == "PARSED"


def test_extract_signature_compatibility(extractor):
    raw = "Function `process_data` accepts parameters req, timeout, retries"
    c = extractor.extract(raw, symbol="process_data")
    assert c.claim_type == ClaimType.SIGNATURE_COMPATIBLE
    assert c.qualifiers.get("expected_parameters") == ["req", "timeout", "retries"]
    assert c.claim_parse_status == "PARSED"


def test_extract_default_value(extractor):
    raw = "Parameter `timeout` of `connect` defaults to 30"
    c = extractor.extract(raw, symbol="connect")
    assert c.claim_type == ClaimType.DEFAULT_VALUE
    assert c.qualifiers.get("parameter_name") == "timeout"
    assert c.qualifiers.get("expected_default") == "30"
    assert c.claim_parse_status == "PARSED"


def test_extract_behavioral_contract(extractor):
    raw = "When HelpFormatter is initialized, text buffered with write_text() can be retrieved via getvalue()."
    c = extractor.extract(raw, symbol="HelpFormatter")
    assert c.claim_type == ClaimType.BEHAVIORAL_CONTRACT
    assert c.subject == "HelpFormatter"
    assert c.claim_parse_status == "PARSED"


def test_extract_dependency_contract(extractor):
    raw = "HookSpec inspects hook functions via varnames allowing hook methods without explicit self parameter."
    c = extractor.extract(raw, symbol="HookSpec")
    assert c.claim_type == ClaimType.DEPENDENCY_CONTRACT
    assert c.claim_parse_status == "PARSED"


def test_extract_unresolved_arbitrary_statement(extractor):
    raw = "The quick brown fox jumps over the lazy dog."
    c = extractor.extract(raw, symbol="fox")
    assert c.claim_type == ClaimType.UNKNOWN_CLAIM_TYPE
    assert c.claim_parse_status == "UNRESOLVED"
