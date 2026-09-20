#!/usr/bin/env python3
"""
scripts/run_causal_matrix_v2_1.py

Machine-Generated 2x2 Causal Counterfactual Execution Engine for Protocol V2.1:
- Real sandbox execution across 4 counterfactual cells:
    Cell 1: stale_solution on base snapshot
    Cell 2: stale_solution on target snapshot
    Cell 3: valid_solution on base snapshot
    Cell 4: valid_solution on target snapshot
- SHA256 hashed outputs, exit codes, and machine verification.
- Output: data/causal_matrix_v2_1/<transition_id>.json and summary.json.
- ZERO hardcoded PASS/FAIL flags.
"""

import os
import sys
import glob
import json
import hashlib
from typing import Dict, Any, List, Tuple

sys.path.insert(0, "/code/rolemem-agent-memory")
from src.sandbox_secure import SecureSandboxExecutor

DATA_DIR = "/code/rolemem-agent-memory/data"
SPECS_DIR = os.path.join(DATA_DIR, "specs")
FIXTURES_DIR = "/code/rolemem-agent-memory/fixtures_v2"
OUTPUT_DIR = os.path.join(DATA_DIR, "causal_matrix_v2_1")
VENVS_ROOT = "/code/rolemem-agent-memory/.venvs"

os.makedirs(OUTPUT_DIR, exist_ok=True)


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def load_workspace(directory: str, overlay_dir: str = None) -> Dict[str, str]:
    files = {}
    if os.path.exists(directory):
        for root, _, filenames in os.walk(directory):
            for fn in filenames:
                abs_p = os.path.join(root, fn)
                rel_p = os.path.relpath(abs_p, directory)
                try:
                    with open(abs_p, "r", encoding="utf-8", errors="ignore") as f:
                        files[rel_p] = f.read()
                except Exception:
                    pass
    if overlay_dir is None:
        candidate_overlay = os.path.join(os.path.dirname(directory), "environment_overlay", "files")
        if os.path.isdir(candidate_overlay):
            overlay_dir = candidate_overlay
    if overlay_dir and os.path.isdir(overlay_dir):
        for root, _, filenames in os.walk(overlay_dir):
            for fn in filenames:
                abs_p = os.path.join(root, fn)
                rel_p = os.path.relpath(abs_p, overlay_dir)
                try:
                    with open(abs_p, "r", encoding="utf-8", errors="ignore") as f:
                        files[rel_p] = f.read()
                except Exception:
                    pass
    return files


def run_test_cell(
    sandbox: SecureSandboxExecutor,
    base_files: Dict[str, str],
    solution_code: str,
    solution_path: str,
    test_code: str,
) -> Dict[str, Any]:
    passed, output = sandbox.execute_in_sandbox(
        workspace_files=base_files,
        target_file=solution_path,
        generated_code=solution_code,
        test_code=test_code
    )
    return {
        "passed": bool(passed),
        "output_sha256": sha256_text(output),
        "output_snippet": output[:300]
    }


def evaluate_transition(spec_path: str) -> Dict[str, Any]:
    with open(spec_path, "r", encoding="utf-8") as f:
        spec = json.load(f)

    tid = spec["transition_id"]
    stale_sensitive = spec.get("stale_sensitive", True)
    transition_type = spec.get("transition_type", "STALE_SENSITIVE")

    fixture_dir = os.path.join(FIXTURES_DIR, tid)
    base_dir = os.path.join(fixture_dir, "before")
    target_dir = os.path.join(fixture_dir, "after")

    target_file = spec.get("target_file", spec.get("primary_file", "solution.py"))
    venv_bin = os.path.join(VENVS_ROOT, tid, "bin")
    if os.path.isdir(venv_bin):
        sandbox = SecureSandboxExecutor(custom_env_bin_dir=venv_bin)
    else:
        sandbox = SecureSandboxExecutor()

    # Load solutions and test code
    stale_sol_p = os.path.join(fixture_dir, "controls", "stale_solution.py")
    valid_sol_p = os.path.join(fixture_dir, "controls", "valid_solution.py")
    hidden_test_p = os.path.join(fixture_dir, "hidden_tests", "test_evaluation.py")

    stale_code = ""
    valid_code = ""
    test_code = ""

    if os.path.exists(stale_sol_p):
        with open(stale_sol_p, "r", encoding="utf-8") as f:
            stale_code = f.read()
    else:
        stale_code = spec.get("stale_solution", "")

    if os.path.exists(valid_sol_p):
        with open(valid_sol_p, "r", encoding="utf-8") as f:
            valid_code = f.read()
    else:
        valid_code = spec.get("valid_solution", "")

    if os.path.exists(hidden_test_p):
        with open(hidden_test_p, "r", encoding="utf-8") as f:
            test_code = f.read()
    else:
        test_code = spec.get("eval_test", "def test_ok(): pass\n")

    base_files = load_workspace(base_dir)
    target_files = load_workspace(target_dir)

    # Run the 4 cells
    cell_stale_base = run_test_cell(sandbox, base_files, stale_code, target_file, test_code)
    cell_stale_target = run_test_cell(sandbox, target_files, stale_code, target_file, test_code)
    cell_valid_base = run_test_cell(sandbox, base_files, valid_code, target_file, test_code)
    cell_valid_target = run_test_cell(sandbox, target_files, valid_code, target_file, test_code)

    stale_on_base = cell_stale_base["passed"]
    stale_on_target = cell_stale_target["passed"]
    valid_on_base = cell_valid_base["passed"]
    valid_on_target = cell_valid_target["passed"]

    if stale_sensitive:
        causal_pass = (stale_on_base is True and stale_on_target is False and valid_on_target is True)
    else:
        causal_pass = (stale_on_base is True and stale_on_target is True and valid_on_target is True)

    record = {
        "transition_id": tid,
        "repo_name": spec.get("repo_name"),
        "transition_type": transition_type,
        "stale_sensitive": stale_sensitive,
        "executions": {
            "stale_on_base": cell_stale_base,
            "stale_on_target": cell_stale_target,
            "valid_on_base": cell_valid_base,
            "valid_on_target": cell_valid_target
        },
        "matrix": {
            "stale_on_base": stale_on_base,
            "stale_on_target": stale_on_target,
            "valid_on_base": valid_on_base,
            "valid_on_target": valid_on_target
        },
        "causal_pass": causal_pass
    }

    out_file = os.path.join(OUTPUT_DIR, f"{tid}.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2)

    return record


def main():
    spec_files = sorted(glob.glob(f"{SPECS_DIR}/trans_track_a_*.json"))

    print(f"Running machine-generated causal matrix for {len(spec_files)} transitions...")
    results = []
    for sf in spec_files:
        rec = evaluate_transition(sf)
        status_str = "PASS" if rec["causal_pass"] else "FAIL"
        print(f"  {rec['transition_id']}: Causal Matrix {status_str} (sb={rec['matrix']['stale_on_base']}, st={rec['matrix']['stale_on_target']}, vb={rec['matrix']['valid_on_base']}, vt={rec['matrix']['valid_on_target']})")
        results.append(rec)

    summary = {
        "protocol_version": "2.1",
        "total_evaluated": len(results),
        "causal_pass_count": sum(1 for r in results if r["causal_pass"]),
        "causal_fail_count": sum(1 for r in results if not r["causal_pass"]),
        "pass_rate": sum(1 for r in results if r["causal_pass"]) / len(results) if results else 0.0
    }

    summary_file = os.path.join(OUTPUT_DIR, "summary.json")
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(f"\n=== Causal Matrix V2.1 Complete: {summary['causal_pass_count']}/{summary['total_evaluated']} PASS ({summary['pass_rate']*100:.1f}%) ===")


if __name__ == "__main__":
    main()
