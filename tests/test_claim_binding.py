"""
tests/test_claim_binding.py

Unit tests for ClaimEvidenceBinder:
- Verifies Cat B, Cat C, and Cat D2 evidence binding rules.
- Tests failure modes for mismatched commits, subjects, dependency paths, and contract hashes.
"""

import pytest
from src.claim_validity.binding import ClaimEvidenceBinder, ClaimEvidenceBinding
from src.claim_validity.types import MemoryClaim, ClaimType


@pytest.fixture
def binder():
    return ClaimEvidenceBinder()


def test_cat_b_verified_binding(binder):
    claim = MemoryClaim(
        claim_id="CLM-000037",
        raw_statement="When HelpFormatter is initialized, text buffered with write_text() can be retrieved via getvalue().",
        claim_type=ClaimType.BEHAVIORAL_CONTRACT,
        subject="HelpFormatter",
        predicate="satisfies_contract",
        object="text buffered with write_text() can be retrieved via getvalue().",
        repository="click",
        file_path="src/click/formatting.py",
        symbol="HelpFormatter",
        source_case_id="MV21-000037"
    )
    art = {
        "case_id": "MV21-000037",
        "repository": "click",
        "base_commit": "c1",
        "target_commit": "c2",
        "claim": "When HelpFormatter is initialized, text buffered with write_text() can be retrieved via getvalue().",
        "claim_subject": "HelpFormatter",
        "claim_predicate": "buffered text via write_text is retrievable via getvalue",
        "contract_assertions": ["hf = HelpFormatter()", "hf.write_text('help')"],
        "target_execution": {"passed": True, "contract_hash": "hash123"}
    }
    binding = binder.verify(claim, art, base_commit="c1", target_commit="c2", repository="click")
    assert binding.binding_status == "VERIFIED"
    assert binding.contract_hash == "hash123"
    assert binding.artifact_claim_hash is not None
    assert binding.contract_assertions_hash is not None


def test_cat_b_mismatched_claim_hash(binder):
    claim = MemoryClaim(
        claim_id="CLM-000037",
        raw_statement="When HelpFormatter is initialized...",
        claim_type=ClaimType.BEHAVIORAL_CONTRACT,
        subject="HelpFormatter",
        predicate="satisfies_contract",
        object="",
        repository="click",
        symbol="HelpFormatter"
    )
    art = {
        "case_id": "MV21-000037",
        "repository": "click",
        "claim": "Completely different raw statement text here",
        "claim_subject": "HelpFormatter",
        "claim_predicate": "buffered text",
        "target_execution": {"passed": True, "contract_hash": "hash123"}
    }
    binding = binder.verify(claim, art)
    assert binding.binding_status == "FAILED"
    assert any("raw statement sha256 mismatch" in r for r in binding.binding_reasons)


def test_cat_b_missing_claim_predicate(binder):
    claim = MemoryClaim(
        claim_id="CLM-000037",
        raw_statement="When HelpFormatter is initialized...",
        claim_type=ClaimType.BEHAVIORAL_CONTRACT,
        subject="HelpFormatter",
        predicate="satisfies_contract",
        object="",
        repository="click",
        symbol="HelpFormatter"
    )
    art = {
        "case_id": "MV21-000037",
        "repository": "click",
        "claim_subject": "HelpFormatter",
        "target_execution": {"passed": True, "contract_hash": "hash123"}
    }
    binding = binder.verify(claim, art)
    assert binding.binding_status == "UNKNOWN"
    assert any("claim_predicate" in r for r in binding.binding_reasons)


def test_cat_b_mismatched_subject(binder):
    claim = MemoryClaim(
        claim_id="CLM-000037",
        raw_statement="When HelpFormatter is initialized...",
        claim_type=ClaimType.BEHAVIORAL_CONTRACT,
        subject="HelpFormatter",
        predicate="satisfies_contract",
        object="",
        repository="click",
        symbol="HelpFormatter"
    )
    art = {
        "case_id": "MV21-000037",
        "repository": "click",
        "claim_subject": "DifferentClass",
        "claim_predicate": "some predicate",
        "target_execution": {"passed": True, "contract_hash": "hash123"}
    }
    binding = binder.verify(claim, art)
    assert binding.binding_status == "FAILED"


def test_cat_c_verified_binding(binder):
    claim = MemoryClaim(
        claim_id="CLM-000045",
        raw_statement="HookSpec inspects hook functions via varnames",
        claim_type=ClaimType.DEPENDENCY_CONTRACT,
        subject="HookSpec",
        predicate="depends_on",
        object="varnames",
        repository="pluggy",
        symbol="HookSpec",
        source_case_id="MV21-000045"
    )
    art = {
        "case_id": "MV21-000045",
        "repository": "pluggy",
        "target_symbol": "HookSpec",
        "dependency_symbol": "varnames",
        "dependency_path": ["HookSpec", "varnames"],
        "old_on_target": {"passed": False, "contract_hash": "dep_hash456"}
    }
    binding = binder.verify(claim, art)
    assert binding.binding_status == "VERIFIED"
    assert binding.contract_hash == "dep_hash456"


def test_cat_c_missing_contract_hash(binder):
    claim = MemoryClaim(
        claim_id="CLM-000045",
        raw_statement="HookSpec inspects hook functions via varnames",
        claim_type=ClaimType.DEPENDENCY_CONTRACT,
        subject="HookSpec",
        predicate="depends_on",
        object="varnames",
        repository="pluggy",
        symbol="HookSpec"
    )
    art = {
        "case_id": "MV21-000045",
        "repository": "pluggy",
        "target_symbol": "HookSpec",
        "dependency_symbol": "varnames",
        "dependency_path": ["HookSpec", "varnames"],
        "old_on_target": {"passed": False}
    }
    binding = binder.verify(claim, art)
    assert binding.binding_status == "UNKNOWN"
    assert any("Missing contract_hash" in r for r in binding.binding_reasons)


def test_cat_c_mismatched_dependency_path(binder):
    claim = MemoryClaim(
        claim_id="CLM-000045",
        raw_statement="HookSpec inspects hook functions via varnames",
        claim_type=ClaimType.DEPENDENCY_CONTRACT,
        subject="HookSpec",
        predicate="depends_on",
        object="varnames",
        repository="pluggy",
        symbol="HookSpec"
    )
    art = {
        "case_id": "MV21-000045",
        "repository": "pluggy",
        "target_symbol": "HookSpec",
        "dependency_symbol": "varnames",
        "dependency_path": ["DifferentRoot", "other_helper"],
        "old_on_target": {"passed": False, "contract_hash": "dep_hash456"}
    }
    binding = binder.verify(claim, art)
    assert binding.binding_status == "FAILED"


def test_d2_unknown_binding(binder):
    claim = MemoryClaim(
        claim_id="CLM-000054",
        raw_statement="BaseHTTPResponse instances provide getheaders() method returning list of header tuples.",
        claim_type=ClaimType.ATTRIBUTE_EXISTS,
        subject="BaseHTTPResponse",
        predicate="has_attribute",
        object="getheaders",
        repository="urllib3",
        source_case_id="MV21-000054"
    )
    art = {
        "case_id": "MV21-000054",
        "repository": "urllib3",
        "break_verified": True,
        "base_execution": {"passed": True, "contract_hash": "d2_hash"},
        "target_execution": {"passed": False, "contract_hash": "d2_hash"}
    }
    binding = binder.verify(claim, art)
    assert binding.binding_status == "UNKNOWN"
    assert any("D2 artifact lacks deterministic assertion binding proof" in r for r in binding.binding_reasons)


def test_none_artifact(binder):
    claim = MemoryClaim(
        claim_id="CLM-01",
        raw_statement="Symbol foo exists",
        claim_type=ClaimType.SYMBOL_EXISTS,
        subject="foo",
        predicate="exists_in",
        object="app.py"
    )
    binding = binder.verify(claim, None)
    assert binding.binding_status == "UNKNOWN"
