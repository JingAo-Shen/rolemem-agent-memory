"""
Unit tests for TransitionVerifierV5 (8-Gate Verification Engine).
"""

import os
import json
import pytest
from src.transition_verifier_v5 import TransitionVerifierV5, AUDIT_V2_DIR


def test_verifier_v5_rejects_incoherent_spec(tmp_path):
    verifier = TransitionVerifierV5()
    # Mock spec where current_task mentions completely different symbol
    bad_spec = {
        "transition_id": "test_incoherent_transition",
        "repo_name": "pallets/click",
        "base_commit": "edcd2dc240f7f97ca5ef5b3c1f43c34234e2fee3",
        "transition_commit": "988c683963b14ced1b32a8cda9f9b466c32d9df1",
        "target_commit": "988c683963b14ced1b32a8cda9f9b466c32d9df1",
        "changed_files": ["src/click/parser.py"],
        "changed_symbols": ["OptionParser"],
        "deprecated_symbols": ["OptionParser"],
        "replacement_symbols": ["parse_args"],
        "target_file": "cli_helper.py",
        "target_symbol": "parse_command_args",
        "current_task": "Do something completely unrelated in another_file.py",
        "stale_memory_candidate": "stale memory candidate test string",
        "valid_memory_candidate": "valid memory candidate test string",
        "repository_change": "Deprecate OptionParser in favor of parse_args"
    }

    res = verifier.verify_candidate_v5(bad_spec)
    assert res["overall_status"] == "REJECT"
    assert res["gates"]["gate8_semantic_coherence_verification"] == "FAIL"


def test_verifier_v5_detects_stale_audit_cache():
    verifier = TransitionVerifierV5()
    tid = "test_stale_cache_transition"
    audit_file = os.path.join(AUDIT_V2_DIR, f"{tid}.json")
    os.makedirs(AUDIT_V2_DIR, exist_ok=True)

    # Pre-populate with stale hash
    with open(audit_file, "w", encoding="utf-8") as f:
        json.dump({
            "transition_id": tid,
            "spec_sha256": "outdated_hash_9999",
            "external_ground_truth_status": "PASS"
        }, f)

    candidate = {
        "transition_id": tid,
        "repo_name": "pallets/werkzeug",
        "pr_url": "https://github.com/pallets/werkzeug/pull/2084",
        "base_commit": "25ca9cd92956e48a38f7a32c837e0f8a54c8ae31",
        "target_commit": "f50fbf5659875821c19ae21b237b4290b12e1e2d",
        "changed_files": ["src/werkzeug/utils.py"],
        "changed_symbols": ["werkzeug.utils.invalidate_cached_property"],
        "deprecated_symbols": ["invalidate_cached_property"],
        "replacement_symbols": ["delattr"],
        "target_file": "property_helper.py",
        "target_symbol": "reset_cached_attribute",
        "current_task": "Implement reset_cached_attribute in property_helper.py",
        "stale_memory_candidate": "Use invalidate_cached_property to reset cached properties",
        "valid_memory_candidate": "Use delattr or del to reset cached properties",
        "repository_change": "Deprecate invalidate_cached_property in favor of del obj.prop"
    }

    gt_res = verifier.verify_ground_truth_v2(candidate)
    assert gt_res["source"] == "live_rerun"
    assert gt_res["details"]["spec_sha256"] != "outdated_hash_9999"

    # Second call without modifying candidate should hit cache
    gt_res2 = verifier.verify_ground_truth_v2(candidate)
    assert gt_res2["source"] == "cache_valid"

    # Clean up test artifact
    if os.path.exists(audit_file):
        os.remove(audit_file)
