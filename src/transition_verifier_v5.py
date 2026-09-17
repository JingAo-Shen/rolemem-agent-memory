"""
TransitionVerifierV5: 8-Gate Scientific Benchmark Verifier.
Evaluates repository-state grounded transitions across 8 Boolean gates:
  Gate 1: Commit & Ancestry Verification (commit_verification)
  Gate 2: Declarative AST Causality Verification (causality_verification)
  Gate 3: Test Evidence Relevance Verification (test_evidence_verification)
  Gate 4: Hidden Test Collection Verification (hidden_test_verification)
  Gate 5: Fixture Control Differentiation Verification (fixture_control_verification)
  Gate 6: Snapshot Hash Integrity Verification (snapshot_hash_verification)
  Gate 7: Dual-Source External Ground Truth Verification (external_ground_truth_verification)
          * Strictly validates spec_sha256 match; invalidates stale cache!
  Gate 8: Semantic Coherence Verification (semantic_coherence_verification)
          * Validates 10-layer semantic coherence across PR, repo, task, tests, and controls.

Plus: 2×2 Causal Counterfactual Matrix Gate (causal_counterfactual_verification).
"""

import os
import sys
import json
import hashlib
import subprocess
from typing import Dict, Any, List, Optional

sys.path.insert(0, "/code/rolemem-agent-memory")
from src.transition_verifier_v3 import TransitionVerifierV3
from scripts.audit_external_ground_truth_v2 import audit_candidate_v2, compute_spec_sha256
from scripts.audit_semantic_coherence import audit_coherence

AUDIT_V2_DIR = "/code/rolemem-agent-memory/data/ground_truth_audit_v2"
SEMANTIC_AUDIT_DIR = "/code/rolemem-agent-memory/data/semantic_audit"
CAUSAL_DIR = "/code/rolemem-agent-memory/data/causal_counterfactual"


class TransitionVerifierV5(TransitionVerifierV3):
    """TransitionVerifier V5 enforcing 8-Gate boolean acceptance logic."""

    def __init__(self, github_token: Optional[str] = None):
        super().__init__()
        self.github_token = github_token

    def verify_ground_truth_v2(self, candidate: Dict[str, Any]) -> Dict[str, Any]:
        """
        Verifies external ground truth with strict spec_sha256 cache validation.
        If cached audit does not match current spec hash, re-runs audit.
        """
        tid = candidate.get("transition_id", "")
        current_hash = compute_spec_sha256(candidate)
        audit_file = os.path.join(AUDIT_V2_DIR, f"{tid}.json")

        if os.path.exists(audit_file):
            try:
                with open(audit_file, "r", encoding="utf-8") as f:
                    cached = json.load(f)
                if cached.get("spec_sha256") == current_hash:
                    # Cache is fresh
                    return {
                        "status": cached.get("external_ground_truth_status", "FAIL"),
                        "source": "cache_valid",
                        "details": cached
                    }
                else:
                    # Cache is stale
                    pass
            except Exception:
                pass

        # Run live dual-source audit
        live_res = audit_candidate_v2(candidate)
        os.makedirs(AUDIT_V2_DIR, exist_ok=True)
        with open(audit_file, "w", encoding="utf-8") as f:
            json.dump(live_res, f, indent=2)

        return {
            "status": live_res.get("external_ground_truth_status", "FAIL"),
            "source": "live_rerun",
            "details": live_res
        }

    def verify_semantic_coherence(self, candidate: Dict[str, Any]) -> Dict[str, Any]:
        """
        Verifies 10-layer semantic coherence across task, memory, fixture, and tests.
        """
        tid = candidate.get("transition_id", "")
        audit_file = os.path.join(SEMANTIC_AUDIT_DIR, f"{tid}.json")

        if os.path.exists(audit_file):
            try:
                with open(audit_file, "r", encoding="utf-8") as f:
                    cached = json.load(f)
                return {
                    "status": cached.get("overall_status", "FAIL"),
                    "details": cached
                }
            except Exception:
                pass

        live_res = audit_coherence(candidate)
        os.makedirs(SEMANTIC_AUDIT_DIR, exist_ok=True)
        with open(audit_file, "w", encoding="utf-8") as f:
            json.dump(live_res, f, indent=2)

        return {
            "status": live_res.get("overall_status", "FAIL"),
            "details": live_res
        }

    def verify_causal_counterfactual(self, candidate: Dict[str, Any]) -> Dict[str, Any]:
        """
        Checks 2×2 Causal Counterfactual Matrix result.
        """
        tid = candidate.get("transition_id", "")
        res_file = os.path.join(CAUSAL_DIR, f"{tid}.json")

        if os.path.exists(res_file):
            try:
                with open(res_file, "r", encoding="utf-8") as f:
                    cached = json.load(f)
                is_causal = cached.get("is_causal", False)
                return {
                    "status": "PASS" if is_causal else "FAIL",
                    "causality_status": cached.get("causality_status", "UNKNOWN"),
                    "matrix": cached.get("matrix", {}),
                    "rationale": cached.get("rationale", "")
                }
            except Exception:
                pass

        return {
            "status": "FAIL",
            "causality_status": "NOT_EXECUTED",
            "matrix": {},
            "rationale": "Causal counterfactual matrix not executed"
        }

    def verify_candidate_v5(self, candidate: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes full 8-Gate + Causal Counterfactual verification pipeline.
        """
        candidate = dict(candidate)
        tgt = candidate.get("target_commit", candidate.get("base_commit", ""))
        for c in ["base_commit", "history_commit", "transition_commit", "target_commit"]:
            if not candidate.get(c):
                candidate[c] = tgt

        tid = candidate.get("transition_id", "")
        fixture_dir = os.path.join("/code/rolemem-agent-memory/fixtures_v2", tid)

        # Baseline V3 checks
        base_v3 = self.verify_candidate_v3(candidate)

        # Gate 1: commit_verification
        g1_commit = base_v3.get("commit_verification", "FAIL")

        # Gate 2: causality_verification
        g2_causality = base_v3.get("causality_status", "FAIL")

        # Gate 3: test_evidence_verification
        gt_v2 = self.verify_ground_truth_v2(candidate)
        test_ev = gt_v2.get("details", {}).get("test_evidence", {})
        g3_test_evidence = test_ev.get("status", "FAIL")

        # Gate 4: hidden_test_verification
        g4_hidden_test = base_v3.get("hidden_test_verification", "FAIL")

        # Gate 5: fixture_control_verification
        g5_controls = base_v3.get("fixture_control_verification", "FAIL")

        # Gate 6: snapshot_hash_verification
        g6_snapshot = base_v3.get("snapshot_hash_verification", "FAIL")

        # Gate 7: external_ground_truth_v2
        g7_ground_truth = gt_v2.get("status", "FAIL")

        # Gate 8: semantic_coherence_verification
        coherence_res = self.verify_semantic_coherence(candidate)
        g8_coherence = coherence_res.get("status", "FAIL")

        # Additional: Causal Counterfactual Matrix
        causal_res = self.verify_causal_counterfactual(candidate)
        g_causal = causal_res.get("status", "FAIL")

        gates = {
            "gate1_commit_verification": g1_commit,
            "gate2_causality_verification": g2_causality,
            "gate3_test_evidence_verification": g3_test_evidence,
            "gate4_hidden_test_verification": g4_hidden_test,
            "gate5_fixture_control_verification": g5_controls,
            "gate6_snapshot_hash_verification": g6_snapshot,
            "gate7_external_ground_truth_v2": g7_ground_truth,
            "gate8_semantic_coherence_verification": g8_coherence,
            "causal_counterfactual_verification": g_causal
        }

        all_gates_pass = (
            g1_commit == "PASS" and
            g2_causality == "CAUSALITY_PASS" and
            g3_test_evidence == "PASS" and
            g4_hidden_test == "PASS" and
            g5_controls == "PASS" and
            g6_snapshot == "PASS" and
            g7_ground_truth == "PASS" and
            g8_coherence == "PASS" and
            g_causal == "PASS"
        )

        if all_gates_pass:
            overall_status = "ACCEPT"
        elif causal_res.get("causality_status") == "TRANSITION_NOT_CAUSAL":
            overall_status = "REBUILD"
        elif g7_ground_truth != "PASS" or g8_coherence != "PASS":
            overall_status = "REJECT"
        else:
            overall_status = "REJECT"

        result = {
            "transition_id": tid,
            "overall_status": overall_status,
            "gates": gates,
            "ground_truth_v2": gt_v2,
            "semantic_coherence": coherence_res,
            "causal_counterfactual": causal_res,
            "environment_verification": base_v3.get("environment_verification", "FAIL"),
            "spec_sha256": compute_spec_sha256(candidate)
        }

        return result
