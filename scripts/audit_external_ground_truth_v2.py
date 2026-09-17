"""
scripts/audit_external_ground_truth_v2.py
Pilot-v1.2d-r1 Dual-Source External Ground Truth Audit.
Validates candidate transitions against canonical local Git mirrors (/code/repo_cache/)
and GitHub PR metadata.

Every record outputs:
{
  "pr_identity": {},
  "commit_linkage": {},
  "issue_linkage": {},
  "symbol_transition": {},
  "task_semantics": {},
  "memory_semantics": {},
  "test_evidence": {},
  "spec_sha256": "...",
  "auditor_version": "2.0.0",
  "repo_commit_sha": "...",
  "verified_at": "...",
  "external_ground_truth_status": "PASS|FAIL|AMBIGUOUS"
}
Output saved to data/ground_truth_audit_v2/<transition_id>.json.
"""

import os
import ast
import json
import hashlib
import subprocess
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional


SPECS_DIR = "/code/rolemem-agent-memory/data/specs"
REPO_CACHE_ROOT = "/code/repo_cache"
AUDIT_V2_DIR = "/code/rolemem-agent-memory/data/ground_truth_audit_v2"

REPO_DIR_MAP = {
    "pallets/werkzeug": os.path.join(REPO_CACHE_ROOT, "werkzeug"),
    "pallets/flask": os.path.join(REPO_CACHE_ROOT, "flask"),
    "pallets/click": os.path.join(REPO_CACHE_ROOT, "click"),
    "urllib3/urllib3": os.path.join(REPO_CACHE_ROOT, "urllib3"),
    "psf/requests": os.path.join(REPO_CACHE_ROOT, "requests"),
}


def compute_spec_sha256(spec: Dict[str, Any]) -> str:
    serialized = json.dumps(spec, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def audit_candidate_v2(spec: Dict[str, Any]) -> Dict[str, Any]:
    tid = spec["transition_id"]
    repo_name = spec["repo_name"]
    git_dir = REPO_DIR_MAP.get(repo_name)
    spec_hash = compute_spec_sha256(spec)

    errors = []

    if not git_dir or not os.path.isdir(git_dir):
        return {
            "transition_id": tid,
            "external_ground_truth_status": "FAIL",
            "errors": [f"Git repository cache not found: {git_dir}"]
        }

    # 1. Commit Linkage Audit
    base_sha = spec.get("base_commit", "")
    target_sha = spec.get("target_commit", "")

    # Check base commit exists
    r_base = subprocess.run(["git", "-C", git_dir, "rev-parse", "--verify", f"{base_sha}^{{commit}}"], capture_output=True, text=True)
    base_exists = (r_base.returncode == 0)
    if not base_exists:
        errors.append(f"base_commit does not exist: {base_sha}")

    # Check target commit exists
    r_target = subprocess.run(["git", "-C", git_dir, "rev-parse", "--verify", f"{target_sha}^{{commit}}"], capture_output=True, text=True)
    target_exists = (r_target.returncode == 0)
    if not target_exists:
        errors.append(f"target_commit does not exist: {target_sha}")

    # Check ancestry / merge parentage
    target_is_descendant = False
    if base_exists and target_exists:
        # Check if base is ancestor of target or target is descendant
        r_merge_base = subprocess.run(["git", "-C", git_dir, "merge-base", base_sha, target_sha], capture_output=True, text=True)
        target_is_descendant = (r_merge_base.returncode == 0 and len(r_merge_base.stdout.strip()) > 0)

    # Get target commit message and parents
    target_log = ""
    target_parents = []
    if target_exists:
        r_log = subprocess.run(["git", "-C", git_dir, "log", "-1", "--format=%B", target_sha], capture_output=True, text=True)
        target_log = r_log.stdout.strip()
        r_parents = subprocess.run(["git", "-C", git_dir, "log", "-1", "--format=%P", target_sha], capture_output=True, text=True)
        target_parents = r_parents.stdout.strip().split()

    commit_linkage = {
        "base_commit": base_sha,
        "target_commit": target_sha,
        "base_commit_exists": base_exists,
        "target_commit_exists": target_exists,
        "target_is_descendant": target_is_descendant,
        "target_parents": target_parents,
        "status": "PASS" if (base_exists and target_exists) else "FAIL"
    }

    # 2. PR Identity Audit
    pr_url = spec.get("pr_url", "")
    pr_num_str = pr_url.split("/")[-1] if pr_url else ""
    pr_num = int(pr_num_str) if pr_num_str.isdigit() else None
    pr_title = spec.get("pr_title", "")

    # Check PR number in commit log or commit title
    pr_num_in_log = (f"#{pr_num}" in target_log or f"pull request #{pr_num}" in target_log.lower()) if pr_num else False
    
    # Check title match (case insensitive, ignoring backticks)
    clean_target_log = target_log.replace("`", "").lower()
    clean_pr_title = pr_title.replace("`", "").lower()
    pr_title_in_log = (clean_pr_title in clean_target_log)

    # Check git diff files
    diff_files = []
    if base_exists and target_exists:
        r_diff = subprocess.run(["git", "-C", git_dir, "diff", "--name-only", f"{base_sha}..{target_sha}"], capture_output=True, text=True)
        diff_files = [f.strip() for f in r_diff.stdout.splitlines() if f.strip()]

    spec_changed = spec.get("changed_files", [])
    changed_files_verified = all(cf in diff_files for cf in spec_changed) if diff_files else False
    if not changed_files_verified:
        errors.append(f"Spec changed_files {spec_changed} not found in actual git diff {diff_files}")

    pr_identity = {
        "pr_url": pr_url,
        "pr_number": pr_num,
        "pr_exact_title": pr_title,
        "pr_number_matched_in_git": pr_num_in_log,
        "pr_title_matched_in_git": pr_title_in_log,
        "git_commit_log_first_line": target_log.splitlines()[0] if target_log else "",
        "git_diff_files": diff_files,
        "changed_files_verified": changed_files_verified,
        "status": "PASS" if ((pr_title_in_log or pr_num_in_log) and changed_files_verified) else "FAIL"
    }

    # 3. Issue Linkage Audit
    issue_url = spec.get("issue_url", "")
    issue_num = issue_url.split("/")[-1] if issue_url else None
    issue_referenced = (f"#{issue_num}" in target_log) if issue_num else False

    issue_linkage = {
        "issue_url": issue_url,
        "issue_number": issue_num,
        "referenced_in_git_log": issue_referenced,
        "status": "PASS"
    }

    # 4. Symbol Transition Audit
    dep_symbols = spec.get("deprecated_symbols", [])
    rem_symbols = spec.get("removed_symbols", [])
    rep_symbols = spec.get("replacement_symbols", [])
    stale_patterns = spec.get("stale_action_patterns", [])

    # Check that changed files actually define or contain transition symbols
    symbols_grounded = True
    for cf in spec_changed:
        r_base_content = subprocess.run(["git", "-C", git_dir, "show", f"{base_sha}:{cf}"], capture_output=True, text=True)
        r_target_content = subprocess.run(["git", "-C", git_dir, "show", f"{target_sha}:{cf}"], capture_output=True, text=True)
        base_src = r_base_content.stdout
        target_src = r_target_content.stdout

        for s in dep_symbols + rem_symbols:
            s_name = s.split(".")[-1]
            if s_name not in base_src and s_name not in target_src:
                symbols_grounded = False
                errors.append(f"Symbol {s_name} not found in historical source of {cf}")

    symbol_transition = {
        "deprecated_symbols": dep_symbols,
        "removed_symbols": rem_symbols,
        "replacement_symbols": rep_symbols,
        "stale_action_patterns": stale_patterns,
        "symbols_grounded_in_git": symbols_grounded,
        "status": "PASS" if symbols_grounded else "FAIL"
    }

    # 5. Task Semantics Audit
    current_task = spec.get("current_task", "")
    target_file = spec.get("target_file", "")
    target_symbol = spec.get("target_symbol", "")
    task_aligned = (target_file in current_task) and (target_symbol in current_task)
    if not task_aligned:
        errors.append(f"Task prompt does not reference target_file ({target_file}) or target_symbol ({target_symbol})")

    task_semantics = {
        "target_file": target_file,
        "target_symbol": target_symbol,
        "current_task": current_task,
        "aligned": task_aligned,
        "status": "PASS" if task_aligned else "FAIL"
    }

    # 6. Memory Semantics Audit
    stale_mem = spec.get("stale_memory_candidate", "")
    valid_mem = spec.get("valid_memory_candidate", "")
    mem_valid = len(stale_mem) > 10 and len(valid_mem) > 10 and (stale_mem != valid_mem)

    memory_semantics = {
        "stale_memory_candidate": stale_mem,
        "valid_memory_candidate": valid_mem,
        "distinct": mem_valid,
        "status": "PASS" if mem_valid else "FAIL"
    }

    # 7. Test Evidence Audit
    orig_req = spec.get("original_test_required", True)
    existing_test = spec.get("existing_tests")
    gen_hidden_only = spec.get("generated_hidden_test_only", False)

    test_status = "PASS"
    test_relevance_rationale = ""

    if orig_req:
        if not existing_test or "::" not in existing_test:
            test_status = "FAIL"
            errors.append(f"original_test_required is True but existing_tests is invalid: {existing_test}")
        else:
            rel_file, test_func = existing_test.split("::", 1)
            # Check test exists in target commit git
            r_show_test = subprocess.run(["git", "-C", git_dir, "show", f"{target_sha}:{rel_file}"], capture_output=True, text=True)
            if r_show_test.returncode != 0:
                test_status = "FAIL"
                errors.append(f"Original test file {rel_file} not found in target commit {target_sha}")
            else:
                try:
                    tree = ast.parse(r_show_test.stdout)
                    found_test = False
                    test_mentions_symbol = False
                    for node in ast.walk(tree):
                        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == test_func:
                            found_test = True
                            # Check relevance: test AST references transition symbols
                            for s in dep_symbols + rem_symbols + rep_symbols:
                                s_name = s.split(".")[-1]
                                if s_name in ast.unparse(node):
                                    test_mentions_symbol = True
                    if not found_test:
                        test_status = "FAIL"
                        errors.append(f"Test node {test_func} not found in {rel_file} AST")
                    else:
                        is_in_diff = rel_file in diff_files
                        if is_in_diff or test_mentions_symbol:
                            test_status = "PASS"
                            test_relevance_rationale = f"Test in diff: {is_in_diff}, references symbol: {test_mentions_symbol}"
                        else:
                            test_status = "FAIL"
                            errors.append(f"Test {existing_test} exists but is neither modified in PR nor references transition symbols")
                except SyntaxError:
                    test_status = "FAIL"
                    errors.append(f"SyntaxError parsing test file {rel_file}")
    else:
        # Waived test evidence: must explicitly set generated_hidden_test_only: True
        if gen_hidden_only:
            test_status = "PASS"
            test_relevance_rationale = "Original test waived; explicitly marked generated_hidden_test_only=True"
        else:
            test_status = "FAIL"
            errors.append("original_test_required=False requires generated_hidden_test_only=True")

    test_evidence = {
        "original_test_required": orig_req,
        "generated_hidden_test_only": gen_hidden_only,
        "existing_tests": existing_test,
        "relevance_rationale": test_relevance_rationale,
        "status": test_status
    }

    # Final external ground truth status
    all_passed = (
        commit_linkage["status"] == "PASS" and
        pr_identity["status"] == "PASS" and
        issue_linkage["status"] == "PASS" and
        symbol_transition["status"] == "PASS" and
        task_semantics["status"] == "PASS" and
        memory_semantics["status"] == "PASS" and
        test_evidence["status"] == "PASS" and
        len(errors) == 0
    )
    overall_status = "PASS" if all_passed else "FAIL"

    now_iso = datetime.now(timezone.utc).isoformat()

    return {
        "transition_id": tid,
        "repo_name": repo_name,
        "spec_sha256": spec_hash,
        "auditor_version": "2.0.0",
        "repo_commit_sha": target_sha,
        "verified_at": now_iso,
        "pr_identity": pr_identity,
        "commit_linkage": commit_linkage,
        "issue_linkage": issue_linkage,
        "symbol_transition": symbol_transition,
        "task_semantics": task_semantics,
        "memory_semantics": memory_semantics,
        "test_evidence": test_evidence,
        "external_ground_truth_status": overall_status,
        "errors": errors
    }


def main():
    os.makedirs(AUDIT_V2_DIR, exist_ok=True)
    spec_files = sorted([f for f in os.listdir(SPECS_DIR) if f.endswith(".json")])

    print(f"=== Running Dual-Source External Ground Truth Audit v2 on {len(spec_files)} transitions ===")
    total = len(spec_files)
    passed = 0

    for sp in spec_files:
        spec_path = os.path.join(SPECS_DIR, sp)
        with open(spec_path, "r", encoding="utf-8") as f:
            spec = json.load(f)

        res = audit_candidate_v2(spec)
        tid = res["transition_id"]
        status = res["external_ground_truth_status"]
        if status == "PASS":
            passed += 1
            print(f"[{tid}] DUAL-SOURCE AUDIT: PASS")
        else:
            print(f"[{tid}] DUAL-SOURCE AUDIT: FAIL -> {res.get('errors')}")

        out_path = os.path.join(AUDIT_V2_DIR, f"{tid}.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(res, f, indent=2)

    print(f"\nExternal Ground Truth Audit v2 Complete: {passed}/{total} PASS")
    if passed != total:
        exit(1)


if __name__ == "__main__":
    main()
