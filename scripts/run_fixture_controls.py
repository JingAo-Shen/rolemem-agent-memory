#!/usr/bin/env python3
"""
Run Fixture Controls in Bubblewrap Sandbox (Pilot-v1.2b).
Executes stale and valid solutions for all fixtures in fixtures_v2/ inside SecureSandboxExecutor:
- Stale solution must FAIL / trigger deprecation warning -> saved to controls/stale_result.json
- Valid solution must PASS -> saved to controls/valid_result.json
- Validates 100% control fidelity across the benchmark suite.
"""

import os
import sys
import json
import argparse
from typing import Dict, Any, List

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.sandbox_secure import SecureSandboxExecutor


def run_controls_for_fixture(fixture_dir: str, executor: SecureSandboxExecutor) -> Dict[str, Any]:
    t_id = os.path.basename(fixture_dir)
    meta_path = os.path.join(fixture_dir, "metadata.json")
    if not os.path.exists(meta_path):
        raise FileNotFoundError(f"Missing metadata.json in {fixture_dir}")

    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)

    target_file = meta.get("target_file", "solution.py")

    # 1. Load workspace files from after/
    after_dir = os.path.join(fixture_dir, "after")
    workspace_files = {}
    for root, _, files in os.walk(after_dir):
        for fn in files:
            fp = os.path.join(root, fn)
            rel = os.path.relpath(fp, after_dir)
            try:
                with open(fp, "r", encoding="utf-8") as f:
                    workspace_files[rel] = f.read()
            except UnicodeDecodeError:
                with open(fp, "r", encoding="utf-8", errors="ignore") as f:
                    workspace_files[rel] = f.read()

    # 2. Load hidden test
    test_path = os.path.join(fixture_dir, "hidden_tests", "test_evaluation.py")
    with open(test_path, "r", encoding="utf-8") as f:
        test_code = f.read()

    # 3. Load controls
    controls_dir = os.path.join(fixture_dir, "controls")
    stale_path = os.path.join(controls_dir, "stale_solution.py")
    valid_path = os.path.join(controls_dir, "valid_solution.py")

    with open(stale_path, "r", encoding="utf-8") as f:
        stale_code = f.read()
    with open(valid_path, "r", encoding="utf-8") as f:
        valid_code = f.read()

    print(f"\n[CONTROL] Testing {t_id}...")

    # Run stale
    stale_passed, stale_log = executor.execute_in_sandbox(
        workspace_files=workspace_files,
        target_file=target_file,
        generated_code=stale_code,
        test_code=test_code
    )
    stale_control_pass = (stale_passed is False)

    stale_record = {
        "transition_id": t_id,
        "control_type": "stale_solution",
        "expected": "FAIL",
        "passed": stale_passed,
        "control_pass": stale_control_pass,
        "log_preview": stale_log[:400]
    }
    with open(os.path.join(controls_dir, "stale_result.json"), "w", encoding="utf-8") as f:
        json.dump(stale_record, f, indent=2)

    # Run valid
    valid_passed, valid_log = executor.execute_in_sandbox(
        workspace_files=workspace_files,
        target_file=target_file,
        generated_code=valid_code,
        test_code=test_code
    )
    valid_control_pass = (valid_passed is True)

    valid_record = {
        "transition_id": t_id,
        "control_type": "valid_solution",
        "expected": "PASS",
        "passed": valid_passed,
        "control_pass": valid_control_pass,
        "log_preview": valid_log[:400]
    }
    with open(os.path.join(controls_dir, "valid_result.json"), "w", encoding="utf-8") as f:
        json.dump(valid_record, f, indent=2)

    status_str = "PASS" if (stale_control_pass and valid_control_pass) else "FAIL"
    print(f"  Stale Solution: passed={stale_passed} (Control: {'PASS' if stale_control_pass else 'FAIL'})")
    print(f"  Valid Solution: passed={valid_passed} (Control: {'PASS' if valid_control_pass else 'FAIL'})")
    print(f"  -> Fixture Control Overall: {status_str}")

    return {
        "transition_id": t_id,
        "stale_passed": stale_passed,
        "stale_control_pass": stale_control_pass,
        "valid_passed": valid_passed,
        "valid_control_pass": valid_control_pass,
        "overall_control_pass": (stale_control_pass and valid_control_pass)
    }


def main():
    parser = argparse.ArgumentParser(description="Run Fixture Controls in Bubblewrap Sandbox")
    parser.add_argument("--fixtures-dir", default="fixtures_v2", help="Root directory containing fixtures")
    args = parser.parse_args()

    if not os.path.exists(args.fixtures_dir):
        raise FileNotFoundError(f"Directory {args.fixtures_dir} not found")

    executor = SecureSandboxExecutor()
    fixtures = sorted([
        os.path.join(args.fixtures_dir, d) for d in os.listdir(args.fixtures_dir)
        if os.path.isdir(os.path.join(args.fixtures_dir, d)) and not d.startswith(".")
    ])

    results = []
    print(f"Found {len(fixtures)} fixtures in {args.fixtures_dir}/")

    for f_dir in fixtures:
        res = run_controls_for_fixture(f_dir, executor)
        results.append(res)

    print("\n" + "=" * 60)
    print("FIXTURE CONTROLS SUMMARY")
    print("=" * 60)
    all_passed = True
    for r in results:
        status = "PASS" if r["overall_control_pass"] else "FAIL"
        if not r["overall_control_pass"]:
            all_passed = False
        print(f"{r['transition_id']:<45} : {status} (StaleFail: {r['stale_control_pass']}, ValidPass: {r['valid_control_pass']})")

    print("=" * 60)
    if all_passed:
        print(f"ALL {len(results)} FIXTURES PASSED RIGOROUS CONTROLS AUDIT!")
    else:
        print("WARNING: One or more fixtures failed controls audit!")
        sys.exit(1)


if __name__ == "__main__":
    main()
