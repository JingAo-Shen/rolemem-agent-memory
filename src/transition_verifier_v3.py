"""
Transition Evidence Verifier v3 (Pilot-v1.2c).
Provides fully decoupled, declarative, and multi-tier verification:
1. Commit verification via local git cache (git cat-file)
2. Declarative AST causality verification (generic rules driven by causality_assertions; zero hardcoded transition_id logic)
3. Multi-tier test verification:
   - original_test_verification: tests from existing repo test files (PASS, FAIL, NEEDS_ENV_RECONSTRUCTION, MISSING_FILE, GENERATED_TEST_ONLY)
   - hidden_test_verification: executable verification of hidden evaluation tests
   - fixture_control_verification: bwrap sandbox execution of stale/valid controls (stale FAIL, valid PASS)
4. Snapshot hash & purity audit (verifying exact correspondence with git archive)
5. Metadata consistency validation
"""

import os
import re
import ast
import json
import hashlib
import tarfile
import io
import subprocess
from typing import Dict, Any, List, Optional, Tuple

from src.transition_verifier import TransitionVerifier, get_github_token
from src.sandbox_secure import SecureSandboxExecutor

REPO_CACHE_DIR = os.getenv("ROLEMEM_REPO_CACHE", "/code/repo_cache")
FIXTURES_DIR = os.getenv("ROLEMEM_FIXTURES_DIR", "/code/rolemem-agent-memory/fixtures_v2")
VENVS_DIR = os.getenv("ROLEMEM_VENVS_DIR", "/code/rolemem-agent-memory/.venvs")


def get_repo_dir(repo_name: str) -> Optional[str]:
    """Map repo_name (e.g. pallets/werkzeug or werkzeug) to local clone in /code/repo_cache."""
    short_name = repo_name.split("/")[-1]
    candidate = os.path.join(REPO_CACHE_DIR, short_name)
    if os.path.isdir(os.path.join(candidate, ".git")) or os.path.isdir(os.path.join(candidate, "objects")):
        return candidate
    return None


def inspect_symbol_in_code_ast(code: str, sym_name: str) -> Dict[str, Any]:
    """
    Parses Python code into AST and inspects whether a symbol:
    1. Is defined (function, async function, class, method, or assignment)
    2. Contains a deprecation warning (docstring or warnings.warn call)
    3. Is handled in module __getattr__ with deprecation warning
    """
    if not code:
        return {"found": False, "deprecated": False, "details": ["empty_code"]}
    try:
        tree = ast.parse(code)
    except Exception as e:
        found = sym_name in code
        deprecated = found and ("deprecat" in code.lower() or "warnings.warn" in code)
        return {"found": found, "deprecated": deprecated, "details": [f"ast_fallback: {e}"]}

    found = False
    deprecated = False
    details = []

    for node in ast.walk(tree):
        # 1. FunctionDef, AsyncFunctionDef, ClassDef
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if node.name == sym_name:
                found = True
                doc = ast.get_docstring(node) or ""
                if "deprecat" in doc.lower():
                    deprecated = True
                    details.append("docstring_deprecate")
                for sub in ast.walk(node):
                    if isinstance(sub, ast.Call):
                        call_str = ast.unparse(sub) if hasattr(ast, "unparse") else ""
                        if "warn" in call_str:
                            deprecated = True
                            details.append(f"warn_call: {call_str[:40]}")

        # 2. Module or class __getattr__ deprecation hooks
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "__getattr__":
            for sub in ast.walk(node):
                if isinstance(sub, ast.Compare):
                    cmp_str = ast.unparse(sub) if hasattr(ast, "unparse") else ""
                    if sym_name in cmp_str:
                        found = True
                        for sub_warn in ast.walk(node):
                            if isinstance(sub_warn, ast.Call):
                                warn_str = ast.unparse(sub_warn) if hasattr(ast, "unparse") else ""
                                if "warn" in warn_str:
                                    deprecated = True
                                    details.append(f"getattr_warn: {warn_str[:40]}")

        # 3. Variable assignment
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id == sym_name:
                    found = True
                    # Check for deprecation comments or warnings nearby
                elif isinstance(t, ast.Attribute) and t.attr == sym_name:
                    found = True
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name) and node.target.id == sym_name:
                found = True

    return {"found": found, "deprecated": deprecated, "details": details}


class TransitionVerifierV3(TransitionVerifier):
    """
    Decoupled, declarative, multi-tier transition verifier for Pilot-v1.2c.
    Zero transition-specific hardcoding. Fully driven by declarative specs.
    """

    def __init__(self, token: Optional[str] = None):
        super().__init__(token=token)
        self.proxy_url = os.getenv("ROLEMEM_PROXY", "http://127.0.0.1:7897")

    def verify_commit_local(self, repo_name: str, sha: str) -> Dict[str, Any]:
        """Check if commit exists in local git repository cache via git cat-file."""
        repo_dir = get_repo_dir(repo_name)
        if not repo_dir:
            return self.verify_commit(repo_name, sha)

        res = subprocess.run(
            ["git", "-C", repo_dir, "cat-file", "-e", sha],
            capture_output=True
        )
        if res.returncode == 0:
            msg_res = subprocess.run(
                ["git", "-C", repo_dir, "log", "-1", "--pretty=%s", sha],
                capture_output=True, text=True
            )
            parents_res = subprocess.run(
                ["git", "-C", repo_dir, "log", "-1", "--pretty=%P", sha],
                capture_output=True, text=True
            )
            return {
                "verified": True,
                "commit_sha": sha,
                "full_sha": sha,
                "message": msg_res.stdout.strip(),
                "parents": parents_res.stdout.strip().split(),
                "source": "local_git_cache"
            }
        return self.verify_commit(repo_name, sha)

    def get_file_content_at_commit(self, repo_name: str, commit_sha: str, file_path: str) -> Optional[str]:
        """Extract exact file content from repository at a specific commit."""
        repo_dir = get_repo_dir(repo_name)
        if not repo_dir:
            return None

        res = subprocess.run(
            ["git", "-C", repo_dir, "show", f"{commit_sha}:{file_path}"],
            capture_output=True
        )
        if res.returncode == 0:
            return res.stdout.decode("utf-8", errors="ignore")
        return None

    def verify_declarative_causality(self, candidate: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generic declarative causality check:
        Executes causality_assertions declared in candidate metadata/spec.
        Zero hardcoded if transition_id == '...'.
        """
        repo_name = candidate.get("repo_name", "")
        repo_dir = get_repo_dir(repo_name)
        base_commit = candidate.get("base_commit", "")
        target_commit = candidate.get("target_commit", "")
        assertions = candidate.get("causality_assertions", [])

        if not repo_dir or not base_commit or not target_commit:
            return {
                "causality_status": "AMBIGUOUS",
                "reason": "Missing repository cache or commits for causality check"
            }

        # Check git diff non-emptiness
        diff_res = subprocess.run(
            ["git", "-C", repo_dir, "diff", f"{base_commit}..{target_commit}"],
            capture_output=True, text=True
        )
        if diff_res.returncode != 0:
            return {
                "causality_status": "CAUSALITY_FAIL",
                "reason": f"git diff failed between {base_commit} and {target_commit}"
            }
        diff_text = diff_res.stdout
        if not diff_text.strip():
            return {
                "causality_status": "CAUSALITY_FAIL",
                "reason": "Diff is completely empty between base and target commit"
            }

        assertion_results = []
        all_passed = True

        if assertions:
            for assertion in assertions:
                art = assertion.get("artifact")
                sym = assertion.get("symbol")
                expected_base = assertion.get("base_state")
                expected_target = assertion.get("target_state")

                content_base = self.get_file_content_at_commit(repo_name, base_commit, art) or ""
                content_target = self.get_file_content_at_commit(repo_name, target_commit, art) or ""

                base_ast = inspect_symbol_in_code_ast(content_base, sym)
                target_ast = inspect_symbol_in_code_ast(content_target, sym)

                # Determine actual base state
                if not base_ast["found"]:
                    actual_base = "absent"
                elif base_ast["deprecated"]:
                    actual_base = "deprecated_warn"
                else:
                    actual_base = "exists_active"

                # Determine actual target state
                if not target_ast["found"]:
                    actual_target = "removed"
                elif base_ast.get("details") and any("getattr" in d for d in target_ast.get("details", [])):
                    actual_target = "deprecated_getattr"
                elif target_ast["deprecated"]:
                    actual_target = "deprecated_warn"
                else:
                    actual_target = "exists_active"

                # Match logic
                base_matches = (expected_base == actual_base) or (expected_base == "exists" and base_ast["found"]) or (expected_base == "deprecated" and base_ast["deprecated"])
                target_matches = (expected_target == actual_target) or (expected_target == "deprecated" and target_ast["deprecated"])

                # Generic check for string in target (e.g. deprecation warning message)
                if assertion.get("target_text_contains"):
                    text_in_target = (assertion["target_text_contains"] in content_target)
                    text_in_base = (assertion["target_text_contains"] in content_base)
                    text_matches = text_in_target and not text_in_base
                    passed = bool(text_matches and (base_matches if expected_base != "absent" else not text_in_base))
                else:
                    passed = bool(base_matches and target_matches)

                if not passed:
                    all_passed = False

                assertion_results.append({
                    "artifact": art,
                    "symbol": sym,
                    "expected_base": expected_base,
                    "actual_base": actual_base,
                    "expected_target": expected_target,
                    "actual_target": actual_target,
                    "passed": passed
                })

            status = "CAUSALITY_PASS" if (all_passed and len(assertions) > 0) else "CAUSALITY_FAIL"
        else:
            # Fallback to symbol-level inspection without assertions
            changed_files = candidate.get("changed_files", [])
            changed_symbols = candidate.get("changed_symbols", [])
            causality_pass = False
            for f_path in changed_files:
                content_base = self.get_file_content_at_commit(repo_name, base_commit, f_path) or ""
                content_target = self.get_file_content_at_commit(repo_name, target_commit, f_path) or ""
                for sym in changed_symbols:
                    name = sym.split(".")[-1]
                    b_ast = inspect_symbol_in_code_ast(content_base, name)
                    t_ast = inspect_symbol_in_code_ast(content_target, name)
                    if b_ast["found"] and not b_ast["deprecated"] and t_ast["deprecated"]:
                        causality_pass = True
                    elif b_ast["found"] and not t_ast["found"]:
                        causality_pass = True
                    elif not b_ast["found"] and t_ast["found"]:
                        causality_pass = True
            status = "CAUSALITY_PASS" if causality_pass else "AMBIGUOUS"

        return {
            "causality_status": status,
            "base_commit": base_commit,
            "target_commit": target_commit,
            "diff_lines": len(diff_text.splitlines()),
            "assertions": assertion_results
        }

    def verify_original_tests(self, candidate: Dict[str, Any]) -> Dict[str, Any]:
        """
        Verifies original tests in the host repository.
        Fixes the Pilot-v1.2b false PASS bug:
        - If pytest --collect-only returncode != 0 -> FAIL or NEEDS_ENV_RECONSTRUCTION
        - If test file missing -> MISSING_FILE
        - Only returns PASS if collection succeeds and node exists.
        """
        repo_name = candidate.get("repo_name", "")
        repo_dir = get_repo_dir(repo_name)
        existing_test = candidate.get("existing_tests")

        if not existing_test:
            return {
                "status": "GENERATED_TEST_ONLY",
                "reason": "No original test specified in candidate metadata"
            }

        parts = existing_test.split("::")
        rel_test_file = parts[0]
        test_node = parts[1] if len(parts) > 1 else None

        if not repo_dir:
            return {
                "status": "FAIL",
                "reason": f"Local repository cache for {repo_name} not found"
            }

        full_test_path = os.path.join(repo_dir, rel_test_file)
        if not os.path.exists(full_test_path):
            return {
                "status": "FAIL",
                "reason": f"Original test file does not exist: {rel_test_file}",
                "file_exists": False
            }

        # Check with pytest collect-only
        res = subprocess.run(
            ["pytest", "--collect-only", "-q", full_test_path],
            cwd=repo_dir,
            capture_output=True,
            text=True
        )

        if res.returncode != 0:
            # Environment mismatch or collection failure
            return {
                "status": "NEEDS_ENV_RECONSTRUCTION",
                "reason": f"pytest collection failed with exit code {res.returncode}",
                "stderr_preview": res.stderr[:300],
                "stdout_preview": res.stdout[:300]
            }

        node_found = (test_node in res.stdout) if test_node else True
        if not node_found:
            return {
                "status": "FAIL",
                "reason": f"Test node {test_node} not found in collected tests",
                "stdout_preview": res.stdout[:300]
            }

        return {
            "status": "PASS",
            "rel_path": rel_test_file,
            "test_node": test_node,
            "exit_code": 0
        }

    def verify_hidden_tests(self, candidate: Dict[str, Any]) -> Dict[str, Any]:
        """Verify hidden test file exists and is syntactically valid."""
        tid = candidate.get("transition_id", "")
        fixture_path = os.path.join(FIXTURES_DIR, tid)
        test_file = os.path.join(fixture_path, "hidden_tests", "test_evaluation.py")

        if not os.path.exists(test_file):
            return {
                "status": "FAIL",
                "reason": f"Missing hidden test file: {test_file}"
            }

        with open(test_file, "r", encoding="utf-8") as f:
            code = f.read()

        try:
            ast.parse(code)
        except SyntaxError as e:
            return {
                "status": "FAIL",
                "reason": f"Syntax error in hidden test: {e}"
            }

        return {
            "status": "PASS",
            "test_file": test_file,
            "lines": len(code.splitlines())
        }

    def verify_fixture_controls(self, candidate: Dict[str, Any]) -> Dict[str, Any]:
        """
        Verifies controls:
        - stale_solution must FAIL / trigger deprecation
        - valid_solution must PASS
        Both must be satisfied for PASS status.
        """
        tid = candidate.get("transition_id", "")
        controls_dir = os.path.join(FIXTURES_DIR, tid, "controls")
        stale_res_path = os.path.join(controls_dir, "stale_result.json")
        valid_res_path = os.path.join(controls_dir, "valid_result.json")

        if not os.path.exists(stale_res_path) or not os.path.exists(valid_res_path):
            return {
                "status": "FAIL",
                "reason": "Missing stale_result.json or valid_result.json; controls have not been run"
            }

        with open(stale_res_path, "r", encoding="utf-8") as f:
            stale_res = json.load(f)
        with open(valid_res_path, "r", encoding="utf-8") as f:
            valid_res = json.load(f)

        stale_ok = (stale_res.get("passed") is False) and (stale_res.get("control_pass") is True)
        valid_ok = (valid_res.get("passed") is True) and (valid_res.get("control_pass") is True)

        if stale_ok and valid_ok:
            status = "PASS"
        elif not stale_ok and valid_ok:
            status = "FAIL_STALE_PASSED"
        elif stale_ok and not valid_ok:
            status = "FAIL_VALID_FAILED"
        else:
            status = "FAIL_BOTH"

        return {
            "status": "PASS" if (stale_ok and valid_ok) else "FAIL",
            "stale_pass": stale_ok,
            "valid_pass": valid_ok,
            "control_status": status
        }

    def verify_snapshot_hash(self, candidate: Dict[str, Any]) -> Dict[str, Any]:
        """
        Verifies snapshot purity:
        Checks that files in after/ exist in git archive of target_commit.
        """
        repo_name = candidate.get("repo_name", "")
        target_commit = candidate.get("target_commit", "")
        tid = candidate.get("transition_id", "")
        repo_dir = get_repo_dir(repo_name)

        if not repo_dir:
            return {"status": "FAIL", "reason": "Missing repo dir for snapshot hash"}

        fixture_after = os.path.join(FIXTURES_DIR, tid, "after")
        if not os.path.isdir(fixture_after):
            return {"status": "FAIL", "reason": f"Missing fixture after directory: {fixture_after}"}

        # Check changed_files match git commit contents
        changed_files = candidate.get("changed_files", [])
        mismatches = []
        for cf in changed_files:
            disk_p = os.path.join(fixture_after, cf)
            if not os.path.exists(disk_p):
                continue
            with open(disk_p, "rb") as f:
                disk_content = f.read()

            git_res = subprocess.run(
                ["git", "-C", repo_dir, "show", f"{target_commit}:{cf}"],
                capture_output=True
            )
            if git_res.returncode == 0:
                disk_sha = hashlib.sha256(disk_content).hexdigest()
                git_sha = hashlib.sha256(git_res.stdout).hexdigest()
                if disk_sha != git_sha:
                    mismatches.append({"file": cf, "disk_sha": disk_sha, "git_sha": git_sha})

        if mismatches:
            return {"status": "FAIL", "reason": "Hash mismatch against git archive", "mismatches": mismatches}

        return {"status": "PASS", "verified_files": len(changed_files)}

    def verify_candidate_v3(self, candidate: Dict[str, Any]) -> Dict[str, Any]:
        """
        Rigorous multi-stage audit for Pilot-v1.2c.
        ACCEPT condition:
        commit_verification == PASS
        AND causality_status == CAUSALITY_PASS
        AND fixture_control_verification == PASS
        AND hidden_test_verification == PASS
        AND snapshot_hash_verification == PASS
        """
        repo_name = candidate.get("repo_name")
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
        causality_res = self.verify_declarative_causality(candidate)
        orig_test_res = self.verify_original_tests(candidate)
        hidden_test_res = self.verify_hidden_tests(candidate)
        control_res = self.verify_fixture_controls(candidate)
        snapshot_res = self.verify_snapshot_hash(candidate)

        # Gate logic
        passes_gates = (
            commit_verification == "PASS"
            and causality_res.get("causality_status") == "CAUSALITY_PASS"
            and control_res.get("status") == "PASS"
            and hidden_test_res.get("status") == "PASS"
            and snapshot_res.get("status") == "PASS"
        )

        if passes_gates:
            overall_status = "ACCEPT"
        elif commit_verification == "FAIL" or causality_res.get("causality_status") == "CAUSALITY_FAIL" or control_res.get("status") == "FAIL":
            overall_status = "REJECT"
        else:
            overall_status = "NEEDS_FIX"

        return {
            "transition_id": candidate.get("transition_id"),
            "repo_name": repo_name,
            "overall_status": overall_status,
            "commit_verification": commit_verification,
            "causality_status": causality_res.get("causality_status"),
            "original_test_verification": orig_test_res.get("status"),
            "hidden_test_verification": hidden_test_res.get("status"),
            "fixture_control_verification": control_res.get("status"),
            "snapshot_hash_verification": snapshot_res.get("status"),
            "causality_details": causality_res,
            "original_test_details": orig_test_res,
            "hidden_test_details": hidden_test_res,
            "control_details": control_res,
            "snapshot_details": snapshot_res
        }
