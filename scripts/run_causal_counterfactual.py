"""
scripts/run_causal_counterfactual.py
Executes the 2×2 Causal Counterfactual Matrix for RoleMem transitions:
  Cell (1,1): stale_solution on base snapshot
  Cell (1,2): stale_solution on target snapshot
  Cell (2,1): valid_solution on base snapshot
  Cell (2,2): valid_solution on target snapshot

Saves results to data/causal_counterfactual/<transition_id>.json.
Flags TRANSITION_NOT_CAUSAL if valid_solution already works identically in base snapshot
and stale_solution behaves identically between base and target.
"""

import os
import sys
import json
import glob
from typing import Dict, Any, List, Tuple

sys.path.insert(0, "/code/rolemem-agent-memory")
from src.sandbox_secure import SecureSandboxExecutor

SPECS_DIR = "/code/rolemem-agent-memory/data/specs"
FIXTURES_DIR = "/code/rolemem-agent-memory/fixtures_v2"
OUTPUT_DIR = "/code/rolemem-agent-memory/data/causal_counterfactual"
VENVS_ROOT = "/code/rolemem-agent-memory/.venvs"


def load_workspace(directory: str) -> Dict[str, str]:
    files = {}
    if not os.path.exists(directory):
        return files
    for root, _, filenames in os.walk(directory):
        for fn in filenames:
            abs_p = os.path.join(root, fn)
            rel_p = os.path.relpath(abs_p, directory)
            try:
                with open(abs_p, "r", encoding="utf-8", errors="ignore") as f:
                    files[rel_p] = f.read()
            except Exception:
                pass
    return files


def classify_failure_reason(passed: bool, log: str) -> str:
    if passed:
        return "NONE"
    log_lower = log.lower()
    if "deprecationwarning" in log_lower or "deprecated" in log_lower:
        return "DEPRECATION_WARNING"
    if "modulenotfounderror" in log_lower or "cannot import" in log_lower or "importerror" in log_lower:
        return "IMPORT_FAILURE"
    if "attributeerror" in log_lower:
        return "API_ABSENT"
    if "typeerror" in log_lower and any(kw in log_lower for kw in ["unexpected keyword", "missing", "takes", "positional argument"]):
        return "SIGNATURE_MISMATCH"
    if "assertionerror" in log_lower:
        return "BEHAVIOR_MISMATCH"
    if any(kw in log_lower for kw in ["internal error", "bwrap", "permission denied", "resource temporarily unavailable"]):
        return "ENVIRONMENT_FAILURE"
    return "TEST_EXPECTATION_ONLY"


def run_counterfactual_matrix(spec: Dict[str, Any]) -> Dict[str, Any]:
    tid = spec["transition_id"]
    fixture_dir = os.path.join(FIXTURES_DIR, tid)

    target_file = spec.get("target_file", "")
    venv_bin = os.path.join(VENVS_ROOT, tid, "bin")
    if os.path.isdir(venv_bin):
        executor = SecureSandboxExecutor(custom_env_bin_dir=venv_bin)
    else:
        executor = SecureSandboxExecutor()

    # Load solutions and test code
    stale_sol_p = os.path.join(fixture_dir, "controls", "stale_solution.py")
    valid_sol_p = os.path.join(fixture_dir, "controls", "valid_solution.py")
    hidden_test_p = os.path.join(fixture_dir, "hidden_tests", "test_evaluation.py")

    with open(stale_sol_p, "r", encoding="utf-8") as f:
        stale_code = f.read()
    with open(valid_sol_p, "r", encoding="utf-8") as f:
        valid_code = f.read()
    with open(hidden_test_p, "r", encoding="utf-8") as f:
        test_code = f.read()

    # Load snapshots
    base_ws = load_workspace(os.path.join(fixture_dir, "before"))
    target_ws = load_workspace(os.path.join(fixture_dir, "after"))

    # Cell 1: stale_solution on base snapshot
    p_stale_base, log_stale_base = executor.execute_in_sandbox(
        workspace_files=base_ws,
        target_file=target_file,
        generated_code=stale_code,
        test_code=test_code
    )

    # Cell 2: stale_solution on target snapshot
    p_stale_target, log_stale_target = executor.execute_in_sandbox(
        workspace_files=target_ws,
        target_file=target_file,
        generated_code=stale_code,
        test_code=test_code
    )

    # Cell 3: valid_solution on base snapshot
    p_valid_base, log_valid_base = executor.execute_in_sandbox(
        workspace_files=base_ws,
        target_file=target_file,
        generated_code=valid_code,
        test_code=test_code
    )

    # Cell 4: valid_solution on target snapshot
    p_valid_target, log_valid_target = executor.execute_in_sandbox(
        workspace_files=target_ws,
        target_file=target_file,
        generated_code=valid_code,
        test_code=test_code
    )


    matrix = {
        "stale_on_base": p_stale_base,
        "stale_on_target": p_stale_target,
        "valid_on_base": p_valid_base,
        "valid_on_target": p_valid_target
    }

    failure_taxonomy = {
        "stale_base_failure": classify_failure_reason(p_stale_base, log_stale_base),
        "stale_target_failure": classify_failure_reason(p_stale_target, log_stale_target),
        "valid_base_failure": classify_failure_reason(p_valid_base, log_valid_base),
        "valid_target_failure": classify_failure_reason(p_valid_target, log_valid_target),
    }

    # Causality Evaluation
    is_causal = False
    causality_status = "CAUSAL_PASS"
    rationale = []

    if not p_valid_target:
        causality_status = "TARGET_VALID_FAILED"
        rationale.append("valid_solution failed on target snapshot")
    elif p_stale_target:
        causality_status = "TARGET_STALE_NOT_INVALIDATED"
        rationale.append("stale_solution still passed on target snapshot without failure/warning")
    else:
        stale_fail_type = failure_taxonomy["stale_target_failure"]
        if stale_fail_type in ["ENVIRONMENT_FAILURE"]:
            causality_status = "ENVIRONMENT_FAILURE"
            rationale.append("stale_solution failed on target due to sandbox environment error")
        elif p_stale_base and not p_stale_target:
            is_causal = True
            rationale.append(f"Causal transition: stale passed on base, failed on target with {stale_fail_type}")
        elif not p_valid_base and p_valid_target:
            is_causal = True
            rationale.append(f"Feature introduction: valid action impossible on base ({failure_taxonomy['valid_base_failure']}), succeeds on target")
        else:
            causality_status = "TRANSITION_NOT_CAUSAL"
            rationale.append("stale and valid actions have identical behavior across base and target snapshots")

    return {
        "transition_id": tid,
        "stale_base": p_stale_base,
        "stale_target": p_stale_target,
        "valid_base": p_valid_base,
        "valid_target": p_valid_target,
        "matrix": matrix,
        "failure_taxonomy": failure_taxonomy,
        "causality_status": causality_status,
        "is_causal": is_causal,
        "rationale": "; ".join(rationale),
        "execution_logs": {
            "stale_base_preview": log_stale_base[:200],
            "stale_target_preview": log_stale_target[:200],
            "valid_base_preview": log_valid_base[:200],
            "valid_target_preview": log_valid_target[:200]
        }
    }


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    spec_files = sorted([f for f in os.listdir(SPECS_DIR) if f.endswith(".json")])

    print(f"=== Running 2×2 Causal Counterfactual Matrix on {len(spec_files)} transitions ===")
    total = len(spec_files)
    passed = 0

    for sp in spec_files:
        spec_path = os.path.join(SPECS_DIR, sp)
        with open(spec_path, "r", encoding="utf-8") as f:
            spec = json.load(f)

        tid = spec["transition_id"]
        res = run_counterfactual_matrix(spec)
        mat = res["matrix"]
        status = res["causality_status"]
        if res["is_causal"]:
            passed += 1
            print(f"[{tid}] CAUSAL PASS: stale(base={mat['stale_on_base']}, target={mat['stale_on_target']}), valid(base={mat['valid_on_base']}, target={mat['valid_on_target']})")
        else:
            print(f"[{tid}] CAUSAL FAIL ({status}): {res['rationale']}")

        out_path = os.path.join(OUTPUT_DIR, f"{tid}.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(res, f, indent=2)

    print(f"\n2×2 Causal Counterfactual Matrix Complete: {passed}/{total} PASS")


if __name__ == "__main__":
    main()
