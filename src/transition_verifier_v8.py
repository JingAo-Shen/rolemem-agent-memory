"""
src/transition_verifier_v8.py
TransitionVerifierV8: Decouples Integrity Verification from Benchmark Eligibility.

In V8:
1. integrity_status:
   - PASS: All 8 machine evidence gates pass (commit ancestry, causality, test relevance, hidden test, fixture control, snapshot hash, external ground truth v3, semantic coherence v2).
   - FAIL: Any machine evidence gate fails or contradicts reality.
   - NOT_EXECUTED / STALE_AUDIT: Missing or invalidated evidence cache.

2. benchmark_eligibility:
   - TRACK_A_ELIGIBLE: Integrity passes, task is valid and solvable with memory differentiation.
   - EXCLUDE_NOT_MEMORY_REQUIRED: Integrity passes, but task is solved identically without memory (e.g. flask_02).
   - EXCLUDE_TASK_TOO_HARD: Integrity passes, but task difficulty is prohibitive for evaluation (e.g. urllib3_02).
   - TRACK_B_ELIGIBLE: Integrity passes and satisfies Track B memory requirements.
   - REBUILD_OR_REPLACE: Integrity fails (e.g. flask_01) or fixture requires semantic reconstruction.
   - BLOCKED: Evidence missing or stale.
"""

import os
import sys
import json
from typing import Dict, Any, List, Optional, Tuple

sys.path.insert(0, "/code/rolemem-agent-memory")
from src.transition_verifier_v7 import TransitionVerifierV7
from src.fingerprint import DEFAULT_AUDITOR_VERSION

KNOWN_ELIGIBILITY_EXCLUSIONS = {
    "trans_gold_flask_02_should_ignore_error": "EXCLUDE_NOT_MEMORY_REQUIRED",
    "trans_gold_urllib3_02_empty_allowed_methods": "EXCLUDE_TASK_TOO_HARD",
}


class TransitionVerifierV8(TransitionVerifierV7):
    """TransitionVerifier V8 with explicit split of integrity status and benchmark eligibility."""

    def __init__(self, auditor_version: str = DEFAULT_AUDITOR_VERSION):
        super().__init__(auditor_version=auditor_version)

    def verify_candidate_v8(self, candidate: Dict[str, Any]) -> Dict[str, Any]:
        v7_res = self.verify_candidate_v7(candidate)
        tid = candidate.get("transition_id", "")
        gates = v7_res["gates"]

        gate_statuses = list(gates.values())
        
        # 1. Determine integrity_status
        if any(s == "NOT_EXECUTED" for s in gate_statuses):
            integrity_status = "NOT_EXECUTED"
        elif any(s == "STALE_AUDIT" for s in gate_statuses):
            integrity_status = "STALE_AUDIT"
        elif (
            gates["gate1_commit_verification"] == "PASS"
            and gates["gate2_causality_counterfactual"] == "PASS"
            and gates["gate3_original_test_verification"] in ["PASS", "GENERATED_HIDDEN_TEST_ONLY"]
            and gates["gate4_hidden_test_verification"] == "PASS"
            and gates["gate5_fixture_control_verification"] == "PASS"
            and gates["gate6_snapshot_hash_verification"] == "PASS"
            and gates["gate7_external_ground_truth_v3"] == "PASS"
            and gates["gate8_semantic_coherence_v2"] == "PASS"
        ):
            integrity_status = "PASS"
        else:
            integrity_status = "FAIL"

        # 2. Determine benchmark_eligibility
        if integrity_status in ["NOT_EXECUTED", "STALE_AUDIT"]:
            benchmark_eligibility = "BLOCKED"
        elif integrity_status == "FAIL":
            benchmark_eligibility = "REBUILD_OR_REPLACE"
        else:
            # Integrity is PASS
            if tid in KNOWN_ELIGIBILITY_EXCLUSIONS:
                benchmark_eligibility = KNOWN_ELIGIBILITY_EXCLUSIONS[tid]
            elif candidate.get("track") == "NOT_MEMORY_REQUIRED":
                benchmark_eligibility = "EXCLUDE_NOT_MEMORY_REQUIRED"
            elif candidate.get("track") == "TASK_TOO_HARD":
                benchmark_eligibility = "EXCLUDE_TASK_TOO_HARD"
            elif candidate.get("track") == "TRACK_B_UNLEAKED_DECISION":
                benchmark_eligibility = "TRACK_B_ELIGIBLE"
            else:
                benchmark_eligibility = "TRACK_A_ELIGIBLE"

        res = dict(v7_res)
        res["integrity_status"] = integrity_status
        res["benchmark_eligibility"] = benchmark_eligibility
        return res
