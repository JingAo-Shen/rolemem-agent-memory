"""
tests/test_transition_verifier_v3.py
Regression and unit tests for TransitionVerifierV3 (Pilot-v1.2c).
Explicitly verifies:
- collection fail -> not PASS
- test file missing -> not PASS
- hidden test fail -> not PASS
- stale control passes -> REJECT
- valid control fails -> REJECT
- declarative causality assertions without hardcoded transition_id logic
"""

import os
import json
import pytest
from src.transition_verifier_v3 import TransitionVerifierV3, inspect_symbol_in_code_ast


@pytest.fixture
def verifier():
    return TransitionVerifierV3()


def test_verifier_v3_accepts_valid_gold_spec(verifier):
    with open("data/specs/trans_gold_werkzeug_01_cached_property.json", "r") as f:
        spec = json.load(f)
    res = verifier.verify_candidate_v3(spec)
    assert res["overall_status"] == "ACCEPT"
    assert res["commit_verification"] == "PASS"
    assert res["causality_status"] == "CAUSALITY_PASS"
    assert res["fixture_control_verification"] == "PASS"
    assert res["hidden_test_verification"] == "PASS"
    assert res["snapshot_hash_verification"] == "PASS"


def test_collection_fail_is_not_pass(verifier):
    """Verifies that if pytest collection fails, status is NOT PASS."""
    candidate = {
        "transition_id": "test_invalid_collection",
        "repo_name": "pallets/werkzeug",
        "existing_tests": "tests/non_existent_folder/test_foo.py::test_bar"
    }
    res = verifier.verify_original_tests(candidate)
    assert res["status"] != "PASS"


def test_test_file_missing_is_not_pass(verifier):
    """Verifies that missing test file yields FAIL or MISSING_FILE."""
    candidate = {
        "transition_id": "test_missing_file",
        "repo_name": "pallets/werkzeug",
        "existing_tests": "tests/does_not_exist_xyz.py::test_xyz"
    }
    res = verifier.verify_original_tests(candidate)
    assert res["status"] == "FAIL"
    assert "not exist" in res["reason"].lower()


def test_hidden_test_fail_triggers_reject(verifier):
    """Verifies that missing or invalid hidden test fails verification."""
    candidate = {
        "transition_id": "non_existent_fixture_id",
        "repo_name": "pallets/werkzeug"
    }
    res = verifier.verify_hidden_tests(candidate)
    assert res["status"] == "FAIL"


def test_stale_control_passes_is_rejected(verifier, monkeypatch):
    """Verifies that if stale control incorrectly PASSES, candidate is REJECTED."""
    with open("data/specs/trans_gold_werkzeug_01_cached_property.json", "r") as f:
        spec = json.load(f)

    # Monkeypatch verify_fixture_controls to simulate stale passing
    monkeypatch.setattr(
        verifier,
        "verify_fixture_controls",
        lambda cand: {"status": "FAIL", "control_status": "FAIL_STALE_PASSED", "stale_pass": False, "valid_pass": True}
    )

    res = verifier.verify_candidate_v3(spec)
    assert res["overall_status"] == "REJECT"
    assert res["fixture_control_verification"] == "FAIL"


def test_valid_control_fails_is_rejected(verifier, monkeypatch):
    """Verifies that if valid control FAILS, candidate is REJECTED."""
    with open("data/specs/trans_gold_werkzeug_01_cached_property.json", "r") as f:
        spec = json.load(f)

    # Monkeypatch verify_fixture_controls to simulate valid failing
    monkeypatch.setattr(
        verifier,
        "verify_fixture_controls",
        lambda cand: {"status": "FAIL", "control_status": "FAIL_VALID_FAILED", "stale_pass": True, "valid_pass": False}
    )

    res = verifier.verify_candidate_v3(spec)
    assert res["overall_status"] == "REJECT"
    assert res["fixture_control_verification"] == "FAIL"


def test_declarative_causality_executes_without_hardcoded_tid(verifier):
    """Verifies that declarative causality assertions work for custom transition IDs."""
    custom_spec = {
        "transition_id": "trans_custom_arbitrary_id_123",
        "repo_name": "pallets/werkzeug",
        "base_commit": "25ca9cd92956e48a38f7a32c837e0f8a54c8ae31",
        "target_commit": "f50fbf5659875821c19ae21b237b4290b12e1e2d",
        "causality_assertions": [
            {
                "artifact": "src/werkzeug/utils.py",
                "symbol": "invalidate_cached_property",
                "base_state": "exists_active",
                "target_state": "deprecated_warn"
            }
        ]
    }
    res = verifier.verify_declarative_causality(custom_spec)
    assert res["causality_status"] == "CAUSALITY_PASS"
    assert len(res["assertions"]) == 1
    assert res["assertions"][0]["passed"] is True
