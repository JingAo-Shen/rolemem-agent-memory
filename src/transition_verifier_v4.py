"""
src/transition_verifier_v4.py
Transition Evidence Verifier v4 (Pilot-v1.2d).
Enforces the complete, uncompromised 7-part Seed Benchmark Acceptance Gate:
1. commit_verification == PASS
2. causality_status == CAUSALITY_PASS
3. original_test_verification == PASS (or explicitly waived via "original_test_required": false)
4. hidden_test_verification == PASS
5. fixture_control_verification == PASS (stale fails 100%, valid passes 100%)
6. snapshot_hash_verification == PASS (matches bare git archive digest)
7. metadata_ground_truth_verification == PASS (PR, issue, commits, and diff verified against Git)

All verifier outputs are written directly to data/verifier_results/<transition_id>.json.
"""

import os
import ast
import json
import hashlib
import subprocess
from typing import Dict, Any, List, Optional

from src.transition_verifier_v3 import TransitionVerifierV3, get_repo_dir
from scripts.audit_external_ground_truth import audit_spec as audit_external_ground_truth

VERIFIER_RESULTS_DIR = "/code/rolemem-agent-memory/data/verifier_results"
GROUND_TRUTH_AUDIT_DIR = "/code/rolemem-agent-memory/data/ground_truth_audit"
FIXTURES_DIR = os.getenv("ROLEMEM_FIXTURES_DIR", "/code/rolemem-agent-memory/fixtures_v2")


class TransitionVerifierV4(TransitionVerifierV3):
    """
    Pilot-v1.2d Transition Verifier.
    Integrates external ground-truth auditing and strict original-test gating into the ACCEPT decision.
    """

    def verify_ground_truth(self, candidate: Dict[str, Any]) -> Dict[str, Any]:
        """Loads pre-computed ground truth audit or executes audit dynamically."""
        tid = candidate.get("transition_id")
        audit_file = os.path.join(GROUND_TRUTH_AUDIT_DIR, f"{tid}.json")
        if os.path.exists(audit_file):
            with open(audit_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return audit_external_ground_truth(candidate)

    def verify_original_tests(self, candidate: Dict[str, Any]) -> Dict[str, Any]:
        """
        Verifies original tests from target_commit repository state:
        1. Checks that the test file exists in git at target_commit.
        2. Retrieves the test file via git show target_commit:rel_test_path.
        3. Parses AST to confirm syntactic validity and verifies that the requested test node exists.
        """
        repo_name = candidate.get("repo_name", "")
        repo_dir = get_repo_dir(repo_name)
        target_commit = candidate.get("target_commit", "")
        existing_test = candidate.get("existing_tests")

        if not existing_test:
            if not candidate.get("original_test_required", True):
                return {
                    "status": "GENERATED_TEST_ONLY",
                    "reason": "original_test_required is set to false in canonical spec"
                }
            return {
                "status": "FAIL",
                "reason": "No original test specified but original_test_required is true"
            }

        parts = existing_test.split("::")
        rel_test_file = parts[0]
        test_node = parts[1] if len(parts) > 1 else None

        if not repo_dir:
            return {
                "status": "FAIL",
                "reason": f"Local repository cache for {repo_name} not found"
            }

        # Check git cat-file for the target commit test file
        check_cmd = ["git", "-C", repo_dir, "cat-file", "-e", f"{target_commit}:{rel_test_file}"]
        res_cat = subprocess.run(check_cmd, capture_output=True)
        if res_cat.returncode != 0:
            return {
                "status": "FAIL",
                "reason": f"Original test file {rel_test_file} not found in git at target commit {target_commit}",
                "file_exists_in_git": False
            }

        # Retrieve file content from git target commit
        show_cmd = ["git", "-C", repo_dir, "show", f"{target_commit}:{rel_test_file}"]
        res_show = subprocess.run(show_cmd, capture_output=True, text=True)
        if res_show.returncode != 0:
            return {
                "status": "FAIL",
                "reason": f"Failed to read {rel_test_file} from git: {res_show.stderr[:200]}"
            }

        code = res_show.stdout
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return {
                "status": "FAIL",
                "reason": f"Syntax error in original test file at {target_commit}: {e}"
            }

        # Verify test node if specified
        if test_node:
            leaf_name = test_node.split("::")[-1]
            found_node = False
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == leaf_name:
                    found_node = True
                    break
                elif isinstance(node, ast.ClassDef) and node.name == leaf_name:
                    found_node = True
                    break

            if not found_node:
                return {
                    "status": "FAIL",
                    "reason": f"Test node '{leaf_name}' not defined in AST of {rel_test_file} at {target_commit}"
                }

        return {
            "status": "PASS",
            "rel_path": rel_test_file,
            "test_node": test_node,
            "target_commit": target_commit,
            "verified_in_git": True
        }

    def verify_candidate_v4(self, candidate: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes complete verification across all 7 rigorous tiers.
        """
        tid = candidate.get("transition_id")
        repo_name = candidate.get("repo_name")

        # 1. Commit Verification
        commits_to_check = ["base_commit", "history_commit", "transition_commit", "target_commit"]
        commit_res = {}
        all_commits_pass = True
        for c_role in commits_to_check:
            sha = candidate.get(c_role)
            c_check = self.verify_commit_local(repo_name, sha)
            commit_res[c_role] = c_check
            if not c_check.get("verified"):
                all_commits_pass = False
        commit_verification = "PASS" if all_commits_pass else "FAIL"

        # 2. Declarative AST Causality Verification
        causality_res = self.verify_declarative_causality(candidate)

        # 3. Original Test Verification
        orig_test_res = self.verify_original_tests(candidate)
        orig_test_required = candidate.get("original_test_required", True)
        if orig_test_required:
            orig_test_pass = (orig_test_res.get("status") == "PASS")
        else:
            orig_test_pass = (orig_test_res.get("status") in ["PASS", "GENERATED_TEST_ONLY"])

        # 4. Hidden Test Verification
        hidden_test_res = self.verify_hidden_tests(candidate)

        # 5. Fixture Control Verification (bwrap sandbox controls)
        control_res = self.verify_fixture_controls(candidate)

        # 6. Snapshot Hash Verification (git archive bitwise equality)
        snapshot_res = self.verify_snapshot_hash(candidate)

        # 7. Metadata External Ground Truth Verification
        ground_truth_res = self.verify_ground_truth(candidate)
        gt_status = ground_truth_res.get("external_ground_truth_status", "FAIL")

        # Full 7-Gate Acceptance Formula
        passes_all_gates = (
            commit_verification == "PASS"
            and causality_res.get("causality_status") == "CAUSALITY_PASS"
            and orig_test_pass
            and hidden_test_res.get("status") == "PASS"
            and control_res.get("status") == "PASS"
            and snapshot_res.get("status") == "PASS"
            and gt_status == "PASS"
        )

        overall_status = "ACCEPT" if passes_all_gates else "REJECT"

        result = {
            "transition_id": tid,
            "repo_name": repo_name,
            "track": candidate.get("track", "A"),
            "overall_status": overall_status,
            "gates": {
                "commit_verification": commit_verification,
                "causality_status": causality_res.get("causality_status"),
                "original_test_verification": orig_test_res.get("status"),
                "original_test_required": orig_test_required,
                "original_test_passed_gate": orig_test_pass,
                "hidden_test_verification": hidden_test_res.get("status"),
                "fixture_control_verification": control_res.get("status"),
                "snapshot_hash_verification": snapshot_res.get("status"),
                "metadata_ground_truth_verification": gt_status
            },
            "commit_details": commit_res,
            "causality_details": causality_res,
            "original_test_details": orig_test_res,
            "hidden_test_details": hidden_test_res,
            "control_details": control_res,
            "snapshot_details": snapshot_res,
            "ground_truth_details": ground_truth_res
        }

        # Persist raw verifier JSON
        os.makedirs(VERIFIER_RESULTS_DIR, exist_ok=True)
        out_path = os.path.join(VERIFIER_RESULTS_DIR, f"{tid}.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)

        return result
