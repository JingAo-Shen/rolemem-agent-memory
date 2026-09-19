"""
src/transition_verifier_v9.py
TransitionVerifierV9: Pure Machine Evidence Consumer for RoleMem.

Key Principles:
1. Zero Hardcoding: No hardcoded status, gates, or exclusion dictionaries.
2. Cryptographic Provenance: Every gate is validated against disk evidence
   bearing a valid, matching SHA-256 audit_fingerprint.
3. Decoupled Verdicts:
   - integrity_status: PASS | FAIL | NOT_EXECUTED | STALE_AUDIT
   - benchmark_eligibility: TRACK_A_PROVISIONAL_GOLD | TRACK_A_CONTROL_ELIGIBLE | TRACK_B_CANDIDATE | REBUILD_OR_REPLACE | BLOCKED
   - overall_status: ACCEPT | REJECT | BLOCKED
"""

import os
import sys
import json
from typing import Dict, Any, List, Optional, Tuple

sys.path.insert(0, "/code/rolemem-agent-memory")
from src.transition_verifier_v7 import TransitionVerifierV7, FIXTURES_DIR, DATA_DIR
from src.fingerprint import compute_unified_audit_fingerprint, DEFAULT_AUDITOR_VERSION


class TransitionVerifierV9(TransitionVerifierV7):
    """TransitionVerifier V9: Pure machine evidence consumer with cryptographic audit fingerprint validation."""

    def __init__(self, auditor_version: str = DEFAULT_AUDITOR_VERSION):
        super().__init__(auditor_version=auditor_version)

    def verify_candidate_v9(self, candidate: Dict[str, Any]) -> Dict[str, Any]:
        """Verify candidate strictly through machine evidence files and return structured verdict."""
        tid = candidate.get("transition_id", "")
        current_fp = self.compute_fingerprint(candidate)

        # 1. Evaluate 8 Machine Evidence Gates using inherited evidence consumers
        commit_res = self.verify_commit_ancestry(candidate)
        causal_status, causal_reason = self.verify_causality_matrix(candidate, current_fp)
        orig_test_status, orig_test_data = self.verify_original_tests(candidate, current_fp)
        hidden_test_status, hidden_test_data = self.verify_hidden_test(candidate, current_fp)
        fixture_ctrl_status, fixture_ctrl_data = self.verify_fixture_controls(candidate, current_fp)
        snapshot_hash_status, snapshot_hash_data = self.verify_snapshot_hash(candidate, current_fp)
        gt_status, gt_details = self.verify_ground_truth_v3(candidate, current_fp)
        sem_status, sem_details = self.verify_semantic_coherence_v2(candidate, current_fp)

        gates = {
            "gate1_commit_verification": commit_res,
            "gate2_causality_counterfactual": causal_status,
            "gate3_original_test_verification": orig_test_status,
            "gate4_hidden_test_verification": hidden_test_status,
            "gate5_fixture_control_verification": fixture_ctrl_status,
            "gate6_snapshot_hash_verification": snapshot_hash_status,
            "gate7_external_ground_truth_v3": gt_status,
            "gate8_semantic_coherence_v2": sem_status
        }

        gate_statuses = list(gates.values())

        # 2. Determine Integrity Status
        if any(s == "NOT_EXECUTED" for s in gate_statuses):
            integrity_status = "NOT_EXECUTED"
        elif any(s == "STALE_AUDIT" for s in gate_statuses):
            integrity_status = "STALE_AUDIT"
        elif (
            commit_res == "PASS"
            and causal_status == "PASS"
            and orig_test_status in ["PASS", "GENERATED_HIDDEN_TEST_ONLY"]
            and hidden_test_status == "PASS"
            and fixture_ctrl_status == "PASS"
            and snapshot_hash_status == "PASS"
            and gt_status == "PASS"
            and sem_status == "PASS"
        ):
            integrity_status = "PASS"
        else:
            integrity_status = "FAIL"

        # 3. Determine Benchmark Eligibility (Driven purely by metadata and integrity)
        stale_sensitive = candidate.get("stale_sensitive", True)
        track = candidate.get("track", "TRACK_A")

        if integrity_status in ["NOT_EXECUTED", "STALE_AUDIT"]:
            benchmark_eligibility = "BLOCKED"
            overall_status = "BLOCKED"
        elif integrity_status == "FAIL":
            benchmark_eligibility = "REBUILD_OR_REPLACE"
            overall_status = "REJECT"
        else:
            # Integrity is PASS
            overall_status = "ACCEPT"
            if "TRACK_B" in track:
                benchmark_eligibility = "TRACK_B_CANDIDATE"
            elif not stale_sensitive:
                benchmark_eligibility = "TRACK_A_CONTROL_ELIGIBLE"
            else:
                benchmark_eligibility = "TRACK_A_PROVISIONAL_GOLD"

        # 4. Evidence Manifest for Provenance
        evidence_manifest = {
            "causal_counterfactual": os.path.join(DATA_DIR, "causal_counterfactual", f"{tid}.json"),
            "hidden_test_evidence": os.path.join(DATA_DIR, "hidden_test_evidence", f"{tid}.json"),
            "fixture_controls": os.path.join(DATA_DIR, "fixture_controls", f"{tid}.json"),
            "snapshot_eval": os.path.join(DATA_DIR, "snapshot_eval", f"{tid}.json"),
            "ground_truth_audit_v3": os.path.join(DATA_DIR, "ground_truth_audit_v3", f"{tid}.json"),
            "semantic_audit_v2": os.path.join(DATA_DIR, "semantic_audit_v2", f"{tid}.json"),
        }

        return {
            "transition_id": tid,
            "repo_name": candidate.get("repo_name", ""),
            "auditor_version": self.auditor_version,
            "audit_fingerprint": current_fp,
            "integrity_status": integrity_status,
            "benchmark_eligibility": benchmark_eligibility,
            "overall_status": overall_status,
            "stale_sensitive": stale_sensitive,
            "track": track,
            "gates": gates,
            "causal_failure_reason": causal_reason,
            "evidence_manifest": evidence_manifest
        }


def main():
    import glob
    v9 = TransitionVerifierV9()
    specs = sorted(glob.glob("/code/rolemem-agent-memory/data/specs/trans_track_a_*.json"))
    print(f"=== TransitionVerifierV9 Evaluation ({len(specs)} transitions) ===")
    passed = 0
    for s in specs:
        with open(s, "r", encoding="utf-8") as f:
            cand = json.load(f)
        res = v9.verify_candidate_v9(cand)
        status = res["overall_status"]
        elig = res["benchmark_eligibility"]
        integ = res["integrity_status"]
        print(f"[{res["transition_id"]:45}] {status:6} | Integrity: {integ:4} | Eligibility: {elig}")
        if status == "ACCEPT":
            passed += 1

    print(f"\nVerifier V9 Result: {passed}/{len(specs)} ACCEPT\n")


if __name__ == "__main__":
    main()
