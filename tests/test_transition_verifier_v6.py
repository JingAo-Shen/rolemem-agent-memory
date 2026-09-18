"""
Unit tests for TransitionVerifierV6.
"""

import os
import json
import pytest
from src.transition_verifier_v6 import TransitionVerifierV6


def test_verifier_v6_accepts_verified_candidate():
    verifier = TransitionVerifierV6()
    spec_path = "/code/rolemem-agent-memory/data/specs/trans_gold_werkzeug_01_cached_property.json"
    with open(spec_path) as f:
        spec = json.load(f)

    res = verifier.verify_candidate_v6(spec)
    assert res["seed_status"] == "SEED_ACCEPT"
    assert res["overall_status"] == "ACCEPT"
    assert res["gates"]["gate1_commit_verification"] == "PASS"
    assert res["gates"]["gate7_external_ground_truth_v3"] == "PASS"
    assert res["gates"]["gate8_semantic_coherence_v2"] == "PASS"


def test_verifier_v6_rebuilds_non_causal_candidate():
    verifier = TransitionVerifierV6()
    spec_path = "/code/rolemem-agent-memory/data/specs/trans_gold_flask_01_context_stack_removal.json"
    with open(spec_path) as f:
        spec = json.load(f)

    res = verifier.verify_candidate_v6(spec)
    assert res["seed_status"] == "REBUILD"
    assert res["causality_status"] == "TRANSITION_NOT_CAUSAL"


def test_verifier_v6_rejects_bogus_commit():
    verifier = TransitionVerifierV6()
    bogus_spec = {
        "transition_id": "test_bogus_commit",
        "repo_name": "pallets/werkzeug",
        "base_commit": "0000000000000000000000000000000000000000",
        "target_commit": "1111111111111111111111111111111111111111",
        "pr_url": "https://github.com/pallets/werkzeug/pull/999999",
        "changed_files": ["src/werkzeug/utils.py"]
    }
    res = verifier.verify_candidate_v6(bogus_spec)
    assert res["seed_status"] == "REJECT"
    assert res["gates"]["gate1_commit_verification"] == "FAIL"
