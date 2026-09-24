#!/usr/bin/env python3
"""
scripts/verify_v2_2_v1_freeze_attestation.py

Comprehensive verification script for RoleMem Protocol V2.2-V1 Post-Freeze Reproducibility Attestation & Closure:
- Dynamic repository root determination.
- Verifies freeze tag and attestation tag identities and resolved commits.
- Verifies algorithm source ancestry and zero algorithm diff between candidate commit and freeze tag.
- Verifies evaluation script diff between candidate and metadata commit contains only status declarations.
- Verifies attestation commit diff against metadata commit contains strictly allowed metadata files.
- Verifies freeze manifest file checksum integrity with explicit categorized counts.
- Verifies exact-tag detached worktree test attestation provenance, fail-closed metadata, and test log hash.
- Verifies formal data firewall closure and 3-way contamination registry checksum equality.
- Emits / updates data/freeze/protocol_v2_2_v1_freeze_closure.json.
"""

import os
import sys
import json
import hashlib
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Any


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


def verify_freeze_attestation_and_closure() -> bool:
    repo_root = get_repo_root()
    manifest_path = repo_root / "data" / "freeze" / "protocol_v2_2_v1_algorithm_freeze.json"
    attestation_path = repo_root / "data" / "freeze" / "protocol_v2_2_v1_freeze_attestation.json"
    firewall_path = repo_root / "data" / "freeze" / "protocol_v2_2_formal_data_firewall.json"
    closure_path = repo_root / "data" / "freeze" / "protocol_v2_2_v1_freeze_closure.json"

    expected_algo_commit = "fe62749b98ea2a8e62ed5dbb031b39deddc33624"
    expected_meta_commit = "29c2b11a53235430c6bd53e39e96a67f1db65391"
    expected_freeze_tag = "protocol-v2.2-v1-deterministic-freeze"

    expected_attest_commit = "fcff4104645203bdf35a27ffbd04542d7e9dd995"
    expected_attest_tag = "protocol-v2.2-v1-freeze-attestation"

    errors: List[str] = []

    # -------------------------------------------------------------------------
    # 1. Tag Identities
    # -------------------------------------------------------------------------
    tag_freeze_status = "FAIL"
    try:
        tag_res = subprocess.run(
            ["git", "rev-parse", f"{expected_freeze_tag}^{{commit}}"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            check=True
        )
        resolved_freeze_commit = tag_res.stdout.strip()
        if resolved_freeze_commit != expected_meta_commit:
            errors.append(f"Freeze tag resolved to {resolved_freeze_commit}, expected {expected_meta_commit}")
        else:
            tag_freeze_status = "PASS"
    except Exception as e:
        errors.append(f"Failed to resolve freeze tag: {e}")

    tag_attest_status = "FAIL"
    try:
        tag_res2 = subprocess.run(
            ["git", "rev-parse", f"{expected_attest_tag}^{{commit}}"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            check=True
        )
        resolved_attest_commit = tag_res2.stdout.strip()
        if resolved_attest_commit != expected_attest_commit:
            errors.append(f"Attestation tag resolved to {resolved_attest_commit}, expected {expected_attest_commit}")
        else:
            tag_attest_status = "PASS"
    except Exception as e:
        errors.append(f"Failed to resolve attestation tag: {e}")

    # -------------------------------------------------------------------------
    # 2. Source Ancestry & Algorithm Diff
    # -------------------------------------------------------------------------
    algo_diff_count = -1
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
        if algo_diff_count != 0:
            errors.append(f"Non-zero algorithm source diff ({algo_diff_count} files): {diff_files}")
    except Exception as e:
        errors.append(f"Failed to check git ancestry/diff: {e}")

    # -------------------------------------------------------------------------
    # 3. Evaluation Script Freeze-Only Diff Check
    # -------------------------------------------------------------------------
    eval_diff_status = "PASS"
    try:
        eval_diff = subprocess.run(
            ["git", "diff", "-U0", expected_algo_commit, expected_meta_commit, "--", "scripts/evaluate_evidence_escalation_v1.py"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            check=True
        ).stdout
        for line in eval_diff.splitlines():
            if line.startswith(('+', '-')) and not line.startswith(('+++', '---')):
                content = line[1:].strip().strip('",')
                if not any(k in content for k in ['V2_2_', 'CURRENT_V1_RESULT_STATUS', 'PROTOCOL_VERSION', 'FORMAL_']):
                    errors.append(f"Disallowed code change in evaluate_evidence_escalation_v1.py diff: {line}")
                    eval_diff_status = "FAIL"
    except Exception as e:
        errors.append(f"Failed to verify evaluation script diff: {e}")
        eval_diff_status = "FAIL"

    # -------------------------------------------------------------------------
    # 4. Attestation Commit Metadata-Only Diff Check
    # -------------------------------------------------------------------------
    attest_diff_files_count = -1
    allowed_attest_files = {
        "data/freeze/protocol_v2_2_v1_freeze_attestation.json",
        "data/freeze/protocol_v2_2_v1_freeze_attestation_test_log.txt",
        "scripts/verify_v2_2_v1_freeze_attestation.py"
    }
    try:
        att_diff_res = subprocess.run(
            ["git", "diff", "--name-only", expected_meta_commit, expected_attest_commit],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            check=True
        )
        att_diff_files = [line.strip() for line in att_diff_res.stdout.splitlines() if line.strip()]
        attest_diff_files_count = len(att_diff_files)
        for f in att_diff_files:
            if f not in allowed_attest_files:
                errors.append(f"Disallowed file modified in attestation commit: {f}")
    except Exception as e:
        errors.append(f"Failed to verify attestation commit diff: {e}")

    # -------------------------------------------------------------------------
    # 5. Manifest Hash Integrity (Detailed Categorized Breakdown)
    # -------------------------------------------------------------------------
    manifest_status = "PASS"
    src_checked = 0
    eval_checked = 0
    dev_repr_checked = 0
    dev_res_checked = 0
    contam_checked = 0
    hash_mismatches = 0

    if not manifest_path.is_file():
        errors.append(f"Manifest file missing: {manifest_path}")
        manifest_status = "FAIL"
    else:
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        # A. Algorithm Source Files
        src_files = manifest.get("frozen_algorithm_source_files", {})
        for rel_p, exp_h in src_files.items():
            full_p = repo_root / rel_p
            src_checked += 1
            if not full_p.is_file() or compute_sha256(full_p) != exp_h:
                errors.append(f"Manifest hash mismatch for source file: {rel_p}")
                hash_mismatches += 1
                manifest_status = "FAIL"

        # B. Evaluation Scripts
        eval_scripts = manifest.get("frozen_evaluation_scripts", {})
        for rel_p, exp_h in eval_scripts.items():
            full_p = repo_root / rel_p
            eval_checked += 1
            if not full_p.is_file() or compute_sha256(full_p) != exp_h:
                errors.append(f"Manifest hash mismatch for evaluation script: {rel_p}")
                hash_mismatches += 1
                manifest_status = "FAIL"

        # C. Development Claim Representation Files
        dev_repr = manifest.get("development_claim_representation", {}).get("files", {})
        for rel_p, exp_h in dev_repr.items():
            full_p = repo_root / rel_p
            dev_repr_checked += 1
            if not full_p.is_file() or compute_sha256(full_p) != exp_h:
                errors.append(f"Manifest hash mismatch for development claim representation: {rel_p}")
                hash_mismatches += 1
                manifest_status = "FAIL"

        # D. Development Result Provenance Files
        dev_res = manifest.get("development_result_provenance", {}).get("files", {})
        for rel_p, exp_h in dev_res.items():
            full_p = repo_root / rel_p
            dev_res_checked += 1
            if not full_p.is_file() or compute_sha256(full_p) != exp_h:
                errors.append(f"Manifest hash mismatch for development result file: {rel_p}")
                hash_mismatches += 1
                manifest_status = "FAIL"

        # E. Contaminated Repository Files
        contam = manifest.get("contaminated_repository_universe", {})
        for key in ["registry_path", "split_manifest_path"]:
            rel_p = contam.get(key)
            exp_h = contam.get(key.replace("_path", "_sha256"))
            if rel_p and exp_h:
                full_p = repo_root / rel_p
                contam_checked += 1
                if not full_p.is_file() or compute_sha256(full_p) != exp_h:
                    errors.append(f"Manifest hash mismatch for contamination file: {rel_p}")
                    hash_mismatches += 1
                    manifest_status = "FAIL"

    total_frozen_checked = src_checked + eval_checked + dev_repr_checked + dev_res_checked + contam_checked

    # -------------------------------------------------------------------------
    # 6. Attestation Metadata Self-Validation & Test Log Sanity (Fail-Closed)
    # -------------------------------------------------------------------------
    test_attestation_status = "PASS"
    before_mod = "NO"
    after_mod = "NO"

    if not attestation_path.is_file():
        errors.append(f"Attestation file missing: {attestation_path}")
        test_attestation_status = "FAIL"
    else:
        with open(attestation_path, "r", encoding="utf-8") as f:
            att = json.load(f)

        # Fail-closed checks on required fields
        if att.get("freeze_tag") != expected_freeze_tag:
            errors.append(f"Attestation freeze_tag mismatch: {att.get('freeze_tag')}")
            test_attestation_status = "FAIL"

        if att.get("freeze_tag_resolved_commit") != expected_meta_commit:
            errors.append(f"Attestation freeze_tag_resolved_commit mismatch: {att.get('freeze_tag_resolved_commit')}")
            test_attestation_status = "FAIL"

        if att.get("frozen_algorithm_source_commit") != expected_algo_commit:
            errors.append(f"Attestation frozen_algorithm_source_commit mismatch: {att.get('frozen_algorithm_source_commit')}")
            test_attestation_status = "FAIL"

        if att.get("freeze_metadata_commit") != expected_meta_commit:
            errors.append(f"Attestation freeze_metadata_commit mismatch: {att.get('freeze_metadata_commit')}")
            test_attestation_status = "FAIL"

        if att.get("verification_mode") != "CLEAN_DETACHED_FREEZE_TAG":
            errors.append(f"Attestation verification_mode mismatch: {att.get('verification_mode')}")
            test_attestation_status = "FAIL"

        if att.get("tracked_worktree_modified_before_test") is not False:
            before_mod = "YES"
            errors.append("Attestation indicates worktree had modifications before test execution")
            test_attestation_status = "FAIL"

        if att.get("tracked_worktree_modified_after_test") is not False:
            after_mod = "YES"
            errors.append("Attestation indicates worktree had modifications after test execution")
            test_attestation_status = "FAIL"

        if att.get("exit_code") != 0 or att.get("failed") != 0 or att.get("passed", 0) <= 0:
            errors.append(f"Attestation records non-passing test results: exit_code={att.get('exit_code')}, passed={att.get('passed')}, failed={att.get('failed')}")
            test_attestation_status = "FAIL"

        log_p = repo_root / att.get("test_log_path", "")
        if not log_p.is_file():
            errors.append(f"Attestation test log missing: {log_p}")
            test_attestation_status = "FAIL"
        else:
            actual_log_hash = compute_sha256(log_p)
            if actual_log_hash != att.get("test_log_sha256"):
                errors.append(f"Attestation test log hash mismatch: actual {actual_log_hash}, expected {att.get('test_log_sha256')}")
                test_attestation_status = "FAIL"

            log_text = log_p.read_text(encoding="utf-8")
            if "rootdir: /tmp/freeze_reproduce_worktree" not in log_text:
                errors.append("Attestation test log missing detached worktree rootdir indicator")
                test_attestation_status = "FAIL"

            expected_pass_str = f"{att['passed']} passed"
            if expected_pass_str not in log_text:
                errors.append(f"Attestation test log missing expected summary string '{expected_pass_str}'")
                test_attestation_status = "FAIL"

    # -------------------------------------------------------------------------
    # 7. Formal Data Firewall & Contamination 3-Way Check (Fail-Closed)
    # -------------------------------------------------------------------------
    formal_firewall_status = "PASS"
    contamination_registry_status = "PASS"
    firewall_opened = True

    if not firewall_path.is_file():
        errors.append(f"Formal data firewall file missing: {firewall_path}")
        formal_firewall_status = "FAIL"
    else:
        with open(firewall_path, "r", encoding="utf-8") as f:
            fw = json.load(f)

        if fw.get("formal_data_opened") is not False:
            errors.append("Formal data firewall indicates formal_data_opened != False")
            formal_firewall_status = "FAIL"
        firewall_opened = fw.get("formal_data_opened", True)

        if fw.get("formal_repository_list") is not None:
            errors.append("Formal data firewall formal_repository_list is not None")
            formal_firewall_status = "FAIL"

        if fw.get("formal_case_ids") is not None:
            errors.append("Formal data firewall formal_case_ids is not None")
            formal_firewall_status = "FAIL"

        if fw.get("formal_gold") is not None:
            errors.append("Formal data firewall formal_gold is not None")
            formal_firewall_status = "FAIL"

        if fw.get("algorithm_freeze_status") != "FROZEN":
            errors.append(f"Formal data firewall algorithm_freeze_status != FROZEN: {fw.get('algorithm_freeze_status')}")
            formal_firewall_status = "FAIL"

        if fw.get("algorithm_freeze_commit") != expected_algo_commit:
            errors.append(f"Formal data firewall algorithm_freeze_commit mismatch: {fw.get('algorithm_freeze_commit')}")
            formal_firewall_status = "FAIL"

        # 3-Way Hash Check on Contamination Registry
        reg_path = repo_root / "data" / "splits" / "repository_contamination_registry.json"
        if not reg_path.is_file():
            errors.append(f"Contamination registry file missing: {reg_path}")
            contamination_registry_status = "FAIL"
        else:
            actual_reg_hash = compute_sha256(reg_path)
            firewall_reg_hash = fw.get("development_repository_blacklist_hash")
            manifest_reg_hash = manifest.get("contaminated_repository_universe", {}).get("registry_sha256") if manifest_path.is_file() else None

            if actual_reg_hash != firewall_reg_hash:
                errors.append(f"Contamination registry actual hash ({actual_reg_hash}) != firewall hash ({firewall_reg_hash})")
                contamination_registry_status = "FAIL"

            if actual_reg_hash != manifest_reg_hash:
                errors.append(f"Contamination registry actual hash ({actual_reg_hash}) != manifest hash ({manifest_reg_hash})")
                contamination_registry_status = "FAIL"

    # -------------------------------------------------------------------------
    # 8. Closure Artifact Emission
    # -------------------------------------------------------------------------
    closure_pass = len(errors) == 0
    closure_data = {
        "protocol_version": "2.2-v1.2",
        "closure_type": "DETERMINISTIC_ALGORITHM_FREEZE_CLOSURE",
        "algorithm_source_commit": expected_algo_commit,
        "freeze_metadata_commit": expected_meta_commit,
        "freeze_tag": expected_freeze_tag,
        "attestation_commit": expected_attest_commit,
        "attestation_tag": expected_attest_tag,
        "algorithm_source_diff_files": algo_diff_count,
        "attestation_metadata_diff_files": attest_diff_files_count,
        "evaluation_freeze_diff_status": eval_diff_status,
        "manifest_hash_integrity": manifest_status,
        "manifest_files_checked": total_frozen_checked,
        "manifest_files_breakdown": {
            "algorithm_source_files": src_checked,
            "evaluation_scripts": eval_checked,
            "development_representation_files": dev_repr_checked,
            "development_result_files": dev_res_checked,
            "contamination_files": contam_checked
        },
        "test_attestation_status": test_attestation_status,
        "formal_firewall_status": formal_firewall_status,
        "contamination_registry_status": contamination_registry_status,
        "formal_data_opened": firewall_opened,
        "freeze_closure": "PASS" if closure_pass else "FAIL"
    }

    with open(closure_path, "w", encoding="utf-8") as f:
        json.dump(closure_data, f, indent=2)

    # -------------------------------------------------------------------------
    # 9. Formatted Console Output
    # -------------------------------------------------------------------------
    print("==================================================")
    print("FREEZE_ATTESTATION_CLOSURE")
    print("==================================================")
    print(f"algorithm_source_commit = {expected_algo_commit}")
    print(f"freeze_metadata_commit = {expected_meta_commit}")
    print(f"freeze_tag = {expected_freeze_tag}")
    print()
    print(f"attestation_commit = {expected_attest_commit}")
    print(f"attestation_tag = {expected_attest_tag}")
    print()
    print(f"freeze_tag_identity = {tag_freeze_status}")
    print(f"attestation_tag_identity = {tag_attest_status}")
    print(f"algorithm_source_diff = {algo_diff_count} files")
    print(f"attestation_metadata_diff = {attest_diff_files_count} files")
    print(f"evaluation_freeze_diff_status = {eval_diff_status}")
    print()
    print(f"algorithm_source_files_checked = {src_checked}")
    print(f"evaluation_scripts_checked = {eval_checked}")
    print(f"development_representation_files_checked = {dev_repr_checked}")
    print(f"development_result_files_checked = {dev_res_checked}")
    print(f"contamination_files_checked = {contam_checked}")
    print()
    print(f"total_frozen_files_checked = {total_frozen_checked}")
    print(f"hash_mismatches = {hash_mismatches}")
    print(f"manifest_hash_integrity = {manifest_status}")
    print()
    print(f"exact_tag_test_run = {test_attestation_status}")
    print(f"tracked_worktree_modified_before_test = {before_mod}")
    print(f"tracked_worktree_modified_after_test = {after_mod}")
    print()
    print(f"contamination_registry_status = {contamination_registry_status}")
    print(f"formal_firewall_status = {formal_firewall_status}")
    print(f"formal_data_opened = {str(firewall_opened).lower()}")
    print()

    if closure_pass:
        print("freeze_attestation = PASS")
        print("freeze_closure = PASS")
        print("==================================================")
        return True
    else:
        print("freeze_attestation = FAIL")
        print("freeze_closure = FAIL")
        print("Errors detected:")
        for err in errors:
            print(f"  - {err}")
        print("==================================================")
        return False


if __name__ == "__main__":
    success = verify_freeze_attestation_and_closure()
    sys.exit(0 if success else 1)
