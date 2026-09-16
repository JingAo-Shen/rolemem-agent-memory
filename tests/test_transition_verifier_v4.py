"""
tests/test_transition_verifier_v4.py
Unit tests for TransitionVerifierV4 and its strict 7-gate acceptance logic.
"""

import os
import json
import pytest
from src.transition_verifier_v4 import TransitionVerifierV4

SPECS_DIR = "/code/rolemem-agent-memory/data/specs"


@pytest.fixture
def verifier():
    return TransitionVerifierV4()


@pytest.fixture
def sample_spec():
    spec_path = os.path.join(SPECS_DIR, "trans_gold_werkzeug_01_cached_property.json")
    with open(spec_path, "r", encoding="utf-8") as f:
        return json.load(f)


def test_verifier_v4_accepts_valid_gold_spec(verifier, sample_spec):
    res = verifier.verify_candidate_v4(sample_spec)
    assert res["overall_status"] == "ACCEPT"
    assert res["gates"]["commit_verification"] == "PASS"
    assert res["gates"]["causality_status"] == "CAUSALITY_PASS"
    assert res["gates"]["original_test_verification"] == "PASS"
    assert res["gates"]["hidden_test_verification"] == "PASS"
    assert res["gates"]["fixture_control_verification"] == "PASS"
    assert res["gates"]["snapshot_hash_verification"] == "PASS"
    assert res["gates"]["metadata_ground_truth_verification"] == "PASS"


def test_verifier_v4_rejects_when_ground_truth_fails(verifier, sample_spec, monkeypatch):
    monkeypatch.setattr(
        verifier,
        "verify_ground_truth",
        lambda cand: {"external_ground_truth_status": "FAIL", "errors": ["Bogus PR"]}
    )
    res = verifier.verify_candidate_v4(sample_spec)
    assert res["overall_status"] == "REJECT"
    assert res["gates"]["metadata_ground_truth_verification"] == "FAIL"


def test_verifier_v4_rejects_when_original_test_fails(verifier, sample_spec, monkeypatch):
    monkeypatch.setattr(
        verifier,
        "verify_original_tests",
        lambda cand: {"status": "FAIL", "reason": "Missing original test file"}
    )
    res = verifier.verify_candidate_v4(sample_spec)
    assert res["overall_status"] == "REJECT"
    assert res["gates"]["original_test_passed_gate"] is False


def test_verifier_v4_allows_waived_original_test(verifier, sample_spec, monkeypatch):
    sample_spec["original_test_required"] = False
    monkeypatch.setattr(
        verifier,
        "verify_original_tests",
        lambda cand: {"status": "GENERATED_TEST_ONLY", "reason": "Waived in spec"}
    )
    res = verifier.verify_candidate_v4(sample_spec)
    assert res["overall_status"] == "ACCEPT"
    assert res["gates"]["original_test_passed_gate"] is True


def test_verifier_v4_rejects_when_snapshot_hash_fails(verifier, sample_spec, monkeypatch):
    monkeypatch.setattr(
        verifier,
        "verify_snapshot_hash",
        lambda cand: {"status": "FAIL", "reason": "Hash mismatch against git archive"}
    )
    res = verifier.verify_candidate_v4(sample_spec)
    assert res["overall_status"] == "REJECT"
    assert res["gates"]["snapshot_hash_verification"] == "FAIL"


def test_verifier_v4_rejects_when_causality_fails(verifier, sample_spec, monkeypatch):
    monkeypatch.setattr(
        verifier,
        "verify_declarative_causality",
        lambda cand: {"causality_status": "CAUSALITY_FAIL", "assertions": []}
    )
    res = verifier.verify_candidate_v4(sample_spec)
    assert res["overall_status"] == "REJECT"
    assert res["gates"]["causality_status"] == "CAUSALITY_FAIL"
