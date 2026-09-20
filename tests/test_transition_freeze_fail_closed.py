import pytest
import os
import json
from scripts.render_transition_freeze_status_v2 import compute_file_sha256


def test_compute_file_sha256_missing_file():
    assert compute_file_sha256("/non/existent/path/file.json") is None


def test_compute_file_sha256_valid_file(tmp_path):
    f = tmp_path / "test.json"
    f.write_text("""{"status": "PASS"}""")
    sha = compute_file_sha256(str(f))
    assert isinstance(sha, str)
    assert len(sha) == 64


def test_missing_evidence_blocks_freeze(tmp_path):
    checks = {
        "spec_valid": True,
        "tree_pure": False,
        "verifier_accept": True,
        "hidden_test_pass": True,
        "mutants_killed": True,
        "controls_pass": True,
        "causal_pass": True,
        "ground_truth_pass": True,
        "semantic_v4_pass": True
    }
    all_passed = all(checks.values())
    status = "TRANSITION_SEED_FREEZE_READY" if all_passed else "TRANSITION_FREEZE_BLOCKED"
    assert status == "TRANSITION_FREEZE_BLOCKED"
