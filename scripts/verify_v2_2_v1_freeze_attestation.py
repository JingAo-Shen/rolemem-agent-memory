#!/usr/bin/env python3
"""
scripts/verify_v2_2_v1_freeze_attestation.py

Comprehensive verification script for RoleMem Protocol V2.2-V1 Post-Freeze Reproducibility Attestation:
- Dynamic repository root determination.
- Verifies freeze tag identity and resolved commit.
- Verifies algorithm source ancestry and zero algorithm diff between candidate commit and freeze tag.
- Verifies freeze manifest file checksum integrity.
- Verifies exact-tag detached worktree test attestation provenance and test log hash.
- Verifies formal data firewall closure.
"""

import os
import sys
import json
import hashlib
import subprocess
from pathlib import Path


def get_repo_root() -> Path:
    try:
        res = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True
        )
        return Path(res.stdout.strip())
    except Exception:
        return Path(__file__).resolve().parents[1]


def compute_sha256(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def verify_freeze_attestation() -> bool:
    repo_root = get_repo_root()
    manifest_path = repo_root / "data" / "freeze" / "protocol_v2_2_v1_algorithm_freeze.json"
    attestation_path = repo_root / "data" / "freeze" / "protocol_v2_2_v1_freeze_attestation.json"
    firewall_path = repo_root / "data" / "freeze" / "protocol_v2_2_formal_data_firewall.json"

    expected_algo_commit = "fe62749b98ea2a8e62ed5dbb031b39deddc33624"
    expected_meta_commit = "29c2b11a53235430c6bd53e39e96a67f1db65391"
    expected_freeze_tag = "protocol-v2.2-v1-deterministic-freeze"

    errors = []

    # 1. Tag Identity
    try:
        tag_res = subprocess.run(
            ["git", "rev-parse", f"{expected_freeze_tag}^{{commit}}"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            check=True
        )
        resolved_tag_commit = tag_res.stdout.strip()
        if resolved_tag_commit != expected_meta_commit:
            errors.append(f"Tag resolved to {resolved_tag_commit}, expected {expected_meta_commit}")
            tag_identity_status = "FAIL"
        else:
            tag_identity_status = "PASS"
    except Exception as e:
        errors.append(f"Failed to resolve tag: {e}")
        tag_identity_status = "FAIL"

    # 2. Source Ancestry & Diff
    try:
        anc_res = subprocess.run(
            ["git", "merge-base", "--is-ancestor", expected_algo_commit, expected_meta_commit],
            cwd=str(repo_root),
            capture_output=True,
            text=True
        )
        if anc_res.returncode != 0:
            errors.append(f"Commit {expected_algo_commit} is not an ancestor of {expected_meta_commit}")

        diff_res = subprocess.run(
            ["git", "diff", "--name-only", expected_algo_commit, expected_meta_commit, "--", "src/claim_validity", "src/evidence_escalation"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            check=True
        )
        diff_files = [line.strip() for line in diff_res.stdout.splitlines() if line.strip()]
        algo_diff_count = len(diff_files)
        if algo_diff_count > 0:
            errors.append(f"Non-zero algorithm source diff ({algo_diff_count} files): {diff_files}")
    except Exception as e:
        errors.append(f"Failed to check git ancestry/diff: {e}")
        algo_diff_count = -1

    # 3. Manifest Hash Integrity
    manifest_status = "PASS"
    if not manifest_path.is_file():
        errors.append(f"Manifest file missing: {manifest_path}")
        manifest_status = "FAIL"
    else:
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        src_files = manifest.get("frozen_algorithm_source_files", {})
        for rel_p, exp_h in src_files.items():
            full_p = repo_root / rel_p
            if not full_p.is_file() or compute_sha256(full_p) != exp_h:
                errors.append(f"Manifest hash mismatch for {rel_p}")
                manifest_status = "FAIL"

        eval_scripts = manifest.get("frozen_evaluation_scripts", {})
        for rel_p, exp_h in eval_scripts.items():
            full_p = repo_root / rel_p
            if not full_p.is_file() or compute_sha256(full_p) != exp_h:
                errors.append(f"Evaluation script hash mismatch for {rel_p}")
                manifest_status = "FAIL"

    # 4. Exact-Tag Test Attestation
    test_run_status = "PASS"
    before_mod = "NO"
    after_mod = "NO"
    if not attestation_path.is_file():
        errors.append(f"Attestation file missing: {attestation_path}")
        test_run_status = "FAIL"
    else:
        with open(attestation_path, "r", encoding="utf-8") as f:
            att = json.load(f)

        if att.get("exit_code") != 0 or att.get("passed", 0) <= 0 or att.get("failed", 0) != 0:
            errors.append(f"Attestation records non-passing test results: exit_code={att.get('exit_code')}, passed={att.get('passed')}, failed={att.get('failed')}")
            test_run_status = "FAIL"

        log_p = repo_root / att.get("test_log_path", "")
        if not log_p.is_file() or compute_sha256(log_p) != att.get("test_log_sha256"):
            errors.append("Attestation test log hash mismatch or missing file")
            test_run_status = "FAIL"

        if att.get("tracked_worktree_modified_before_test", True):
            before_mod = "YES"
            errors.append("Worktree had modifications before test execution")
        if att.get("tracked_worktree_modified_after_test", True):
            after_mod = "YES"
            errors.append("Worktree had modifications after test execution")

    # 5. Formal Data Firewall
    firewall_opened = True
    if not firewall_path.is_file():
        errors.append(f"Formal data firewall file missing: {firewall_path}")
    else:
        with open(firewall_path, "r", encoding="utf-8") as f:
            fw = json.load(f)
        firewall_opened = fw.get("formal_data_opened", True)
        if firewall_opened:
            errors.append("Formal data firewall indicates formal_data_opened == True")

    # Output formatted report
    print("==================================================")
    print("FREEZE_ATTESTATION")
    print("==================================================")
    print(f"algorithm_source_commit = {expected_algo_commit}")
    print(f"freeze_metadata_commit = {expected_meta_commit}")
    print(f"freeze_tag = {expected_freeze_tag}")
    print()
    print(f"freeze_tag_identity = {tag_identity_status}")
    print(f"algorithm_source_diff = {algo_diff_count} files")
    print(f"manifest_hash_integrity = {manifest_status}")
    print()
    print(f"exact_tag_test_run = {test_run_status}")
    print(f"tracked_worktree_modified_before_test = {before_mod}")
    print(f"tracked_worktree_modified_after_test = {after_mod}")
    print()
    print(f"formal_data_opened = {str(firewall_opened).lower()}")
    print()

    if not errors:
        print("freeze_attestation = PASS")
        print("==================================================")
        return True
    else:
        print("freeze_attestation = FAIL")
        print("Errors detected:")
        for err in errors:
            print(f"  - {err}")
        print("==================================================")
        return False


if __name__ == "__main__":
    success = verify_freeze_attestation()
    sys.exit(0 if success else 1)
