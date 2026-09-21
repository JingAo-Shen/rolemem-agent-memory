"""
tests/test_claim_extractor.py

Unit tests for DeterministicClaimExtractor:
- Verifies extraction across all claim patterns.
- Includes Marshmallow extraction regression test.
- Verifies unparsed fallback for unparsable statements.
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
    raw = "Symbol `utils` can be imported from `click`."
    c = extractor.extract(raw, symbol="utils")
    assert c.claim_type == ClaimType.IMPORT_PATH_VALID
    assert c.subject == "utils"
    assert c.predicate == "imported_from"
    assert c.object == "click"
    assert c.claim_parse_status == "PARSED"


def test_extract_marshmallow_regression(extractor):
    """Regression test ensuring Marshmallow claim parses subject=pprint, predicate=exported_in, object=marshmallow.__all__."""
    raw = "marshmallow exports pprint in __all__ at top level."
    c = extractor.extract(raw, symbol="pprint")
    assert c.claim_type == ClaimType.IMPORT_PATH_VALID
    assert c.subject == "pprint"
    assert c.predicate == "exported_in"
    assert c.object == "marshmallow.__all__"
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
    raw = "HookCaller inspects hook functions via varnames allowing hook methods without explicit self parameter."
    c = extractor.extract(raw, symbol="HookCaller")
    assert c.claim_type == ClaimType.DEPENDENCY_CONTRACT
    assert c.subject == "HookCaller"
    assert c.predicate == "depends_on"
    assert c.object == "varnames"
    assert c.claim_parse_status == "PARSED"


def test_extract_dependency_strict_regression_cases(extractor):
    cases = [
        ("HookSpec inspects hook functions via varnames", "HookSpec", "depends_on", "varnames"),
        ("HookCaller inspects hook functions via varnames", "HookCaller", "depends_on", "varnames"),
        ("Service depends on Database", "Service", "depends_on", "Database"),
        ("Class Service depends on Database", "Service", "depends_on", "Database"),
        ("pkg.Service.run calls helper", "pkg.Service.run", "depends_on", "helper"),
    ]
    for raw, exp_subj, exp_pred, exp_obj in cases:
        c = extractor.extract(raw)
        assert c.claim_type == ClaimType.DEPENDENCY_CONTRACT, f"Failed type on {raw}"
        assert c.subject == exp_subj, f"Failed subject on {raw}: got {c.subject}, expected {exp_subj}"
        assert c.predicate == exp_pred, f"Failed predicate on {raw}: got {c.predicate}, expected {exp_pred}"
        assert c.object == exp_obj, f"Failed object on {raw}: got {c.object}, expected {exp_obj}"
        assert c.claim_parse_status == "PARSED", f"Failed parse status on {raw}"


def test_clm_000045_corrected_representation(extractor):
    raw = "HookSpec inspects hook functions via varnames allowing hook methods without explicit self parameter."
    c = extractor.extract(
        raw_statement=raw,
        claim_id="CLM-000045",
        repository="pluggy",
        file_path="src/pluggy/_hooks.py",
        symbol="HookSpec",
        source_case_id="MV21-000045"
    )
    assert c.claim_type == ClaimType.DEPENDENCY_CONTRACT
    assert c.subject == "HookSpec"
    assert c.predicate == "depends_on"
    assert c.object == "varnames"
    assert c.symbol == "HookSpec"
    assert c.source_case_id == "MV21-000045"
    assert c.claim_parse_status == "PARSED"


def test_blind_inputs_leading_symbol_subject_not_truncated(extractor):
    """Semantic invariant: If a known symbol is the leading subject in statement, extracted subject must not truncate to last char."""
    import json
    blind_path = "/code/rolemem-agent-memory/data/memory_validity_v2_1/blind_inputs.jsonl"
    with open(blind_path, "r", encoding="utf-8") as f:
        blind_records = [json.loads(line) for line in f if line.strip()]

    for r in blind_records:
        st = r["memory_statement"]
        sym = r.get("symbol_qualified_name") or r.get("symbol", "")
        cid = r["case_id"]
        claim = extractor.extract(st, repository=r.get("repository", ""), file_path=r.get("file_path", ""), symbol=sym)

        if sym and len(sym) > 1:
            prefixes = [sym, f"`{sym}`", f"'{sym}'", f'"{sym}"', f"Class {sym}", f"Symbol {sym}", f"Function {sym}"]
            if any(st.startswith(p) for p in prefixes):
                assert claim.subject != sym[-1], (
                    f"Regression: Single-character truncation detected for {cid}! "
                    f"Symbol '{sym}', Extracted subject '{claim.subject}', Statement: '{st}'"
                )
                assert claim.subject.split(".")[-1] == sym.split(".")[-1], (
                    f"Subject alignment mismatch for {cid}: expected '{sym}', got '{claim.subject}'"
                )


def test_extract_unresolved_arbitrary_statement(extractor):
    raw = "The quick brown fox jumps over the lazy dog."
    c = extractor.extract(raw, symbol="fox")
    assert c.claim_type == ClaimType.UNKNOWN_CLAIM_TYPE
    assert c.claim_parse_status == "UNRESOLVED"
