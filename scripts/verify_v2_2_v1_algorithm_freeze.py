#!/usr/bin/env python3
"""
scripts/verify_v2_2_v1_algorithm_freeze.py

Verification script for RoleMem Protocol V2.2-V1 Deterministic Algorithm Freeze:
1. Loads freeze manifest from data/freeze/protocol_v2_2_v1_algorithm_freeze.json.
2. Recomputes SHA256 checksums for all frozen algorithm source files, evaluation scripts,
   representation files, result provenances, and contaminated repository universe records.
3. Compares recomputed checksums with the manifest.
4. Reports any hash mismatches or missing files.
5. Exits 0 on PASS, non-zero on FAIL.
"""

import os
import sys
import json
import hashlib
from typing import Dict, List, Tuple

MANIFEST_PATH = "/code/rolemem-agent-memory/data/freeze/protocol_v2_2_v1_algorithm_freeze.json"


def compute_sha256(filepath: str) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def verify_freeze() -> bool:
    if not os.path.isfile(MANIFEST_PATH):
        print(f"ERROR: Freeze manifest not found at {MANIFEST_PATH}", file=sys.stderr)
        return False

    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    print("==================================================")
    print("ALGORITHM_FREEZE_VERIFICATION")
    print("==================================================")
    print(f"Protocol Version: {manifest.get('protocol_version')}")
    print(f"Freeze Type: {manifest.get('freeze_type')}")
    print(f"Frozen Source Commit: {manifest.get('frozen_algorithm_source_commit')}")
    print(f"Algorithm Freeze: {manifest.get('algorithm_freeze')}")
    print(f"Development Benchmark Status: {manifest.get('development_benchmark_status')}")
    print("--------------------------------------------------")

    files_checked = 0
    mismatches: List[Tuple[str, str, str]] = []
    missing_files: List[str] = []

    # 1. Algorithm Source Files
    src_files = manifest.get("frozen_algorithm_source_files", {})
    for rel_path, expected_hash in src_files.items():
        abs_path = os.path.join("/code/rolemem-agent-memory", rel_path)
        files_checked += 1
        if not os.path.isfile(abs_path):
            missing_files.append(rel_path)
            continue
        actual_hash = compute_sha256(abs_path)
        if actual_hash != expected_hash:
            mismatches.append((rel_path, expected_hash, actual_hash))

    # 2. Evaluation Scripts
    eval_scripts = manifest.get("frozen_evaluation_scripts", {})
    for rel_path, expected_hash in eval_scripts.items():
        abs_path = os.path.join("/code/rolemem-agent-memory", rel_path)
        files_checked += 1
        if not os.path.isfile(abs_path):
            missing_files.append(rel_path)
            continue
        actual_hash = compute_sha256(abs_path)
        if actual_hash != expected_hash:
            mismatches.append((rel_path, expected_hash, actual_hash))

    # 3. Development Claim Representation Files
    dev_repr = manifest.get("development_claim_representation", {}).get("files", {})
    for rel_path, expected_hash in dev_repr.items():
        abs_path = os.path.join("/code/rolemem-agent-memory", rel_path)
        files_checked += 1
        if not os.path.isfile(abs_path):
            missing_files.append(rel_path)
            continue
        actual_hash = compute_sha256(abs_path)
        if actual_hash != expected_hash:
            mismatches.append((rel_path, expected_hash, actual_hash))

    # 4. Development Result Provenance Files
    result_prov = manifest.get("development_result_provenance", {}).get("files", {})
    for rel_path, expected_hash in result_prov.items():
        abs_path = os.path.join("/code/rolemem-agent-memory", rel_path)
        files_checked += 1
        if not os.path.isfile(abs_path):
            missing_files.append(rel_path)
            continue
        actual_hash = compute_sha256(abs_path)
        if actual_hash != expected_hash:
            mismatches.append((rel_path, expected_hash, actual_hash))

    # 5. Contaminated Repository Manifests
    contam = manifest.get("contaminated_repository_universe", {})
    for key in ["registry_path", "split_manifest_path"]:
        rel_path = contam.get(key)
        expected_hash = contam.get(key.replace("_path", "_sha256"))
        if rel_path and expected_hash:
            abs_path = os.path.join("/code/rolemem-agent-memory", rel_path)
            files_checked += 1
            if not os.path.isfile(abs_path):
                missing_files.append(rel_path)
                continue
            actual_hash = compute_sha256(abs_path)
            if actual_hash != expected_hash:
                mismatches.append((rel_path, expected_hash, actual_hash))

    print(f"files_checked = {files_checked}")
    print(f"hash_mismatches = {len(mismatches)}")
    print(f"missing_files = {len(missing_files)}")

    if missing_files:
        print("\nMISSING FILES DETECTED:")
        for mf in missing_files:
            print(f"  - {mf}")

    if mismatches:
        print("\nHASH MISMATCHES DETECTED:")
        for p, exp, act in mismatches:
            print(f"  - {p}: expected {exp}, got {act}")

    if not mismatches and not missing_files:
        print("\nalgorithm_freeze_integrity = PASS")
        print("==================================================")
        return True
    else:
        print("\nalgorithm_freeze_integrity = FAIL")
        print("==================================================")
        return False


if __name__ == "__main__":
    success = verify_freeze()
    sys.exit(0 if success else 1)
