"""
tests/test_transition_verifier_v7.py
Rigorous mutation regression tests for TransitionVerifierV7:
- Standard seed verification: SEED_ACCEPT
- delete hidden test -> FAIL
- make stale control pass -> FAIL
- make valid control fail -> FAIL
- modify snapshot byte -> FAIL
- change spec after audit -> STALE_AUDIT
- delete evidence file -> NOT_EXECUTED
"""

import os
import sys
import copy
import json
import pytest
import tempfile
import shutil

sys.path.insert(0, "/code/rolemem-agent-memory")
from src.transition_verifier_v7 import TransitionVerifierV7


@pytest.fixture
def base_candidate():
    spec_path = "/code/rolemem-agent-memory/data/specs/trans_gold_click_01_option_parser.json"
    with open(spec_path, "r", encoding="utf-8") as f:
        return json.load(f)


def test_v7_standard_accept(base_candidate):
    verifier = TransitionVerifierV7()
    res = verifier.verify_candidate_v7(base_candidate)
    assert res["seed_status"] == "SEED_ACCEPT"
    assert res["overall_status"] == "ACCEPT"
    assert res["gates"]["gate1_commit_verification"] == "PASS"
    assert res["gates"]["gate2_causality_counterfactual"] == "PASS"
    assert res["gates"]["gate3_original_test_verification"] == "PASS"
    assert res["gates"]["gate4_hidden_test_verification"] == "PASS"
    assert res["gates"]["gate5_fixture_control_verification"] == "PASS"
    assert res["gates"]["gate6_snapshot_hash_verification"] == "PASS"
    assert res["gates"]["gate7_external_ground_truth_v3"] == "PASS"
    assert res["gates"]["gate8_semantic_coherence_v2"] == "PASS"


def test_v7_mutation_delete_hidden_test(base_candidate, monkeypatch):
    tid = base_candidate["transition_id"]
    verifier = TransitionVerifierV7()
    hidden_file = f"/code/rolemem-agent-memory/fixtures_v2/{tid}/hidden_tests/test_evaluation.py"

    orig_exists = os.path.exists
    def mock_exists(p):
        if p == hidden_file:
            return False
        return orig_exists(p)

    monkeypatch.setattr(os.path, "exists", mock_exists)
    res = verifier.verify_candidate_v7(base_candidate)
    assert res["gates"]["gate4_hidden_test_verification"] == "FAIL"
    assert res["overall_status"] in ["REJECT", "STALE_AUDIT"]


def test_v7_mutation_stale_control_pass(base_candidate, monkeypatch):
    tid = base_candidate["transition_id"]
    verifier = TransitionVerifierV7()
    current_fp = verifier.compute_fingerprint(base_candidate)
    ctrl_file = f"/code/rolemem-agent-memory/data/fixture_controls/{tid}.json"

    orig_open = open
    def mock_open(fpath, *args, **kwargs):
        if fpath == ctrl_file and "r" in args[0] if args else kwargs.get("mode", "r"):
            mock_data = {
                "transition_id": tid,
                "stale_pass": True,
                "valid_pass": True,
                "status": "FAIL_STALE_PASSED",
                "audit_fingerprint": current_fp,
                "auditor_version": "v7.0"
            }
            return tempfile.SpooledTemporaryFile(max_size=10000) # or StringIO
        return orig_open(fpath, *args, **kwargs)

    # Use monkeypatch on json.load when reading ctrl_file
    orig_json_load = json.load
    def mock_json_load(fp):
        name = getattr(fp, "name", "")
        if "fixture_controls" in name:
            return {
                "transition_id": tid,
                "stale_pass": True,
                "valid_pass": True,
                "status": "FAIL_STALE_PASSED",
                "audit_fingerprint": current_fp,
                "auditor_version": "v7.0"
            }
        return orig_json_load(fp)

    monkeypatch.setattr(json, "load", mock_json_load)
    res = verifier.verify_candidate_v7(base_candidate)
    assert res["gates"]["gate5_fixture_control_verification"] == "FAIL_STALE_PASSED"
    assert res["overall_status"] in ["REJECT", "STALE_AUDIT"]


def test_v7_mutation_valid_control_fail(base_candidate, monkeypatch):
    tid = base_candidate["transition_id"]
    verifier = TransitionVerifierV7()
    current_fp = verifier.compute_fingerprint(base_candidate)

    orig_json_load = json.load
    def mock_json_load(fp):
        name = getattr(fp, "name", "")
        if "fixture_controls" in name:
            return {
                "transition_id": tid,
                "stale_pass": False,
                "valid_pass": False,
                "status": "FAIL_VALID_FAILED",
                "audit_fingerprint": current_fp,
                "auditor_version": "v7.0"
            }
        return orig_json_load(fp)

    monkeypatch.setattr(json, "load", mock_json_load)
    res = verifier.verify_candidate_v7(base_candidate)
    assert res["gates"]["gate5_fixture_control_verification"] == "FAIL_VALID_FAILED"
    assert res["overall_status"] in ["REJECT", "STALE_AUDIT"]


def test_v7_mutation_modify_snapshot_byte(base_candidate, monkeypatch):
    verifier = TransitionVerifierV7()
    orig_sha256 = os.path.exists

    # We mock live snapshot verification by returning corrupted disk content
    orig_open = open
    def mock_open(fpath, mode="r", *args, **kwargs):
        if "after" in fpath and "rb" in mode:
            # Corrupted byte
            import io
            return io.BytesIO(b"corrupted_snapshot_byte_content")
        return orig_open(fpath, mode, *args, **kwargs)

    monkeypatch.setattr("builtins.open", mock_open)
    res = verifier.verify_candidate_v7(base_candidate)
    assert res["gates"]["gate6_snapshot_hash_verification"] == "FAIL"
    assert res["overall_status"] in ["REJECT", "STALE_AUDIT"]


def test_v7_mutation_change_spec_after_audit(base_candidate):
    verifier = TransitionVerifierV7()
    # Mutate spec (e.g. change a description, commit, or requirement)
    mutated = copy.deepcopy(base_candidate)
    mutated["pr_title"] = "MUTATED_AFTER_AUDIT"

    res = verifier.verify_candidate_v7(mutated)
    # The current fingerprint will not match the cached audit fingerprint!
    gate_values = list(res["gates"].values())
    assert "STALE_AUDIT" in gate_values
    assert res["overall_status"] == "STALE_AUDIT"
    assert res["seed_status"] == "BLOCKED"


def test_v7_mutation_delete_evidence_file(base_candidate, monkeypatch):
    tid = base_candidate["transition_id"]
    verifier = TransitionVerifierV7()
    cf_file = f"/code/rolemem-agent-memory/data/causal_counterfactual/{tid}.json"

    orig_exists = os.path.exists
    def mock_exists(p):
        if p == cf_file:
            return False
        return orig_exists(p)

    monkeypatch.setattr(os.path, "exists", mock_exists)
    res = verifier.verify_candidate_v7(base_candidate)
    assert res["gates"]["gate2_causality_counterfactual"] == "NOT_EXECUTED"
    assert res["overall_status"] == "NOT_EXECUTED"
    assert res["seed_status"] == "BLOCKED"
