"""
scripts/audit_semantic_coherence.py
Audits 10-layer semantic coherence for benchmark transitions:
PR change ↔ repository_change ↔ causality_assertions ↔ stale_memory ↔ valid_memory
↔ current_task ↔ target_file/target_symbol ↔ hidden test ↔ stale control ↔ valid control

Output saved to data/semantic_audit/<transition_id>.json
"""

import os
import ast
import json
import re
from typing import Dict, Any, List, Tuple


SPECS_DIR = "/code/rolemem-agent-memory/data/specs"
FIXTURES_DIR = "/code/rolemem-agent-memory/fixtures_v2"
SEMANTIC_AUDIT_DIR = "/code/rolemem-agent-memory/data/semantic_audit"


def extract_imported_names(code: str) -> List[Tuple[str, str]]:
    """Returns list of (module, symbol) imported."""
    imports = []
    try:
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    imports.append((node.module or "", alias.name))
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(("", alias.name))
    except SyntaxError:
        pass
    return imports


def extract_defined_symbols(code: str) -> List[str]:
    """Returns list of top-level function and class names defined in code."""
    defs = []
    try:
        tree = ast.parse(code)
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                defs.append(node.name)
    except SyntaxError:
        pass
    return defs


def audit_coherence(spec: Dict[str, Any]) -> Dict[str, Any]:
    tid = spec["transition_id"]
    fixture_dir = os.path.join(FIXTURES_DIR, tid)

    target_file = spec.get("target_file", "")
    target_mod = os.path.splitext(target_file)[0]
    target_sym = spec.get("target_symbol", "")

    layers = {}
    errors = []

    # Layer 1: PR change vs repository_change
    rep_change = spec.get("repository_change", "")
    chg_syms = spec.get("changed_symbols", [])
    dep_syms = spec.get("deprecated_symbols", [])
    rep_syms = spec.get("replacement_symbols", [])
    all_sym_names = [s.split(".")[-1] for s in chg_syms + dep_syms + rep_syms]

    l1_match = any(sym.lower() in rep_change.lower() for sym in all_sym_names)
    layers["pr_vs_repo_change"] = {
        "status": "PASS" if l1_match else "FAIL",
        "repository_change": rep_change,
        "symbols_checked": all_sym_names
    }
    if not l1_match:
        errors.append(f"repository_change does not mention any transition symbols: {all_sym_names}")

    # Layer 2: repository_change vs causality_assertions
    assertions = spec.get("causality_assertions", [])
    l2_match = len(assertions) > 0 and all(
        a.get("symbol") in all_sym_names or any(s in a.get("symbol", "") for s in all_sym_names)
        for a in assertions
    )
    layers["repo_change_vs_causality"] = {
        "status": "PASS" if l2_match else "FAIL",
        "assertions": assertions
    }
    if not l2_match:
        errors.append(f"causality_assertions ({len(assertions)}) do not map to transition symbols")

    # Layer 3: stale_memory vs valid_memory semantics
    stale_mem = spec.get("stale_memory_candidate", "")
    valid_mem = spec.get("valid_memory_candidate", "")
    l3_distinct = (stale_mem != valid_mem) and len(stale_mem) > 10 and len(valid_mem) > 10
    layers["memory_distinctness"] = {
        "status": "PASS" if l3_distinct else "FAIL",
        "stale_memory": stale_mem,
        "valid_memory": valid_mem
    }
    if not l3_distinct:
        errors.append("stale_memory_candidate and valid_memory_candidate are identical or underspecified")

    # Layer 4: current_task vs target_file / target_symbol
    task = spec.get("current_task", "")
    l4_file_in_task = target_file in task
    l4_sym_in_task = target_sym in task
    l4_match = l4_file_in_task and l4_sym_in_task
    layers["task_vs_target"] = {
        "status": "PASS" if l4_match else "FAIL",
        "task": task,
        "target_file": target_file,
        "target_symbol": target_sym,
        "file_in_task": l4_file_in_task,
        "sym_in_task": l4_sym_in_task
    }
    if not l4_match:
        errors.append(f"current_task does not reference target_file ({target_file}) or target_symbol ({target_sym})")

    # Read fixture files
    test_eval_path = os.path.join(fixture_dir, "hidden_tests", "test_evaluation.py")
    stale_sol_path = os.path.join(fixture_dir, "controls", "stale_solution.py")
    valid_sol_path = os.path.join(fixture_dir, "controls", "valid_solution.py")

    test_eval_code = ""
    stale_sol_code = ""
    valid_sol_code = ""

    if os.path.exists(test_eval_path):
        with open(test_eval_path, "r", encoding="utf-8") as f:
            test_eval_code = f.read()
    if os.path.exists(stale_sol_path):
        with open(stale_sol_path, "r", encoding="utf-8") as f:
            stale_sol_code = f.read()
    if os.path.exists(valid_sol_path):
        with open(valid_sol_path, "r", encoding="utf-8") as f:
            valid_sol_code = f.read()

    # Layer 5: target_symbol vs hidden test
    # Hidden test must import target_symbol from target_mod or invoke target_sym
    test_imports = extract_imported_names(test_eval_code)
    test_targets = [(m, s) for m, s in test_imports if s == target_sym or m == target_mod]
    l5_match = len(test_targets) > 0 or (target_sym in test_eval_code and target_mod in test_eval_code)
    layers["hidden_test_coherence"] = {
        "status": "PASS" if l5_match else "FAIL",
        "expected_module": target_mod,
        "expected_symbol": target_sym,
        "detected_imports": test_imports
    }
    if not l5_match:
        errors.append(f"hidden_tests/test_evaluation.py does not import {target_sym} from {target_mod}")

    # Layer 6: target_symbol vs controls (stale and valid solutions)
    stale_defs = extract_defined_symbols(stale_sol_code)
    valid_defs = extract_defined_symbols(valid_sol_code)
    l6_stale = target_sym in stale_defs or target_sym in stale_sol_code
    l6_valid = target_sym in valid_defs or target_sym in valid_sol_code
    l6_match = l6_stale and l6_valid
    layers["controls_definition_coherence"] = {
        "status": "PASS" if l6_match else "FAIL",
        "stale_defines_target": l6_stale,
        "valid_defines_target": l6_valid,
        "stale_defs": stale_defs,
        "valid_defs": valid_defs
    }
    if not l6_match:
        errors.append(f"controls do not define target_symbol '{target_sym}' (stale_defines={l6_stale}, valid_defines={l6_valid})")

    # Overall coherence
    overall_status = "PASS" if len(errors) == 0 else "FAIL"

    return {
        "transition_id": tid,
        "overall_status": overall_status,
        "layers": layers,
        "errors": errors
    }


def main():
    os.makedirs(SEMANTIC_AUDIT_DIR, exist_ok=True)
    spec_files = sorted([f for f in os.listdir(SPECS_DIR) if f.endswith(".json")])

    print(f"=== Running Semantic Coherence Audit on {len(spec_files)} transitions ===")
    total = len(spec_files)
    passed = 0

    for sp in spec_files:
        spec_path = os.path.join(SPECS_DIR, sp)
        with open(spec_path, "r", encoding="utf-8") as f:
            spec = json.load(f)

        res = audit_coherence(spec)
        tid = res["transition_id"]
        status = res["overall_status"]
        if status == "PASS":
            passed += 1
            print(f"[{tid}] COHERENCE PASS")
        else:
            print(f"[{tid}] COHERENCE FAIL: {res['errors']}")

        out_file = os.path.join(SEMANTIC_AUDIT_DIR, f"{tid}.json")
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(res, f, indent=2)

    print(f"\nSemantic Coherence Result: {passed}/{total} PASS")


if __name__ == "__main__":
    main()
