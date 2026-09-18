"""
src/transition_verifier_v7.py
TransitionVerifierV7: Final Eight-Gate Integrity Verifier with Cryptographic Fingerprints.

Enforces:
  Gate 1: Commit & Merge Ancestry Verification (gate1_commit_verification)
  Gate 2: Declarative AST & 2×2 Counterfactual Causality (gate2_causality_counterfactual)
  Gate 3: Test Evidence Relevance / Original Test Verification (gate3_original_test_verification)
  Gate 4: Hidden Test Collection & Execution Verification (gate4_hidden_test_verification)
  Gate 5: Fixture Control Differentiation Verification (gate5_fixture_control_verification)
  Gate 6: Snapshot Hash & Purity Verification (gate6_snapshot_hash_verification)
  Gate 7: Dual-Source External Ground Truth V3 Verification (gate7_external_ground_truth_v3)
  Gate 8: 10-Layer Semantic Coherence V2 Verification (gate8_semantic_coherence_v2)

Zero hardcoded PASS. Every gate reads machine evidence with unified audit_fingerprint validation.
Missing evidence -> NOT_EXECUTED -> REJECT/BLOCKED.
Stale evidence -> STALE_AUDIT -> REJECT/BLOCKED.
"""

import os
import sys
import json
import hashlib
import subprocess
from typing import Dict, Any, List, Optional, Tuple

sys.path.insert(0, "/code/rolemem-agent-memory")
from src.fingerprint import compute_unified_audit_fingerprint, REPO_DIR_MAP, DEFAULT_AUDITOR_VERSION

DATA_DIR = "/code/rolemem-agent-memory/data"
FIXTURES_DIR = "/code/rolemem-agent-memory/fixtures_v2"
CAUSAL_DIR = os.path.join(DATA_DIR, "causal_counterfactual")
TEST_EV_DIR = os.path.join(DATA_DIR, "test_evidence")
HIDDEN_EV_DIR = os.path.join(DATA_DIR, "hidden_test_evidence")
FIXTURE_CTRL_DIR = os.path.join(DATA_DIR, "fixture_controls")
SNAPSHOT_DIR = os.path.join(DATA_DIR, "snapshot_eval")
GROUND_TRUTH_V3_DIR = os.path.join(DATA_DIR, "ground_truth_audit_v3")
SEMANTIC_AUDIT_V2_DIR = os.path.join(DATA_DIR, "semantic_audit_v2")


class TransitionVerifierV7:
    """TransitionVerifier V7 with machine evidence checking and cryptographic cache protection."""

    def __init__(self, auditor_version: str = DEFAULT_AUDITOR_VERSION):
        self.auditor_version = auditor_version

    def compute_fingerprint(self, candidate: Dict[str, Any]) -> str:
        tid = candidate.get("transition_id", "")
        fixture_dir = os.path.join(FIXTURES_DIR, tid)
        return compute_unified_audit_fingerprint(candidate, fixture_dir=fixture_dir, auditor_version=self.auditor_version)

    def verify_commit_ancestry(self, candidate: Dict[str, Any]) -> str:
        repo_name = candidate.get("repo_name", "")
        repo_dir = REPO_DIR_MAP.get(repo_name)
        if not repo_dir or not os.path.exists(repo_dir):
            return "FAIL"

        base = candidate.get("base_commit", "")
        target = candidate.get("target_commit", "")
        if not base or not target:
            return "FAIL"

        try:
            subprocess.check_call(
                ["git", "-C", repo_dir, "cat-file", "-e", f"{base}^{{commit}}"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            subprocess.check_call(
                ["git", "-C", repo_dir, "cat-file", "-e", f"{target}^{{commit}}"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            ret = subprocess.call(
                ["git", "-C", repo_dir, "merge-base", "--is-ancestor", base, target],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            return "PASS" if ret == 0 else "FAIL"
        except Exception:
            return "FAIL"

    def verify_causality_matrix(self, candidate: Dict[str, Any], current_fp: str) -> Tuple[str, Optional[str]]:
        tid = candidate.get("transition_id", "")
        cf_file = os.path.join(CAUSAL_DIR, f"{tid}.json")

        if not os.path.exists(cf_file):
            return "NOT_EXECUTED", "COUNTERFACTUAL_EVIDENCE_MISSING"

        try:
            with open(cf_file, "r", encoding="utf-8") as f:
                cf_data = json.load(f)
            cached_fp = cf_data.get("audit_fingerprint")
            if cached_fp != current_fp:
                return "STALE_AUDIT", "COUNTERFACTUAL_FINGERPRINT_MISMATCH"

            status = cf_data.get("causality_status", "TRANSITION_NOT_CAUSAL")
            reason = cf_data.get("failure_reason") or cf_data.get("rationale")
            return ("PASS" if status == "CAUSAL_PASS" else "FAIL", reason)
        except Exception as e:
            return "FAIL", str(e)

    def verify_original_tests(self, candidate: Dict[str, Any], current_fp: str) -> Tuple[str, Dict[str, Any]]:
        tid = candidate.get("transition_id", "")
        ev_file = os.path.join(TEST_EV_DIR, f"{tid}.json")

        if not os.path.exists(ev_file):
            return "NOT_EXECUTED", {"error": "TEST_EVIDENCE_FILE_MISSING"}

        try:
            with open(ev_file, "r", encoding="utf-8") as f:
                ev_data = json.load(f)
            cached_fp = ev_data.get("audit_fingerprint")
            if cached_fp != current_fp:
                return "STALE_AUDIT", {"error": "TEST_EVIDENCE_FINGERPRINT_MISMATCH"}

            status = ev_data.get("status", "FAIL")
            return status, ev_data
        except Exception as e:
            return "FAIL", {"error": str(e)}

    def verify_hidden_test(self, candidate: Dict[str, Any], current_fp: str) -> Tuple[str, Dict[str, Any]]:
        tid = candidate.get("transition_id", "")
        hidden_file = os.path.join(FIXTURES_DIR, tid, "hidden_tests", "test_evaluation.py")
        if not os.path.exists(hidden_file):
            return "FAIL", {"error": "HIDDEN_TEST_FILE_MISSING"}

        ev_file = os.path.join(HIDDEN_EV_DIR, f"{tid}.json")
        if not os.path.exists(ev_file):
            return "NOT_EXECUTED", {"error": "HIDDEN_TEST_EVIDENCE_MISSING"}

        try:
            with open(ev_file, "r", encoding="utf-8") as f:
                ev_data = json.load(f)
            cached_fp = ev_data.get("audit_fingerprint")
            if cached_fp != current_fp:
                return "STALE_AUDIT", {"error": "HIDDEN_TEST_FINGERPRINT_MISMATCH"}

            status = ev_data.get("status", "FAIL")
            return status, ev_data
        except Exception as e:
            return "FAIL", {"error": str(e)}

    def verify_fixture_controls(self, candidate: Dict[str, Any], current_fp: str) -> Tuple[str, Dict[str, Any]]:
        tid = candidate.get("transition_id", "")
        ctrl_file = os.path.join(FIXTURE_CTRL_DIR, f"{tid}.json")
        if not os.path.exists(ctrl_file):
            return "NOT_EXECUTED", {"error": "FIXTURE_CTRL_EVIDENCE_MISSING"}

        try:
            with open(ctrl_file, "r", encoding="utf-8") as f:
                ctrl_data = json.load(f)
            cached_fp = ctrl_data.get("audit_fingerprint")
            if cached_fp != current_fp:
                return "STALE_AUDIT", {"error": "FIXTURE_CTRL_FINGERPRINT_MISMATCH"}

            status = ctrl_data.get("status", "FAIL")
            return status, ctrl_data
        except Exception as e:
            return "FAIL", {"error": str(e)}

    def verify_snapshot_hash(self, candidate: Dict[str, Any], current_fp: str) -> Tuple[str, Dict[str, Any]]:
        tid = candidate.get("transition_id", "")
        snap_file = os.path.join(SNAPSHOT_DIR, f"{tid}.json")
        if not os.path.exists(snap_file):
            return "NOT_EXECUTED", {"error": "SNAPSHOT_EVIDENCE_MISSING"}

        try:
            with open(snap_file, "r", encoding="utf-8") as f:
                snap_data = json.load(f)
            cached_fp = snap_data.get("audit_fingerprint")
            if cached_fp != current_fp:
                return "STALE_AUDIT", {"error": "SNAPSHOT_FINGERPRINT_MISMATCH"}

            # Also verify live files exist and haven't been mutated
            fixture_after = os.path.join(FIXTURES_DIR, tid, "after")
            repo_name = candidate.get("repo_name", "")
            target_commit = candidate.get("target_commit", "")
            repo_dir = REPO_DIR_MAP.get(repo_name)

            if os.path.isdir(fixture_after) and repo_dir and os.path.exists(repo_dir):
                for root, _, files in os.walk(fixture_after):
                    for fn in files:
                        fpath = os.path.join(root, fn)
                        rel = os.path.relpath(fpath, fixture_after)
                        with open(fpath, "rb") as f_in:
                            disk_sha = hashlib.sha256(f_in.read()).hexdigest()
                        git_res = subprocess.run(
                            ["git", "-C", repo_dir, "show", f"{target_commit}:{rel}"],
                            capture_output=True
                        )
                        if git_res.returncode == 0:
                            git_sha = hashlib.sha256(git_res.stdout).hexdigest()
                            if disk_sha != git_sha:
                                return "FAIL", {"error": f"Snapshot byte mismatch on {rel}"}

            status = snap_data.get("status", "FAIL")
            return status, snap_data
        except Exception as e:
            return "FAIL", {"error": str(e)}

    def verify_ground_truth_v3(self, candidate: Dict[str, Any], current_fp: str) -> Tuple[str, Dict[str, Any]]:
        tid = candidate.get("transition_id", "")
        audit_file = os.path.join(GROUND_TRUTH_V3_DIR, f"{tid}.json")

        if not os.path.exists(audit_file):
            return "NOT_EXECUTED", {"error": "GROUND_TRUTH_EVIDENCE_MISSING"}

        try:
            with open(audit_file, "r", encoding="utf-8") as f:
                cached = json.load(f)
            cached_fp = cached.get("audit_fingerprint")
            if cached_fp != current_fp:
                return "STALE_AUDIT", {"error": "GROUND_TRUTH_FINGERPRINT_MISMATCH"}
            return cached.get("overall_status", "FAIL"), cached
        except Exception as e:
            return "FAIL", {"error": str(e)}

    def verify_semantic_coherence_v2(self, candidate: Dict[str, Any], current_fp: str) -> Tuple[str, Dict[str, Any]]:
        tid = candidate.get("transition_id", "")
        sem_file = os.path.join(SEMANTIC_AUDIT_V2_DIR, f"{tid}.json")

        if not os.path.exists(sem_file):
            return "NOT_EXECUTED", {"error": "SEMANTIC_EVIDENCE_MISSING"}

        try:
            with open(sem_file, "r", encoding="utf-8") as f:
                cached = json.load(f)
            cached_fp = cached.get("audit_fingerprint")
            if cached_fp != current_fp:
                return "STALE_AUDIT", {"error": "SEMANTIC_FINGERPRINT_MISMATCH"}
            return cached.get("overall_status", "FAIL"), cached
        except Exception as e:
            return "FAIL", {"error": str(e)}

    def verify_candidate_v7(self, candidate: Dict[str, Any]) -> Dict[str, Any]:
        tid = candidate.get("transition_id", "")
        current_fp = self.compute_fingerprint(candidate)

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

        # Check for NOT_EXECUTED or STALE_AUDIT across any gate
        gate_statuses = list(gates.values())
        if any(s == "NOT_EXECUTED" for s in gate_statuses):
            seed_status = "BLOCKED"
            overall_status = "NOT_EXECUTED"
        elif any(s == "STALE_AUDIT" for s in gate_statuses):
            seed_status = "BLOCKED"
            overall_status = "STALE_AUDIT"
        elif commit_res != "PASS" or gt_status != "PASS" or sem_status != "PASS" or hidden_test_status != "PASS" or fixture_ctrl_status != "PASS" or snapshot_hash_status != "PASS" or (orig_test_status not in ["PASS", "GENERATED_HIDDEN_TEST_ONLY"]):
            seed_status = "REJECT"
            overall_status = "REJECT"
        elif causal_status != "PASS":
            seed_status = "REBUILD"
            overall_status = "REBUILD"
        else:
            seed_status = "SEED_ACCEPT"
            overall_status = "ACCEPT"

        return {
            "transition_id": tid,
            "seed_status": seed_status,
            "overall_status": overall_status,
            "repo_name": candidate.get("repo_name", ""),
            "track": candidate.get("track", "A"),
            "audit_fingerprint": current_fp,
            "gates": gates,
            "causality_status": "CAUSAL_PASS" if causal_status == "PASS" else "TRANSITION_NOT_CAUSAL",
            "causal_failure_reason": causal_reason,
        }
