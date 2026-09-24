#!/usr/bin/env python3
"""
scripts/verify_v2_2_formal_preregistration.py

Comprehensive verification script for RoleMem Protocol V2.2 Formal Unseen Benchmark Preregistration:
- Dynamic repository root determination.
- Verifies algorithm freeze closure status (PASS) and immutable freeze tags.
- Verifies zero algorithm source mutation against frozen source commit.
- Verifies formal data firewall integrity (formal_data_opened=False, state=S0_PREREGISTRATION, null lists).
- Verifies 4-way contamination registry SHA256 checksum equality (registry, freeze manifest, firewall, preregistration).
- Verifies machine-readable preregistration specification completeness and parameter constraints.
- Verifies non-existence of formal benchmark data/gold artifacts.
- Anti-leak / accidental data exposure scanner.
- Emits formatted verification report.
"""

import os
import sys
import json
import re
import hashlib
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Any, Set, Optional


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


def verify_formal_preregistration() -> bool:
    repo_root = get_repo_root()
    freeze_manifest_path = repo_root / "data" / "freeze" / "protocol_v2_2_v1_algorithm_freeze.json"
    attestation_path = repo_root / "data" / "freeze" / "protocol_v2_2_v1_freeze_attestation.json"
    closure_path = repo_root / "data" / "freeze" / "protocol_v2_2_v1_freeze_closure.json"
    firewall_path = repo_root / "data" / "freeze" / "protocol_v2_2_formal_data_firewall.json"
    prereg_path = repo_root / "data" / "formal_v2_2" / "protocol_preregistration.json"
    report_path = repo_root / "reports" / "protocol-v2.2-formal-benchmark-preregistration.md"
    reg_path = repo_root / "data" / "splits" / "repository_contamination_registry.json"

    expected_algo_commit = "fe62749b98ea2a8e62ed5dbb031b39deddc33624"
    expected_meta_commit = "29c2b11a53235430c6bd53e39e96a67f1db65391"
    expected_freeze_tag = "protocol-v2.2-v1-deterministic-freeze"
    expected_attest_commit = "fcff4104645203bdf35a27ffbd04542d7e9dd995"
    expected_attest_tag = "protocol-v2.2-v1-freeze-attestation"

    errors: List[str] = []

    # -------------------------------------------------------------------------
    # 1. Algorithm Freeze & Closure Status
    # -------------------------------------------------------------------------
    algo_freeze_status = "PASS"
    freeze_closure_status = "FAIL"

    # Check freeze tag resolution
    try:
        tag_res = subprocess.run(
            ["git", "rev-parse", f"{expected_freeze_tag}^{{commit}}"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            check=True
        )
        if tag_res.stdout.strip() != expected_meta_commit:
            errors.append(f"Freeze tag resolved to {tag_res.stdout.strip()}, expected {expected_meta_commit}")
            algo_freeze_status = "FAIL"
    except Exception as e:
        errors.append(f"Failed to resolve freeze tag: {e}")
        algo_freeze_status = "FAIL"

    # Check attestation tag resolution
    try:
        tag_res2 = subprocess.run(
            ["git", "rev-parse", f"{expected_attest_tag}^{{commit}}"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            check=True
        )
        if tag_res2.stdout.strip() != expected_attest_commit:
            errors.append(f"Attestation tag resolved to {tag_res2.stdout.strip()}, expected {expected_attest_commit}")
            algo_freeze_status = "FAIL"
    except Exception as e:
        errors.append(f"Failed to resolve attestation tag: {e}")
        algo_freeze_status = "FAIL"

    # Check algorithm source diff against frozen commit
    try:
        diff_res = subprocess.run(
            ["git", "diff", "--name-only", expected_algo_commit, "HEAD", "--", "src/claim_validity", "src/evidence_escalation"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            check=True
        )
        diff_files = [line.strip() for line in diff_res.stdout.splitlines() if line.strip()]
        if len(diff_files) > 0:
            errors.append(f"Non-zero algorithm source diff from {expected_algo_commit}: {diff_files}")
            algo_freeze_status = "FAIL"
    except Exception as e:
        errors.append(f"Failed to check git algorithm diff: {e}")
        algo_freeze_status = "FAIL"

    # Check freeze closure artifact
    if not closure_path.is_file():
        errors.append(f"Freeze closure artifact missing: {closure_path}")
    else:
        with open(closure_path, "r", encoding="utf-8") as f:
            closure_data = json.load(f)
        if closure_data.get("freeze_closure") == "PASS":
            freeze_closure_status = "PASS"
        else:
            errors.append(f"Freeze closure status is not PASS: {closure_data.get('freeze_closure')}")

    # -------------------------------------------------------------------------
    # 2. Formal Data Firewall Integrity (Fail-Closed)
    # -------------------------------------------------------------------------
    formal_firewall_status = "PASS"
    firewall_opened = True

    if not firewall_path.is_file():
        errors.append(f"Formal data firewall manifest missing: {firewall_path}")
        formal_firewall_status = "FAIL"
    else:
        with open(firewall_path, "r", encoding="utf-8") as f:
            fw = json.load(f)

        if fw.get("formal_data_opened") is not False:
            errors.append("Firewall indicated formal_data_opened != False")
            formal_firewall_status = "FAIL"
        firewall_opened = fw.get("formal_data_opened", True)

        if fw.get("formal_repository_list") is not None:
            errors.append("Firewall formal_repository_list is not None")
            formal_firewall_status = "FAIL"

        if fw.get("formal_case_ids") is not None:
            errors.append("Firewall formal_case_ids is not None")
            formal_firewall_status = "FAIL"

        if fw.get("formal_gold") is not None:
            errors.append("Firewall formal_gold is not None")
            formal_firewall_status = "FAIL"

        if fw.get("formal_state") != "S0_PREREGISTRATION":
            errors.append(f"Firewall formal_state != S0_PREREGISTRATION: {fw.get('formal_state')}")
            formal_firewall_status = "FAIL"

        if fw.get("formal_protocol_preregistered") is not True:
            errors.append("Firewall formal_protocol_preregistered != True")
            formal_firewall_status = "FAIL"

    # -------------------------------------------------------------------------
    # 3. 4-Way Contamination Registry Hash Integrity
    # -------------------------------------------------------------------------
    contamination_registry_3way_status = "PASS"

    if not reg_path.is_file():
        errors.append(f"Contamination registry file missing: {reg_path}")
        contamination_registry_3way_status = "FAIL"
    else:
        actual_reg_hash = compute_sha256(reg_path)

        # A. Manifest
        manifest_reg_hash = None
        if freeze_manifest_path.is_file():
            with open(freeze_manifest_path, "r", encoding="utf-8") as f:
                manifest_data = json.load(f)
            manifest_reg_hash = manifest_data.get("contaminated_repository_universe", {}).get("registry_sha256")
        if actual_reg_hash != manifest_reg_hash:
            errors.append(f"Registry actual hash ({actual_reg_hash}) != freeze manifest hash ({manifest_reg_hash})")
            contamination_registry_3way_status = "FAIL"

        # B. Firewall
        firewall_reg_hash = fw.get("development_repository_blacklist_hash") if firewall_path.is_file() else None
        if actual_reg_hash != firewall_reg_hash:
            errors.append(f"Registry actual hash ({actual_reg_hash}) != firewall hash ({firewall_reg_hash})")
            contamination_registry_3way_status = "FAIL"

        # C. Preregistration
        prereg_reg_hash = None
        if prereg_path.is_file():
            with open(prereg_path, "r", encoding="utf-8") as f:
                prereg_data = json.load(f)
            prereg_reg_hash = prereg_data.get("repository_eligibility", {}).get("contamination_blacklist", {}).get("registry_sha256")
        if actual_reg_hash != prereg_reg_hash:
            errors.append(f"Registry actual hash ({actual_reg_hash}) != preregistration hash ({prereg_reg_hash})")
            contamination_registry_3way_status = "FAIL"

    # -------------------------------------------------------------------------
    # 4. Preregistration Manifest Completeness & Parameter Verification
    # -------------------------------------------------------------------------
    prereg_manifest_status = "PASS"
    repos_selected = -1
    trans_inspected = -1
    claims_created = -1
    gold_created = -1

    if not prereg_path.is_file():
        errors.append(f"Preregistration manifest missing: {prereg_path}")
        prereg_manifest_status = "FAIL"
    else:
        with open(prereg_path, "r", encoding="utf-8") as f:
            prereg = json.load(f)

        if prereg.get("preregistration_status") != "PREREGISTERED_FROZEN":
            errors.append(f"Preregistration status != PREREGISTERED_FROZEN: {prereg.get('preregistration_status')}")
            prereg_manifest_status = "FAIL"

        sm = prereg.get("state_machine", {})
        if sm.get("current_state") != "S0_PREREGISTRATION":
            errors.append(f"State machine current_state != S0_PREREGISTRATION: {sm.get('current_state')}")
            prereg_manifest_status = "FAIL"

        expected_states = [
            "S0_PREREGISTRATION",
            "S1_REPOSITORY_DISCOVERY",
            "S2_TRANSITION_MINING",
            "S3_CLAIM_CONSTRUCTION",
            "S4_GOLD_ADJUDICATION",
            "S5_FORMAL_INPUT_FREEZE",
            "S6_PREDICTION_RUN",
            "S7_GOLD_OPEN",
            "S8_SCORING_COMPLETE"
        ]
        states_dict = sm.get("states", {})
        for s in expected_states:
            if s not in states_dict:
                errors.append(f"Missing state in state machine: {s}")
                prereg_manifest_status = "FAIL"

        # Repository targets
        repo_scale = prereg.get("repository_eligibility", {}).get("target_repository_scale", {})
        if repo_scale.get("min_accepted_repositories") != 20 or repo_scale.get("target_repositories") != 25 or repo_scale.get("max_repositories") != 30:
            errors.append(f"Invalid target_repository_scale: {repo_scale}")
            prereg_manifest_status = "FAIL"

        # Claims targets
        claim_scale = prereg.get("benchmark_composition_and_scale", {}).get("scale_targets", {})
        if claim_scale.get("min_valid_claims") != 100 or claim_scale.get("target_valid_claims") != 150 or claim_scale.get("max_valid_claims") != 200:
            errors.append(f"Invalid scale_targets: {claim_scale}")
            prereg_manifest_status = "FAIL"

        # Bootstrap configuration
        bs = prereg.get("metrics_and_statistical_analysis", {}).get("statistical_inference", {})
        if bs.get("bootstrap_seed") != 3407 or bs.get("bootstrap_samples") != 5000:
            errors.append(f"Invalid bootstrap configuration: {bs}")
            prereg_manifest_status = "FAIL"

        # Budget
        budget = prereg.get("metrics_and_statistical_analysis", {}).get("runtime_budget")
        if budget != "B50":
            errors.append(f"Invalid runtime budget: {budget}")
            prereg_manifest_status = "FAIL"

        # Counts must all be 0
        fw_dict = prereg.get("formal_data_firewall", {})
        repos_selected = fw_dict.get("formal_repositories_selected_count", -1)
        trans_inspected = fw_dict.get("formal_transitions_inspected_count", -1)
        claims_created = fw_dict.get("formal_claims_created_count", -1)
        gold_created = fw_dict.get("formal_gold_labels_created_count", -1)

        if repos_selected != 0 or trans_inspected != 0 or claims_created != 0 or gold_created != 0:
            errors.append(f"Non-zero counts in preregistration firewall: repos={repos_selected}, trans={trans_inspected}, claims={claims_created}, gold={gold_created}")
            prereg_manifest_status = "FAIL"

        if fw_dict.get("formal_data_opened") is not False:
            errors.append("Preregistration formal_data_firewall.formal_data_opened != False")
            prereg_manifest_status = "FAIL"

    # -------------------------------------------------------------------------
    # 5. Non-Existence of Formal Benchmark Data Files
    # -------------------------------------------------------------------------
    forbidden_formal_data_files = [
        repo_root / "data" / "formal_v2_2" / "formal_inputs.jsonl",
        repo_root / "data" / "formal_v2_2" / "formal_gold_private.jsonl",
        repo_root / "data" / "formal_v2_2" / "formal_case_map_private.json",
        repo_root / "data" / "formal_v2_2" / "formal_predictions.jsonl",
        repo_root / "data" / "formal_v2_2" / "formal_evaluation_report.json"
    ]
    for p in forbidden_formal_data_files:
        if p.exists():
            errors.append(f"Forbidden formal benchmark artifact exists prematurely: {p}")
            prereg_manifest_status = "FAIL"

    # Check report file exists
    if not report_path.is_file():
        errors.append(f"Preregistration human-readable report missing: {report_path}")
        prereg_manifest_status = "FAIL"

    # -------------------------------------------------------------------------
    # 6. Anti-Leak / Accidental Data Exposure Scanner
    # -------------------------------------------------------------------------
    anti_leak_status = "PASS"

    # Load known contaminated repos
    known_repos: Set[str] = set()
    if reg_path.is_file():
        with open(reg_path, "r", encoding="utf-8") as f:
            reg_json = json.load(f)
        known_repos = set(reg_json.get("records", {}).keys())

    # Files to audit for leaks: data/formal_v2_2/** and reports/protocol-v2.2-formal-benchmark-preregistration.md
    audit_files = [prereg_path, report_path, firewall_path]
    for af in audit_files:
        if not af.is_file():
            continue
        text = af.read_text(encoding="utf-8")

        # Check for actual external case ID assignments (e.g. FV22-000001: { ... })
        # We allow documentation references like "FV22-XXXXXX" or "FV22-000001", but not populated data rows
        if '"case_id": "FV22-' in text or '"gold_label":' in text or '"target_label":' in text:
            errors.append(f"Potential formal case data leak found in {af}")
            anti_leak_status = "FAIL"

        # Check for unexpected candidate git clone urls
        # Documentation may mention "github.com", but not actual candidate target repos like "github.com/foo/bar.git"
        git_urls = re.findall(r'https://github\.com/([a-zA-Z0-9_\-\.]+)/([a-zA-Z0-9_\-\.]+)', text)
        for owner, repo_name in git_urls:
            clean_repo = repo_name.rstrip('.git').rstrip('",)').lower()
            if clean_repo not in known_repos and clean_repo not in ["rolemem-agent-memory"]:
                errors.append(f"Unregistered candidate repo URL detected in {af}: {owner}/{repo_name}")
                anti_leak_status = "FAIL"

    # -------------------------------------------------------------------------
    # 7. Formatted Console Output
    # -------------------------------------------------------------------------
    all_pass = len(errors) == 0 and algo_freeze_status == "PASS" and freeze_closure_status == "PASS" and formal_firewall_status == "PASS" and contamination_registry_3way_status == "PASS" and prereg_manifest_status == "PASS" and anti_leak_status == "PASS"

    print("==================================================")
    print("FORMAL_BENCHMARK_PREREGISTRATION_VERIFICATION")
    print("==================================================")
    print(f"algorithm_freeze_status = {algo_freeze_status}")
    print(f"freeze_closure_status = {freeze_closure_status}")
    print(f"formal_data_firewall_status = {formal_firewall_status}")
    print(f"formal_data_opened = {str(firewall_opened).lower()}")
    print()
    print(f"formal_state = S0_PREREGISTRATION")
    print(f"preregistration_manifest = {prereg_manifest_status}")
    print(f"contamination_registry_3way_hash = {contamination_registry_3way_status}")
    print()
    print(f"formal_repository_list = null")
    print(f"formal_case_ids = null")
    print(f"formal_gold = null")
    print()
    print(f"formal_repositories_selected = {repos_selected}")
    print(f"formal_transitions_inspected = {trans_inspected}")
    print(f"formal_claims_created = {claims_created}")
    print(f"formal_gold_labels_created = {gold_created}")
    print()
    print(f"anti_leak_data_exposure_scan = {anti_leak_status}")

    if all_pass:
        print("formal_preregistration = PASS")
        print("==================================================")
        return True
    else:
        print("formal_preregistration = FAIL")
        print("Errors detected:")
        for err in errors:
            print(f"  - {err}")
        print("==================================================")
        return False


if __name__ == "__main__":
    success = verify_formal_preregistration()
    sys.exit(0 if success else 1)
