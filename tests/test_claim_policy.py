"""
tests/test_claim_policy.py

Unit tests for Decision Policies: SelectivePolicy, ForcedBinaryValidDefaultPolicy, ForcedBinaryStaleDefaultPolicy.
"""

import pytest
from src.claim_validity.types import (
    ClaimEvaluationResult,
    GroundingStatus,
    ValidationStatus
)
from src.claim_validity.policy import (
    SelectivePolicy,
    ForcedBinaryValidDefaultPolicy,
    ForcedBinaryStaleDefaultPolicy
)


def make_result(decision: str) -> ClaimEvaluationResult:
    return ClaimEvaluationResult(
        claim_id="CLM-001",
        decision=decision,
        grounding_status=GroundingStatus.EXACT,
        validation_status=ValidationStatus.SUPPORTED if decision == "VALID" else ValidationStatus.INSUFFICIENT_EVIDENCE,
        confidence=0.90 if decision != "UNCERTAIN" else 0.50
    )


def test_selective_policy():
    policy = SelectivePolicy()
    assert policy.decide(make_result("VALID")) == "VALID"
    assert policy.decide(make_result("STALE")) == "STALE"
    assert policy.decide(make_result("UNCERTAIN")) == "UNCERTAIN"


def test_forced_binary_valid_default_policy():
    policy = ForcedBinaryValidDefaultPolicy()
    assert policy.decide(make_result("VALID")) == "VALID"
    assert policy.decide(make_result("STALE")) == "STALE"
    assert policy.decide(make_result("UNCERTAIN")) == "VALID"


def test_forced_binary_stale_default_policy():
    policy = ForcedBinaryStaleDefaultPolicy()
    assert policy.decide(make_result("VALID")) == "VALID"
    assert policy.decide(make_result("STALE")) == "STALE"
    assert policy.decide(make_result("UNCERTAIN")) == "STALE"
