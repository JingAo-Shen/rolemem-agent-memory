import pytest
from src.memory_writer_evaluator_v3 import (
    validate_claim_attribution_v3,
    match_claims_bipartite_v3,
    evaluate_memory_writer_v3
)

def test_recall_and_precision_calculation():
    gold_claims = [
        {"claim_id": "g1", "symbol": "foo", "artifact_uri": "src/a.py", "gold_claim_status": "REQUIRED"},
        {"claim_id": "g2", "symbol": "bar", "artifact_uri": "src/b.py", "gold_claim_status": "REQUIRED"},
        {"claim_id": "g3", "symbol": "opt", "artifact_uri": "src/c.py", "gold_claim_status": "OPTIONAL_VALID"}
    ]
    gen_claims = [
        {"symbol": "foo", "artifact_uri": "src/a.py", "statement": "foo is deprecated"},
        {"symbol": "opt", "artifact_uri": "src/c.py", "statement": "opt is new"},
        {"symbol": "bogus", "artifact_uri": "src/z.py", "statement": "bogus info"}
    ]
    res = match_claims_bipartite_v3(gen_claims, gold_claims)
    # Matched required: foo (1/2) -> 0.5
    assert res["matched_required"] == 1
    assert res["total_required"] == 2
    assert res["required_recall"] == 0.5

    # Matched valid: foo (required) + opt (optional) = 2. Total generated = 3 -> 2/3
    assert res["matched_optional"] == 1
    assert res["valid_precision"] == pytest.approx(2/3, 0.01)

    # Optional discovery: opt matched (1/1) -> 1.0
    assert res["optional_discovery_rate"] == 1.0


def test_missing_commit_attribution():
    gold_spec = {
        "target_commit": "abc12345",
        "gold_claims": [{"symbol": "foo", "artifact_uri": "src/a.py"}]
    }
    claim_without_commit = {
        "symbol": "foo",
        "artifact_uri": "src/a.py",
        "statement": "foo is deprecated in favor of bar"
    }
    status, details = validate_claim_attribution_v3(claim_without_commit, gold_spec)
    assert status == "MISSING_COMMIT_ATTRIBUTION"
    assert details["missing_commit"] is True


def test_tightened_supported_status():
    gold_spec = {
        "target_commit": "abc12345",
        "gold_claims": [
            {"symbol": "old_fn", "artifact_uri": "src/a.py", "replacement_symbol": "new_fn"}
        ]
    }
    claim_full = {
        "evidence_commit": "abc12345",
        "symbol": "old_fn",
        "artifact_uri": "src/a.py",
        "statement": "old_fn is deprecated and replaced by new_fn"
    }
    diff = "--- a/src/a.py\n+++ b/src/a.py\n-def old_fn():\n+def new_fn():\n"
    status, details = validate_claim_attribution_v3(claim_full, gold_spec, pr_diff=diff)
    assert status == "SUPPORTED"

    # Missing replacement in statement -> should be PARTIAL
    claim_no_rep = {
        "evidence_commit": "abc12345",
        "symbol": "old_fn",
        "artifact_uri": "src/a.py",
        "statement": "old_fn is deprecated"
    }
    status_no_rep, details_no_rep = validate_claim_attribution_v3(claim_no_rep, gold_spec, pr_diff=diff)
    assert status_no_rep == "PARTIAL"
