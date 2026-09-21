"""
tests/test_claim_aware_engine.py

Unit tests for ClaimAwareValidityEngine end-to-end evaluation and fail-uncertain behavior.
"""

import pytest
from src.claim_validity.engine import ClaimAwareValidityEngine
from src.claim_validity.types import ClaimType, GroundingStatus, ValidationStatus


@pytest.fixture
def engine():
    return ClaimAwareValidityEngine()


def test_engine_valid_exact_claim(engine):
    src = "def process():\n    return 42\n"
    res = engine.evaluate(
        claim_or_statement="Symbol `process` defines core implementation in `app.py`",
        base_source=src,
        target_source=src,
        symbol_qualified_name="process",
        file_path="app.py"
    )
    assert res.decision == "VALID"
    assert res.grounding_status == GroundingStatus.EXACT
    assert res.validation_status == ValidationStatus.SUPPORTED


def test_engine_stale_deleted_claim(engine):
    base_src = "def process():\n    return 42\n"
    target_src = "def other():\n    return 100\n"
    diff = "--- a/app.py\n+++ b/app.py\n-def process():\n-    return 42\n+def other():\n+    return 100\n"

    res = engine.evaluate(
        claim_or_statement="Symbol `process` defines core implementation in `app.py`",
        base_source=base_src,
        target_source=target_src,
        diff_hunk=diff,
        symbol_qualified_name="process",
        file_path="app.py"
    )
    assert res.decision == "STALE"
    assert res.validation_status == ValidationStatus.CONTRADICTED


def test_engine_unresolved_claim_is_uncertain(engine):
    res = engine.evaluate(
        claim_or_statement="Some arbitrary sentence that cannot be parsed.",
        base_source="",
        target_source="",
        symbol_qualified_name="something",
        file_path="app.py"
    )
    assert res.decision == "UNCERTAIN"
    assert res.grounding_status == GroundingStatus.UNRESOLVED
    assert res.validation_status == ValidationStatus.INSUFFICIENT_EVIDENCE
