import pytest
from src.transition_verifier_v8 import TransitionVerifierV8

def test_v8_split_logic_pass_and_eligible():
    v8 = TransitionVerifierV8()
    candidate = {
        "transition_id": "mock_cand_01",
        "repo_name": "pallets/click",
        "track": "TRACK_A_API_EVOLUTION"
    }
    
    # Mock verify_candidate_v7 result
    mock_v7 = {
        "transition_id": "mock_cand_01",
        "seed_status": "SEED_ACCEPT",
        "overall_status": "ACCEPT",
        "gates": {
            "gate1_commit_verification": "PASS",
            "gate2_causality_counterfactual": "PASS",
            "gate3_original_test_verification": "PASS",
            "gate4_hidden_test_verification": "PASS",
            "gate5_fixture_control_verification": "PASS",
            "gate6_snapshot_hash_verification": "PASS",
            "gate7_external_ground_truth_v3": "PASS",
            "gate8_semantic_coherence_v2": "PASS"
        }
    }
    v8.verify_candidate_v7 = lambda cand: mock_v7
    res = v8.verify_candidate_v8(candidate)
    assert res["integrity_status"] == "PASS"
    assert res["benchmark_eligibility"] == "TRACK_A_ELIGIBLE"


def test_v8_split_logic_flask_02_not_memory_required():
    v8 = TransitionVerifierV8()
    candidate = {
        "transition_id": "trans_gold_flask_02_should_ignore_error",
        "repo_name": "pallets/flask",
        "track": "NOT_MEMORY_REQUIRED"
    }
    mock_v7 = {
        "transition_id": "trans_gold_flask_02_should_ignore_error",
        "seed_status": "SEED_ACCEPT",
        "overall_status": "ACCEPT",
        "gates": {
            "gate1_commit_verification": "PASS",
            "gate2_causality_counterfactual": "PASS",
            "gate3_original_test_verification": "GENERATED_HIDDEN_TEST_ONLY",
            "gate4_hidden_test_verification": "PASS",
            "gate5_fixture_control_verification": "PASS",
            "gate6_snapshot_hash_verification": "PASS",
            "gate7_external_ground_truth_v3": "PASS",
            "gate8_semantic_coherence_v2": "PASS"
        }
    }
    v8.verify_candidate_v7 = lambda cand: mock_v7
    res = v8.verify_candidate_v8(candidate)
    assert res["integrity_status"] == "PASS"
    assert res["benchmark_eligibility"] == "EXCLUDE_NOT_MEMORY_REQUIRED"


def test_v8_split_logic_urllib3_02_task_too_hard():
    v8 = TransitionVerifierV8()
    candidate = {
        "transition_id": "trans_gold_urllib3_02_empty_allowed_methods",
        "repo_name": "urllib3/urllib3",
        "track": "TASK_TOO_HARD"
    }
    mock_v7 = {
        "transition_id": "trans_gold_urllib3_02_empty_allowed_methods",
        "seed_status": "SEED_ACCEPT",
        "overall_status": "ACCEPT",
        "gates": {
            "gate1_commit_verification": "PASS",
            "gate2_causality_counterfactual": "PASS",
            "gate3_original_test_verification": "PASS",
            "gate4_hidden_test_verification": "PASS",
            "gate5_fixture_control_verification": "PASS",
            "gate6_snapshot_hash_verification": "PASS",
            "gate7_external_ground_truth_v3": "PASS",
            "gate8_semantic_coherence_v2": "PASS"
        }
    }
    v8.verify_candidate_v7 = lambda cand: mock_v7
    res = v8.verify_candidate_v8(candidate)
    assert res["integrity_status"] == "PASS"
    assert res["benchmark_eligibility"] == "EXCLUDE_TASK_TOO_HARD"


def test_v8_split_logic_flask_01_rebuild_or_replace():
    v8 = TransitionVerifierV8()
    candidate = {
        "transition_id": "trans_gold_flask_01_context_stack_removal",
        "repo_name": "pallets/flask",
        "track": "REBUILD"
    }
    mock_v7 = {
        "transition_id": "trans_gold_flask_01_context_stack_removal",
        "seed_status": "REJECT",
        "overall_status": "REJECT",
        "gates": {
            "gate1_commit_verification": "PASS",
            "gate2_causality_counterfactual": "FAIL",
            "gate3_original_test_verification": "GENERATED_HIDDEN_TEST_ONLY",
            "gate4_hidden_test_verification": "PASS",
            "gate5_fixture_control_verification": "PASS",
            "gate6_snapshot_hash_verification": "PASS",
            "gate7_external_ground_truth_v3": "PASS",
            "gate8_semantic_coherence_v2": "FAIL"
        }
    }
    v8.verify_candidate_v7 = lambda cand: mock_v7
    res = v8.verify_candidate_v8(candidate)
    assert res["integrity_status"] == "FAIL"
    assert res["benchmark_eligibility"] == "REBUILD_OR_REPLACE"
