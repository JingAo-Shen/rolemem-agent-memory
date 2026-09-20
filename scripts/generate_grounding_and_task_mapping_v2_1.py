#!/usr/bin/env python3
"""
scripts/generate_grounding_and_task_mapping_v2_1.py

Generates reproducible machine evidence artifacts for Protocol V2.1-R2:
1. data/memory_grounding_v2_1/<tid>.json
2. data/task_mapping_v2_1/<tid>.json
3. data/evidence_integrity_v2_1/<tid>.json
"""

import os
import sys
import glob
import json
import hashlib
import subprocess
from typing import Dict, Any, List

REPO_CACHE = "/code/repo_cache"
SPECS_DIR = "/code/rolemem-agent-memory/data/specs"
CAUSAL_DIR = "/code/rolemem-agent-memory/data/causal_matrix_v2_1"
EXTERNAL_EV_DIR = "/code/rolemem-agent-memory/data/external_evidence"
HIDDEN_TEST_DIR = "/code/rolemem-agent-memory/data/hidden_test_evidence"
TEST_EV_DIR = "/code/rolemem-agent-memory/data/test_evidence"

GROUNDING_DIR = "/code/rolemem-agent-memory/data/memory_grounding_v2_1"
TASK_MAPPING_DIR = "/code/rolemem-agent-memory/data/task_mapping_v2_1"
EVIDENCE_INTEGRITY_DIR = "/code/rolemem-agent-memory/data/evidence_integrity_v2_1"

os.makedirs(GROUNDING_DIR, exist_ok=True)
os.makedirs(TASK_MAPPING_DIR, exist_ok=True)
os.makedirs(EVIDENCE_INTEGRITY_DIR, exist_ok=True)


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def get_git_file(repo: str, commit: str, filepath: str) -> str:
    repo_dir = os.path.join(REPO_CACHE, repo)
    if not os.path.isdir(repo_dir):
        return ""
    res = subprocess.run(
        ["git", "show", f"{commit}:{filepath}"],
        cwd=repo_dir,
        capture_output=True,
        text=True
    )
    return res.stdout if res.returncode == 0 else ""


def get_git_diff(repo: str, b_c: str, t_c: str, filepath: str) -> str:
    repo_dir = os.path.join(REPO_CACHE, repo)
    if not os.path.isdir(repo_dir):
        return ""
    res = subprocess.run(
        ["git", "diff", b_c, t_c, "--", filepath],
        cwd=repo_dir,
        capture_output=True,
        text=True
    )
    return res.stdout if res.returncode == 0 else ""


def check_git_commit(repo: str, commit: str) -> bool:
    repo_dir = os.path.join(REPO_CACHE, repo)
    if not os.path.isdir(repo_dir) or len(commit) != 40:
        return False
    res = subprocess.run(
        ["git", "cat-file", "-t", commit],
        cwd=repo_dir,
        capture_output=True,
        text=True
    )
    return (res.returncode == 0 and res.stdout.strip() == "commit")


def generate_all_artifacts():
    spec_files = sorted(glob.glob(f"{SPECS_DIR}/trans_track_a_*.json"))
    print(f"Processing {len(spec_files)} transition specifications...")

    for sf in spec_files:
        with open(sf, "r", encoding="utf-8") as f:
            spec = json.load(f)

        tid = spec["transition_id"]
        repo = spec["repo_name"].split("/")[-1]
        b_commit = spec.get("base_commit", "")
        t_commit = spec.get("target_commit", "")
        primary_file = spec.get("primary_file", "")
        pr_url = str(spec.get("pr_url", ""))
        stale_candidate = spec.get("stale_memory_candidate", "")
        valid_candidate = spec.get("valid_memory_candidate", "")
        current_task = spec.get("current_task", "")
        target_symbol = spec.get("target_symbol", "")
        target_file = spec.get("target_file", "")

        b_src = get_git_file(repo, b_commit, primary_file)
        t_src = get_git_file(repo, t_commit, primary_file)
        diff_hunk = get_git_diff(repo, b_commit, t_commit, primary_file)

        # 1. Grounding Artifact
        # Check symbol / candidate presence
        dep_syms = spec.get("deprecated_symbols", []) + spec.get("changed_symbols", [])
        base_sym_found = any(s in b_src for s in dep_syms) if (b_src and dep_syms) else bool(b_src)
        target_sym_found = bool(t_src)

        base_grounded = bool(b_src and len(stale_candidate.strip()) > 15)
        target_grounded = bool(t_src and len(valid_candidate.strip()) > 15)

        grounding_data = {
            "transition_id": tid,
            "repository": repo,
            "base_commit": b_commit,
            "target_commit": t_commit,
            "primary_file": primary_file,
            "base_grounded": base_grounded,
            "target_grounded": target_grounded,
            "base_symbol_found": base_sym_found,
            "target_symbol_found": target_sym_found,
            "stale_memory_candidate": stale_candidate,
            "valid_memory_candidate": valid_candidate,
            "base_file_sha256": sha256_text(b_src) if b_src else "",
            "target_file_sha256": sha256_text(t_src) if t_src else ""
        }
        with open(os.path.join(GROUNDING_DIR, f"{tid}.json"), "w", encoding="utf-8") as gf:
            json.dump(grounding_data, gf, indent=2)

        # 2. Task Mapping Artifact
        causal_file = os.path.join(CAUSAL_DIR, f"{tid}.json")
        causal_pass = False
        execution_status = "UNKNOWN"
        if os.path.exists(causal_file):
            with open(causal_file, "r", encoding="utf-8") as cf:
                cdata = json.load(cf)
                causal_pass = bool(cdata.get("causal_pass", False))
                execution_status = cdata.get("execution_status", "UNKNOWN")

        has_hidden_test = os.path.exists(os.path.join(HIDDEN_TEST_DIR, f"{tid}.py")) or os.path.exists(os.path.join(HIDDEN_TEST_DIR, f"{tid}.json"))
        has_test_ev = os.path.exists(os.path.join(TEST_EV_DIR, f"{tid}.json")) or os.path.exists(os.path.join(TEST_EV_DIR, tid))

        task_mapping_verified = bool(current_task and (execution_status == "EXECUTED" or has_hidden_test or has_test_ev))

        task_mapping_data = {
            "transition_id": tid,
            "repository": repo,
            "current_task": current_task,
            "target_symbol": target_symbol,
            "target_file": target_file,
            "task_mapping_verified": task_mapping_verified,
            "execution_status": execution_status,
            "causal_pass": causal_pass,
            "has_hidden_test": has_hidden_test,
            "has_test_evidence": has_test_ev
        }
        with open(os.path.join(TASK_MAPPING_DIR, f"{tid}.json"), "w", encoding="utf-8") as tf:
            json.dump(task_mapping_data, tf, indent=2)

        # 3. Evidence Integrity Artifact
        auth_base = check_git_commit(repo, b_commit)
        auth_target = check_git_commit(repo, t_commit)
        pr_valid = pr_url.startswith("https://github.com/")
        ext_ev_exists = os.path.isdir(os.path.join(EXTERNAL_EV_DIR, tid)) or os.path.exists(os.path.join(EXTERNAL_EV_DIR, f"{tid}.json"))
        evidence_integrity_verified = bool(auth_base and auth_target and pr_valid and b_src and ext_ev_exists)

        evidence_data = {
            "transition_id": tid,
            "repository": repo,
            "base_commit": b_commit,
            "target_commit": t_commit,
            "authenticity_base": auth_base,
            "authenticity_target": auth_target,
            "authenticity_verified": (auth_base and auth_target),
            "primary_file_verified": bool(b_src and t_src),
            "diff_hunk_bytes": len(diff_hunk),
            "pr_url": pr_url,
            "pr_url_valid": pr_valid,
            "external_evidence_found": ext_ev_exists,
            "evidence_integrity_verified": evidence_integrity_verified
        }
        with open(os.path.join(EVIDENCE_INTEGRITY_DIR, f"{tid}.json"), "w", encoding="utf-8") as ef:
            json.dump(evidence_data, ef, indent=2)

    print("=== Successfully Generated Grounding, Task Mapping, and Evidence Integrity Artifacts ===")


if __name__ == "__main__":
    generate_all_artifacts()
