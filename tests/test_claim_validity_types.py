"""
tests/test_claim_validity_types.py

Unit tests for Protocol V2.2 Claim Types, Dataclasses, and Serialization Models.
"""

import json
import pytest
from src.claim_validity.types import (
    ClaimType,
    GroundingStatus,
    ValidationStatus,
    EvidenceType,
    MemoryClaim,
    GroundedClaim,
    ClaimEvidence,
    ClaimImpact,
    ClaimEvaluationResult
)


def test_claim_type_enum_coverage():
    expected_types = {
        "SYMBOL_EXISTS",
        "ATTRIBUTE_EXISTS",
        "IMPORT_PATH_VALID",
        "CALLABLE",
        "SIGNATURE_COMPATIBLE",
        "DEFAULT_VALUE",
        "RETURN_VALUE",
        "DEPRECATION_STATUS",
        "BEHAVIORAL_CONTRACT",
        "DEPENDENCY_CONTRACT",
        "UNKNOWN_CLAIM_TYPE"
    }
    actual_types = {ct.value for ct in ClaimType}
    assert expected_types.issubset(actual_types)


def test_memory_claim_serialization():
    claim = MemoryClaim(
        claim_id="CLM-000001",
        raw_statement="Symbol `foo` exists in `src/app.py`",
        claim_type=ClaimType.SYMBOL_EXISTS,
        subject="foo",
        predicate="exists_in",
        object="src/app.py",
        qualifiers={"extra": 123},
        repository="test-repo",
        file_path="src/app.py",
        symbol="foo",
        confidence=0.99,
        source_case_id="MV21-000001",
        claim_parse_status="PARSED"
    )
    d = claim.to_dict()
    assert d["claim_id"] == "CLM-000001"
    assert d["claim_type"] == "SYMBOL_EXISTS"
    assert d["claim_parse_status"] == "PARSED"

    rebuilt = MemoryClaim.from_dict(d)
    assert rebuilt.claim_id == claim.claim_id
    assert rebuilt.claim_type == ClaimType.SYMBOL_EXISTS
    assert rebuilt.qualifiers == {"extra": 123}


def test_claim_evidence_and_impact_serialization():
    ev = ClaimEvidence(
        evidence_type=EvidenceType.AST,
        source="target_ast",
        claim_id="CLM-000001",
        supports_or_contradicts="SUPPORTS",
        confidence=0.95,
        artifact_hash="abc123hash",
        detail="Symbol present in AST"
    )
    ev_dict = ev.to_dict()
    assert ev_dict["evidence_type"] == "AST"
    assert ClaimEvidence.from_dict(ev_dict).confidence == 0.95

    impact = ClaimImpact(
        direct_subject_changed=True,
        dependency_path_changed=False,
        signature_changed=True,
        impact_paths=[["foo", "bar"]]
    )
    imp_dict = impact.to_dict()
    assert imp_dict["direct_subject_changed"] is True
    assert ClaimImpact.from_dict(imp_dict).impact_paths == [["foo", "bar"]]


def test_claim_evaluation_result_serialization():
    res = ClaimEvaluationResult(
        claim_id="CLM-000001",
        decision="VALID",
        grounding_status=GroundingStatus.EXACT,
        validation_status=ValidationStatus.SUPPORTED,
        confidence=0.95,
        evidences=[
            ClaimEvidence(
                evidence_type=EvidenceType.AST,
                source="target_ast",
                claim_id="CLM-000001",
                supports_or_contradicts="SUPPORTS",
                confidence=0.95,
                artifact_hash="abc",
                detail="test"
            )
        ],
        reasons=["All assertions satisfied."]
    )
    r_dict = res.to_dict()
    rebuilt = ClaimEvaluationResult.from_dict(r_dict)
    assert rebuilt.decision == "VALID"
    assert rebuilt.grounding_status == GroundingStatus.EXACT
    assert len(rebuilt.evidences) == 1
