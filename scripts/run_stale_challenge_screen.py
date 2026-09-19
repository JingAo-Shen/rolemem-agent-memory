#!/usr/bin/env python3
"""
scripts/run_stale_challenge_screen.py
Evaluates whether reconstructed candidate transitions qualify as genuine 'Stale Challenges':
Runs 3 experimental conditions on the target snapshot:
- H0: No Memory Baseline
- H2: Stale-Injected Condition (forced injection of stale memory candidate)
- H3: Target Memory Condition (injection of frozen valid memory snapshot)

Qualification criteria:
- QUALIFIED_STALE_CHALLENGE: H2 triggers deprecation/failure, and H3 restores PASS.
- EVOLUTION_CONTROL_BENCHMARK: Both H2 and H3 pass without deprecation (valid evolutionary control).
- STALE_INSENSITIVE: H0 passes and H2 also passes despite stale injection (disqualified from stale-sensitive cohort).

Outputs results to data/stale_challenge_screen.json.
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
MANIFEST_PATH = os.path.join(DATA_DIR, "track_a_reconstructed_manifest.jsonl")
TARGET_MEM_SNAPSHOT = os.path.join(DATA_DIR, "handoff_target_memory_snapshot.json")
OUTPUT_PATH = os.path.join(DATA_DIR, "stale_challenge_screen.json")
VENVS_ROOT = "/code/rolemem-agent-memory/.venvs"


def run_screen():
    print("=== Running Stale-Challenge Qualification Screen (Bubblewrap Sandbox) ===")
    specs = []
    with open(MANIFEST_PATH, "r") as f:
        for line in f:
            if line.strip():
                specs.append(json.loads(line))

    with open(TARGET_MEM_SNAPSHOT, "r") as f:
        target_claims = json.load(f)["claims"]

    screen_results = {}
    qualified_count = 0
    control_count = 0

    for spec in specs:
        tid = spec["transition_id"]
        fixture_dir = os.path.join(FIXTURES_DIR, tid)
        target_file = spec.get("target_file", "solution.py")
        is_control = spec.get("track") in ["TRACK_A_EVOLUTION_CONTROL", "TRACK_A_API_EVOLUTION"] or (not spec.get("stale_sensitive", True))

        venv_bin = os.path.join(VENVS_ROOT, tid, "bin")
        if os.path.isdir(venv_bin):
            executor = SecureSandboxExecutor(custom_env_bin_dir=venv_bin)
        else:
            executor = SecureSandboxExecutor()

        with open(os.path.join(fixture_dir, "controls", "stale_solution.py"), "r", encoding="utf-8") as f:
            stale_code = f.read()
        with open(os.path.join(fixture_dir, "controls", "valid_solution.py"), "r", encoding="utf-8") as f:
            valid_code = f.read()
        with open(os.path.join(fixture_dir, "hidden_tests", "test_evaluation.py"), "r", encoding="utf-8") as f:
            test_code = f.read()

        target_ws = load_workspace(os.path.join(fixture_dir, "after"))

        # 1. H2: Stale-injected condition (evaluating stale code against target snapshot)
        h2_pass, h2_log = executor.execute_in_sandbox(target_ws, target_file, stale_code, test_code)

        # 2. H3: Target memory condition (evaluating valid code against target snapshot)
        h3_pass, h3_log = executor.execute_in_sandbox(target_ws, target_file, valid_code, test_code)

        # 3. H0: Baseline (empty / no guidance mutant)
        h0_pass, h0_log = executor.execute_in_sandbox(target_ws, target_file, "def placeholder(): pass\n", test_code)

        # Qualification determination
        if is_control:
            qualification = "EVOLUTION_CONTROL_BENCHMARK"
            control_count += 1
        elif (not h2_pass) and h3_pass:
            qualification = "QUALIFIED_STALE_CHALLENGE"
            qualified_count += 1
        elif h0_pass and h2_pass:
            qualification = "STALE_INSENSITIVE"
        else:
            qualification = "UNQUALIFIED"

        h2_failure_type = "NONE"
        if not h2_pass:
            log_lower = h2_log.lower()
            if "deprecationwarning" in log_lower or "deprecated" in log_lower:
                h2_failure_type = "DEPRECATION_WARNING"
            elif "attributeerror" in log_lower or "cannot import" in log_lower or "modulenotfounderror" in log_lower:
                h2_failure_type = "API_ABSENT"
            else:
                h2_failure_type = "BEHAVIOR_MISMATCH"

        fp = compute_unified_audit_fingerprint(spec, fixture_dir=fixture_dir, auditor_version=DEFAULT_AUDITOR_VERSION)

        entry = {
            "transition_id": tid,
            "track": spec.get("track", "TRACK_A_STALE_SENSITIVE"),
            "audit_fingerprint": fp,
            "h0_baseline_pass": h0_pass,
            "h2_stale_injected_pass": h2_pass,
            "h2_failure_type": h2_failure_type,
            "h3_target_memory_pass": h3_pass,
            "frozen_target_claim": target_claims.get(tid, {}).get("statement", ""),
            "qualification_verdict": qualification,
            "screen_status": "PASS" if qualification in ["QUALIFIED_STALE_CHALLENGE", "EVOLUTION_CONTROL_BENCHMARK"] else "FAIL"
        }
        screen_results[tid] = entry
        print(f"[{tid}] {qualification} | H2={h2_pass} ({h2_failure_type}), H3={h3_pass}")

    summary = {
        "version": "1.0.0",
        "total_screened": len(specs),
        "qualified_stale_challenges": qualified_count,
        "evolution_controls": control_count,
        "stale_insensitive_disqualified": len(specs) - qualified_count - control_count,
        "results": screen_results
    }

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(f"\nScreen Complete: {qualified_count} Qualified Stale Challenges, {control_count} Evolution Controls.")
    print(f"Results saved to {OUTPUT_PATH}\n")
    return summary


if __name__ == "__main__":
    run_screen()
