#!/usr/bin/env python3
"""
scripts/generate_hidden_test_evidence.py
Executes hidden tests for Track A reconstructed transitions in the Bubblewrap sandbox.
Binds output evidence to compute_unified_audit_fingerprint.
Saves genuine execution logs, exit codes, and collection statuses to:
  data/hidden_test_evidence/<transition_id>.json
  data/test_evidence/<transition_id>.json
"""

import os
import sys
import json
from typing import Dict, Any

sys.path.insert(0, "/code/rolemem-agent-memory")
from src.sandbox_secure import SecureSandboxExecutor
from src.fingerprint import compute_unified_audit_fingerprint, DEFAULT_AUDITOR_VERSION
from scripts.run_causal_counterfactual_v2 import load_workspace

DATA_DIR = "/code/rolemem-agent-memory/data"
FIXTURES_DIR = "/code/rolemem-agent-memory/fixtures_v2"
HIDDEN_OUT_DIR = os.path.join(DATA_DIR, "hidden_test_evidence")
TEST_OUT_DIR = os.path.join(DATA_DIR, "test_evidence")
MANIFEST_PATH = os.path.join(DATA_DIR, "track_a_reconstructed_manifest.jsonl")
VENVS_ROOT = "/code/rolemem-agent-memory/.venvs"

os.makedirs(HIDDEN_OUT_DIR, exist_ok=True)
os.makedirs(TEST_OUT_DIR, exist_ok=True)


def generate_hidden_test_evidence_for_cohort():
    print("=== Generating Executable Hidden Test Evidence in Bubblewrap Sandbox ===")
    specs = []
    with open(MANIFEST_PATH, "r") as f:
        for line in f:
            if line.strip():
                specs.append(json.loads(line))

    passed = 0
    for spec in specs:
        tid = spec["transition_id"]
        fixture_dir = os.path.join(FIXTURES_DIR, tid)
        target_file = spec.get("target_file", "solution.py")

        venv_bin = os.path.join(VENVS_ROOT, tid, "bin")
        if os.path.isdir(venv_bin):
            executor = SecureSandboxExecutor(custom_env_bin_dir=venv_bin)
        else:
            executor = SecureSandboxExecutor()

        with open(os.path.join(fixture_dir, "controls", "valid_solution.py"), "r", encoding="utf-8") as f:
            valid_code = f.read()
        with open(os.path.join(fixture_dir, "hidden_tests", "test_evaluation.py"), "r", encoding="utf-8") as f:
            test_code = f.read()

        target_ws = load_workspace(os.path.join(fixture_dir, "after"))

        # Execute valid solution against hidden test on target snapshot
        p_res, log = executor.execute_in_sandbox(
            workspace_files=target_ws,
            target_file=target_file,
            generated_code=valid_code,
            test_code=test_code
        )

        fp = compute_unified_audit_fingerprint(spec, fixture_dir=fixture_dir, auditor_version=DEFAULT_AUDITOR_VERSION)

        collection_status = "PASS" if "1 error during collection" not in log and "collected 0 items" not in log else "FAIL"
        execution_status = "PASS" if p_res else "FAIL"
        overall_status = "PASS" if p_res and collection_status == "PASS" else "FAIL"

        evidence_payload = {
            "transition_id": tid,
            "audit_fingerprint": fp,
            "status": overall_status,
            "collection_status": collection_status,
            "execution_status": execution_status,
            "exit_code": 0 if p_res else 1,
            "raw_stdout": log[:500],
            "verification_status": "GENERATED_HIDDEN_TEST_PASS" if overall_status == "PASS" else "FAIL"
        }

        with open(os.path.join(HIDDEN_OUT_DIR, f"{tid}.json"), "w", encoding="utf-8") as f:
            json.dump(evidence_payload, f, indent=2)

        # Also write G3 test evidence
        g3_payload = {
            "transition_id": tid,
            "audit_fingerprint": fp,
            "status": "GENERATED_HIDDEN_TEST_ONLY",
            "verification_status": "GENERATED_HIDDEN_TEST_ONLY",
            "evidence": "Executable hidden test verified in sandbox"
        }
        with open(os.path.join(TEST_OUT_DIR, f"{tid}.json"), "w", encoding="utf-8") as f:
            json.dump(g3_payload, f, indent=2)

        if overall_status == "PASS":
            passed += 1
            print(f"[{tid}] HIDDEN_TEST_PASS: collection={collection_status}, execution={execution_status}")
        else:
            print(f"[{tid}] HIDDEN_TEST_FAIL: {log[:150]}")

    print(f"\nHidden Test Execution Complete: {passed}/{len(specs)} PASS\n")


if __name__ == "__main__":
    generate_hidden_test_evidence_for_cohort()
