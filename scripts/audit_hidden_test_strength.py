#!/usr/bin/env python3
"""
scripts/audit_hidden_test_strength.py
Executes mutation testing against hidden tests across all reconstructed Track A transitions.
Tests 8 invalid mutants (M1-M8) per transition in the Bubblewrap sandbox.

Hard requirements:
1. Constant return (M2) MUST have 0.0% bypass rate across all transitions.
2. Each transition must achieve Mutation Kill Rate >= 0.80.
3. Outputs machine audit evidence to data/test_strength/<tid>.json.
"""

import os
import sys
import json
from typing import Dict, Any, List

sys.path.insert(0, "/code/rolemem-agent-memory")
from src.sandbox_secure import SecureSandboxExecutor
from src.fingerprint import compute_unified_audit_fingerprint, DEFAULT_AUDITOR_VERSION
from scripts.run_causal_counterfactual_v2 import load_workspace

DATA_DIR = "/code/rolemem-agent-memory/data"
FIXTURES_DIR = "/code/rolemem-agent-memory/fixtures_v2"
OUTPUT_DIR = os.path.join(DATA_DIR, "test_strength")
MANIFEST_PATH = os.path.join(DATA_DIR, "track_a_reconstructed_manifest.jsonl")
VENVS_ROOT = "/code/rolemem-agent-memory/.venvs"

os.makedirs(OUTPUT_DIR, exist_ok=True)


def get_mutants_for_transition(tid: str, fixture_dir: str) -> Dict[str, Dict[str, str]]:
    with open(os.path.join(fixture_dir, "controls", "stale_solution.py"), "r", encoding="utf-8") as f:
        stale_code = f.read()

    mutants = {}

    if tid == "trans_track_a_01_click_stream_deprecations":
        mutants = {
            "M1_return_none": {"desc": "return None", "code": "def get_io_stream(name: str):\n    return None\n"},
            "M2_constant_return": {"desc": "return constant string", "code": "def get_io_stream(name: str):\n    return '1.0'\n"},
            "M3_noop_pass": {"desc": "pass / no-op", "code": "def get_io_stream(name: str):\n    pass\n"},
            "M4_try_except_dummy": {"desc": "try/except return dummy", "code": "def get_io_stream(name: str):\n    try:\n        return None\n    except Exception:\n        return 'dummy'\n"},
            "M5_stale_solution": {"desc": "deprecated API call", "code": stale_code},
            "M6_mismatched_signature": {"desc": "wrong signature / no arguments", "code": "import sys\ndef get_io_stream():\n    return sys.stdout.buffer\n"},
            "M7_missing_attribute": {"desc": "missing target symbol", "code": "def other_helper():\n    pass\n"},
            "M8_static_mock": {"desc": "static mock object", "code": "class FakeStream:\n    pass\ndef get_io_stream(name: str):\n    return FakeStream()\n"},
        }
    elif tid == "trans_track_a_02_flask_should_ignore_error":
        mutants = {
            "M1_return_none": {"desc": "return None callable", "code": "def CustomApp(*args, **kwargs):\n    return None\n"},
            "M2_constant_return": {"desc": "return constant string", "code": "def CustomApp(*args, **kwargs):\n    return '1.0'\n"},
            "M3_noop_pass": {"desc": "empty class pass", "code": "class CustomApp:\n    pass\n"},
            "M4_try_except_dummy": {"desc": "try/except return dummy", "code": "def CustomApp(*args, **kwargs):\n    try:\n        return None\n    except Exception:\n        return 'dummy'\n"},
            "M5_stale_solution": {"desc": "stale should_ignore_error override", "code": stale_code},
            "M6_wrong_method_override": {"desc": "wrong replacement override", "code": "from flask import Flask\nclass CustomApp(Flask):\n    def teardown_request(self):\n        pass\n"},
            "M7_missing_attribute": {"desc": "missing CustomApp class", "code": "class UnrelatedApp:\n    pass\n"},
            "M8_static_mock": {"desc": "mock without Flask inheritance", "code": "class CustomApp:\n    def __init__(self, *args, **kwargs): pass\n    def route(self, *a): return lambda f: f\n    def test_client(self):\n        class C:\n            def get(self, *a):\n                class R: status_code = 200; data = b'ok'\n                return R()\n        return C()\n"},
        }
    elif tid == "trans_track_a_03_werkzeug_environ_property":
        mutants = {
            "M1_return_none": {"desc": "return None", "code": "def create_header_property(key: str):\n    return None\n"},
            "M2_constant_return": {"desc": "return constant string", "code": "def create_header_property(key: str):\n    return '1.0'\n"},
            "M3_noop_pass": {"desc": "pass / no-op", "code": "def create_header_property(key: str):\n    pass\n"},
            "M4_try_except_dummy": {"desc": "try/except return dummy", "code": "def create_header_property(key: str):\n    try:\n        return None\n    except Exception:\n        return 'dummy'\n"},
            "M5_stale_solution": {"desc": "stale environ_property", "code": stale_code},
            "M6_mismatched_signature": {"desc": "wrong signature", "code": "def create_header_property():\n    return property(lambda self: '')\n"},
            "M7_missing_attribute": {"desc": "missing create_header_property", "code": "def unrelated():\n    pass\n"},
            "M8_static_mock": {"desc": "static string return instead of descriptor", "code": "def create_header_property(key: str):\n    return 'localhost'\n"},
        }
    elif tid == "trans_track_a_04_jinja_version_deprecation":
        mutants = {
            "M1_return_none": {"desc": "return None", "code": "def get_engine_version() -> str:\n    return None\n"},
            "M2_constant_return": {"desc": "return constant string", "code": "def get_engine_version() -> str:\n    return '1.0'\n"},
            "M3_noop_pass": {"desc": "pass / no-op", "code": "def get_engine_version() -> str:\n    pass\n"},
            "M4_try_except_dummy": {"desc": "try/except return dummy", "code": "def get_engine_version() -> str:\n    try:\n        return None\n    except Exception:\n        return 'dummy'\n"},
            "M5_stale_solution": {"desc": "stale jinja2.__version__ read", "code": stale_code},
            "M6_wrong_package_arg": {"desc": "metadata lookup for wrong package", "code": "import importlib.metadata\ndef get_engine_version() -> str:\n    return importlib.metadata.version('wrong_pkg')\n"},
            "M7_missing_attribute": {"desc": "missing function", "code": "def other(): pass\n"},
            "M8_static_mock": {"desc": "static string mock bypassing metadata", "code": "def get_engine_version() -> str:\n    return '3.1.5'\n"},
        }
    elif tid == "trans_track_a_05_itsdangerous_version_removal":
        mutants = {
            "M1_return_none": {"desc": "return None", "code": "def get_package_version() -> str:\n    return None\n"},
            "M2_constant_return": {"desc": "return constant string", "code": "def get_package_version() -> str:\n    return '1.0'\n"},
            "M3_noop_pass": {"desc": "pass / no-op", "code": "def get_package_version() -> str:\n    pass\n"},
            "M4_try_except_dummy": {"desc": "try/except return dummy", "code": "def get_package_version() -> str:\n    try:\n        return None\n    except Exception:\n        return 'dummy'\n"},
            "M5_stale_solution": {"desc": "stale itsdangerous.__version__ read", "code": stale_code},
            "M6_wrong_package_arg": {"desc": "metadata lookup for wrong package", "code": "import importlib.metadata\ndef get_package_version() -> str:\n    return importlib.metadata.version('wrong_pkg')\n"},
            "M7_missing_attribute": {"desc": "missing function", "code": "def other(): pass\n"},
            "M8_static_mock": {"desc": "static string mock bypassing metadata", "code": "def get_package_version() -> str:\n    return '2.2.0'\n"},
        }
    elif tid == "trans_track_a_06_markupsafe_version_removal":
        mutants = {
            "M1_return_none": {"desc": "return None", "code": "def get_library_version() -> str:\n    return None\n"},
            "M2_constant_return": {"desc": "return constant string", "code": "def get_library_version() -> str:\n    return '1.0'\n"},
            "M3_noop_pass": {"desc": "pass / no-op", "code": "def get_library_version() -> str:\n    pass\n"},
            "M4_try_except_dummy": {"desc": "try/except return dummy", "code": "def get_library_version() -> str:\n    try:\n        return None\n    except Exception:\n        return 'dummy'\n"},
            "M5_stale_solution": {"desc": "stale markupsafe.__version__ read", "code": stale_code},
            "M6_wrong_package_arg": {"desc": "metadata lookup for wrong package", "code": "import importlib.metadata\ndef get_library_version() -> str:\n    return importlib.metadata.version('wrong_pkg')\n"},
            "M7_missing_attribute": {"desc": "missing function", "code": "def other(): pass\n"},
            "M8_static_mock": {"desc": "static string mock bypassing metadata", "code": "def get_library_version() -> str:\n    return '3.1.0'\n"},
        }
    elif tid == "trans_track_a_07_pluggy_varnames_noself":
        mutants = {
            "M1_return_none": {"desc": "return None", "code": "def extract_spec_varnames(func=None):\n    return None\n"},
            "M2_constant_return": {"desc": "return constant string", "code": "def extract_spec_varnames(func=None):\n    return '1.0'\n"},
            "M3_noop_pass": {"desc": "pass / no-op", "code": "def extract_spec_varnames(func=None):\n    pass\n"},
            "M4_try_except_dummy": {"desc": "try/except return dummy", "code": "def extract_spec_varnames(func=None):\n    try:\n        return None\n    except Exception:\n        return 'dummy'\n"},
            "M5_stale_solution": {"desc": "stale legacy_noself=True call", "code": stale_code},
            "M6_mismatched_signature": {"desc": "wrong signature / no arguments", "code": "def extract_spec_varnames():\n    return ()\n"},
            "M7_missing_attribute": {"desc": "missing function", "code": "def other(): pass\n"},
            "M8_static_mock": {"desc": "static tuple mock", "code": "def extract_spec_varnames(func=None):\n    return (('dummy', 'a', 'b'), ())\n"},
        }
    elif tid == "trans_track_a_08_attrs_py313_replace_control":
        prefix = "import attr\n@attr.s(auto_attribs=True)\nclass Point:\n    x: int\n    y: int\ndef create_point(x: int, y: int):\n    return Point(x, y)\n"
        mutants = {
            "M1_return_none": {"desc": "return None", "code": prefix + "def replace_point(pt, **changes):\n    return None\n", "expected_to_fail": True},
            "M2_constant_return": {"desc": "return constant string", "code": prefix + "def replace_point(pt, **changes):\n    return '1.0'\n", "expected_to_fail": True},
            "M3_noop_pass": {"desc": "pass / no-op", "code": prefix + "def replace_point(pt, **changes):\n    pass\n", "expected_to_fail": True},
            "M4_try_except_dummy": {"desc": "try/except return dummy", "code": prefix + "def replace_point(pt, **changes):\n    return 'dummy'\n", "expected_to_fail": True},
            "M5_stale_solution": {"desc": "control evolve call (EXPECTED_SURVIVOR_CONTROL)", "code": stale_code, "expected_to_fail": False},
            "M6_mismatched_signature": {"desc": "wrong signature", "code": prefix + "def replace_point(pt):\n    return pt\n", "expected_to_fail": True},
            "M7_missing_attribute": {"desc": "missing replace_point", "code": prefix, "expected_to_fail": True},
            "M8_static_mock": {"desc": "static object mock", "code": prefix + "def replace_point(pt, **changes):\n    class P: x = 30; y = 20\n    return P()\n", "expected_to_fail": True},
        }
    elif tid == "trans_track_a_09_virtualenv_drop_py38_control":
        mutants = {
            "M1_return_none": {"desc": "return None", "code": "def requires_pyvenv_patch(info):\n    return None\n"},
            "M2_constant_return": {"desc": "return constant string", "code": "def requires_pyvenv_patch(info):\n    return '1.0'\n"},
            "M3_noop_pass": {"desc": "pass / no-op", "code": "def requires_pyvenv_patch(info):\n    pass\n"},
            "M4_try_except_dummy": {"desc": "try/except return dummy", "code": "def requires_pyvenv_patch(info):\n    try:\n        return None\n    except Exception:\n        return 'dummy'\n"},
            "M5_stale_solution": {"desc": "calls dropped pyvenv_launch_patch_active", "code": stale_code},
            "M6_mismatched_signature": {"desc": "wrong signature", "code": "def requires_pyvenv_patch():\n    return False\n"},
            "M7_missing_attribute": {"desc": "missing function", "code": "def other(): pass\n"},
            "M8_static_mock": {"desc": "string boolean instead of bool", "code": "def requires_pyvenv_patch(info):\n    return 'False'\n"},
        }
    elif tid == "trans_track_a_10_httpx_client_proxies_deprecation":
        mutants = {
            "M1_return_none": {"desc": "return None", "code": "def build_proxied_client(proxy_url: str):\n    return None\n"},
            "M2_constant_return": {"desc": "return constant string", "code": "def build_proxied_client(proxy_url: str):\n    return '1.0'\n"},
            "M3_noop_pass": {"desc": "pass / no-op", "code": "def build_proxied_client(proxy_url: str):\n    pass\n"},
            "M4_try_except_dummy": {"desc": "try/except return dummy", "code": "def build_proxied_client(proxy_url: str):\n    try:\n        return None\n    except Exception:\n        return 'dummy'\n"},
            "M5_stale_solution": {"desc": "calls deprecated proxies param", "code": stale_code},
            "M6_mismatched_signature": {"desc": "wrong signature", "code": "import httpx\ndef build_proxied_client():\n    return httpx.Client()\n"},
            "M7_missing_attribute": {"desc": "missing function", "code": "def other(): pass\n"},
            "M8_static_mock": {"desc": "fake client mock", "code": "class DummyClient:\n    _transport = 'dummy'\ndef build_proxied_client(proxy_url: str):\n    return DummyClient()\n"},
        }

    return mutants


def run_mutation_audit():
    print("=== Running Hidden-Test Strength & Mutation Testing Audit (Bubblewrap) ===")
    specs = []
    with open(MANIFEST_PATH, "r") as f:
        for line in f:
            if line.strip():
                specs.append(json.loads(line))

    all_results = {}
    constant_return_bypasses = 0
    total_mutants = 0
    total_killed = 0

    for spec in specs:
        tid = spec["transition_id"]
        fixture_dir = os.path.join(FIXTURES_DIR, tid)
        target_file = spec.get("target_file", "solution.py")

        venv_bin = os.path.join(VENVS_ROOT, tid, "bin")
        if os.path.isdir(venv_bin):
            executor = SecureSandboxExecutor(custom_env_bin_dir=venv_bin)
        else:
            executor = SecureSandboxExecutor()

        with open(os.path.join(fixture_dir, "hidden_tests", "test_evaluation.py"), "r", encoding="utf-8") as f:
            test_code = f.read()

        target_ws = load_workspace(os.path.join(fixture_dir, "after"))
        mutants = get_mutants_for_transition(tid, fixture_dir)

        mutant_evals = {}
        killed_count = 0
        invalid_count = 0
        invalid_killed = 0

        for mid, mdata in mutants.items():
            expected_fail = mdata.get("expected_to_fail", True)
            total_mutants += 1
            if expected_fail:
                invalid_count += 1

            res, log = executor.execute_in_sandbox(
                workspace_files=target_ws,
                target_file=target_file,
                generated_code=mdata["code"],
                test_code=test_code
            )
            # A mutant is killed if the test FAILS (res == False)
            is_killed = not res
            if is_killed:
                killed_count += 1
                total_killed += 1
                if expected_fail:
                    invalid_killed += 1

            if mid == "M2_constant_return" and not is_killed:
                constant_return_bypasses += 1

            status_str = "KILLED" if is_killed else ("EXPECTED_SURVIVOR" if not expected_fail else "SURVIVED")
            mutant_evals[mid] = {
                "description": mdata["desc"],
                "expected_to_fail": expected_fail,
                "passed_test": res,
                "killed": is_killed,
                "status": status_str,
                "log_snippet": log[-300:] if len(log) > 300 else log
            }

        kill_rate = invalid_killed / invalid_count if invalid_count else 0.0
        meets_threshold = kill_rate >= 0.80
        m2_killed = mutant_evals.get("M2_constant_return", {}).get("killed", False)

        fp = compute_unified_audit_fingerprint(spec, fixture_dir=fixture_dir, auditor_version=DEFAULT_AUDITOR_VERSION)

        audit_payload = {
            "transition_id": tid,
            "audit_fingerprint": fp,
            "total_mutants": len(mutants),
            "invalid_mutants_count": invalid_count,
            "invalid_mutants_killed": invalid_killed,
            "killed_mutants": killed_count,
            "mutation_kill_rate": round(kill_rate, 4),
            "constant_return_killed": m2_killed,
            "constant_return_bypass": not m2_killed,
            "meets_kill_rate_threshold": meets_threshold,
            "audit_status": "PASS" if meets_threshold and m2_killed else "FAIL",
            "mutants": mutant_evals
        }

        out_path = os.path.join(OUTPUT_DIR, f"{tid}.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(audit_payload, f, indent=2)

        all_results[tid] = audit_payload

        status_str = "PASS" if meets_threshold and m2_killed else "FAIL"
        print(f"[{tid}] {status_str} | Invalid Kill Rate: {invalid_killed}/{invalid_count} ({kill_rate*100:.1f}%) | M2_Killed: {m2_killed}")

    total_invalid = sum(r["invalid_mutants_count"] for r in all_results.values())
    total_invalid_killed = sum(r["invalid_mutants_killed"] for r in all_results.values())
    overall_kill_rate = total_invalid_killed / total_invalid if total_invalid else 0.0
    print("\n=== Audit Summary ===")
    print(f"Total Mutants Evaluated: {total_mutants}")
    print(f"Total Invalid Mutants (expected to fail): {total_invalid}")
    print(f"Total Invalid Mutants Killed: {total_invalid_killed} ({overall_kill_rate*100:.1f}%)")
    print(f"Constant Return Bypasses: {constant_return_bypasses} (0.0% required)")

    assert constant_return_bypasses == 0, f"FAILED: {constant_return_bypasses} constant return mutants bypassed hidden tests!"
    for tid, res in all_results.items():
        assert res["meets_kill_rate_threshold"], f"FAILED: {tid} mutation kill rate {res['mutation_kill_rate']} < 0.80"

    print("All 10 transitions PASSED Hidden-Test Strength & Mutation Testing Audit!\n")
    return all_results


if __name__ == "__main__":
    run_mutation_audit()
