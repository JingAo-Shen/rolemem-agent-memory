#!/usr/bin/env python3
"""
scripts/evaluate_solution_constraints.py
Executes benchmark solution constraints (API Deprecation, Replacement Mechanism, Behavior Fidelity)
against any candidate generated code.

Outputs machine evidence to:
  data/solution_constraint_evidence/<tid>/<run_id>.json
"""

import os
import sys
import json
import re
import ast
from typing import Dict, Any, Tuple

sys.path.insert(0, "/code/rolemem-agent-memory")
from src.sandbox_secure import SecureSandboxExecutor
from scripts.run_causal_counterfactual_v2 import load_workspace

DATA_DIR = "/code/rolemem-agent-memory/data"
CONSTRAINTS_DIR = os.path.join(DATA_DIR, "solution_constraints")
OUTPUT_BASE_DIR = os.path.join(DATA_DIR, "solution_constraint_evidence")
FIXTURES_DIR = "/code/rolemem-agent-memory/fixtures_v2"
VENVS_ROOT = "/code/rolemem-agent-memory/.venvs"

os.makedirs(OUTPUT_BASE_DIR, exist_ok=True)


class SolutionConstraintEvaluator:
    def __init__(self, tid: str):
        self.tid = tid
        self.fixture_dir = os.path.join(FIXTURES_DIR, tid)
        constraint_p = os.path.join(CONSTRAINTS_DIR, f"{tid}.json")
        if os.path.exists(constraint_p):
            with open(constraint_p, "r", encoding="utf-8") as f:
                self.spec = json.load(f).get("constraints", {})
        else:
            self.spec = {}

        venv_bin = os.path.join(VENVS_ROOT, tid, "bin")
        if os.path.isdir(venv_bin):
            self.executor = SecureSandboxExecutor(custom_env_bin_dir=venv_bin)
        else:
            self.executor = SecureSandboxExecutor()

        self.target_ws = load_workspace(os.path.join(self.fixture_dir, "after"))
        with open(os.path.join(self.fixture_dir, "hidden_tests", "test_evaluation.py"), "r", encoding="utf-8") as f:
            self.test_code = f.read()

        manifest_line = {}
        with open(os.path.join(DATA_DIR, "track_a_reconstructed_manifest.jsonl"), "r") as f:
            for l in f:
                if l.strip():
                    item = json.loads(l)
                    if item.get("transition_id") == tid:
                        manifest_line = item
                        break
        self.target_file = manifest_line.get("target_file", self.spec.get("target_file", "solution.py"))
        self.is_control = manifest_line.get("track") in ["TRACK_A_EVOLUTION_CONTROL", "TRACK_A_API_EVOLUTION"]

    def evaluate_code(self, generated_code: str, run_id: str = "default") -> Dict[str, Any]:
        """Evaluates generated code against the 3 constraints."""
        out_dir = os.path.join(OUTPUT_BASE_DIR, self.tid)
        os.makedirs(out_dir, exist_ok=True)

        dep_gate_status = "PASS"
        dep_details = ""
        rep_gate_status = "PASS"
        rep_details = ""
        beh_gate_status = "PASS"
        beh_details = ""

        # 1. API Deprecation Gate
        if self.is_control:
            dep_gate_status = "NOT_APPLICABLE"
            dep_details = "Control transition without deprecation"
        else:
            dep_spec = self.spec.get("api_deprecation_gate", {})
            dep_sym = dep_spec.get("deprecated_symbol", "")
            short_sym = dep_sym.split(".")[-1] if dep_sym else ""

            # Check if code mentions deprecated symbol
            has_dep = False
            if short_sym and short_sym in generated_code:
                has_dep = True
            elif "__version__" in generated_code and ("jinja" in self.tid or "itsdangerous" in self.tid or "markupsafe" in self.tid):
                has_dep = True

            if has_dep:
                dep_gate_status = "FAIL"
                dep_details = f"Generated code invokes deprecated symbol '{short_sym or dep_sym}'"
            else:
                dep_gate_status = "PASS"
                dep_details = f"Code free of deprecated symbol '{short_sym or dep_sym}'"

        # 2. Replacement Mechanism Gate
        rep_spec = self.spec.get("replacement_mechanism_gate", {})
        prohibited = rep_spec.get("prohibited_returns", ["1.0", "dummy"])
        has_prohibited = any(p in generated_code for p in prohibited if p == "1.0" or p == "dummy")

        if has_prohibited:
            rep_gate_status = "FAIL"
            rep_details = "Code contains prohibited constant/dummy return"
        else:
            # Check for required mechanism presence
            if "jinja" in self.tid or "itsdangerous" in self.tid or "markupsafe" in self.tid:
                if "importlib.metadata" not in generated_code:
                    rep_gate_status = "FAIL"
                    rep_details = "Missing required importlib.metadata replacement"
                else:
                    rep_gate_status = "PASS"
                    rep_details = "importlib.metadata mechanism present"
            elif "flask" in self.tid:
                if "teardown_request" not in generated_code:
                    rep_gate_status = "FAIL"
                    rep_details = "Missing required teardown_request handler registration"
                else:
                    rep_gate_status = "PASS"
                    rep_details = "teardown_request mechanism present"
            elif "click" in self.tid:
                if "buffer" not in generated_code and "stdout" not in generated_code:
                    rep_gate_status = "FAIL"
                    rep_details = "Missing direct standard stream buffer access"
                else:
                    rep_gate_status = "PASS"
                    rep_details = "Direct stream buffer access present"
            elif "httpx" in self.tid:
                if "proxies" in generated_code:
                    rep_gate_status = "FAIL"
                    rep_details = "Uses deprecated proxies parameter"
                else:
                    rep_gate_status = "PASS"
                    rep_details = "Uses modern proxy parameter"
            else:
                rep_gate_status = "PASS"
                rep_details = "Replacement pattern satisfied"

        # 3. Behavior Fidelity Gate (pytest in Bubblewrap)
        pytest_pass, pytest_log = self.executor.execute_in_sandbox(
            workspace_files=self.target_ws,
            target_file=self.target_file,
            generated_code=generated_code,
            test_code=self.test_code
        )
        beh_gate_status = "PASS" if pytest_pass else "FAIL"
        beh_details = "Pytest execution passed" if pytest_pass else "Pytest execution failed"

        # Overall task success determination
        overall_pass = (
            (dep_gate_status in ["PASS", "NOT_APPLICABLE"]) and
            (rep_gate_status == "PASS") and
            (beh_gate_status == "PASS")
        )

        evidence = {
            "transition_id": self.tid,
            "run_id": run_id,
            "target_file": self.target_file,
            "api_deprecation_gate": {
                "status": dep_gate_status,
                "details": dep_details
            },
            "replacement_mechanism_gate": {
                "status": rep_gate_status,
                "details": rep_details
            },
            "behavior_fidelity_gate": {
                "status": beh_gate_status,
                "details": beh_details,
                "pytest_passed": pytest_pass,
                "log_snippet": pytest_log[-300:] if len(pytest_log) > 300 else pytest_log
            },
            "overall_constraint_status": "PASS" if overall_pass else "FAIL",
            "overall_status": "PASS" if overall_pass else "FAIL",
            "task_success": overall_pass
        }

        out_file = os.path.join(out_dir, f"{run_id}.json")
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(evidence, f, indent=2)

        return evidence


if __name__ == "__main__":
    if len(sys.argv) > 1:
        tid_arg = sys.argv[1]
        evaluator = SolutionConstraintEvaluator(tid_arg)
        with open(os.path.join(FIXTURES_DIR, tid_arg, "controls", "valid_solution.py")) as f:
            code = f.read()
        res = evaluator.evaluate_code(code, "valid_control_smoke")
        print(f"Smoke test for {tid_arg}: {res['overall_constraint_status']}")
    else:
        print("Usage: evaluate_solution_constraints.py <transition_id>")
