"""
scripts/build_transition_environment.py
Constructs and validates per-transition virtual environments for historical Python transitions.
Uses `uv` for ultra-fast, deterministic virtual environment creation and package installation.
"""

import os
import sys
import json
import subprocess
from typing import Dict, Any, Optional

SPECS_DIR = "/code/rolemem-agent-memory/data/specs"
VENVS_DIR = "/code/rolemem-agent-memory/.venvs"
REPO_CACHE_DIR = "/code/repo_cache"


def get_interpreter_for_version(py_ver: str) -> str:
    """Find installed interpreter matching requested python version."""
    if py_ver.startswith("3.10"):
        if os.path.exists("/usr/bin/python3.10"):
            return "/usr/bin/python3.10"
        return "python3.10"
    if py_ver.startswith("3.13"):
        if os.path.exists("/root/anaconda3/bin/python3.13"):
            return "/root/anaconda3/bin/python3.13"
        return sys.executable
    return sys.executable


def build_environment_for_spec(spec: Dict[str, Any], force_rebuild: bool = False) -> Dict[str, Any]:
    """Build or verify virtual environment for a given transition spec."""
    tid = spec["transition_id"]
    env_info = spec.get("environment", {})
    py_ver = env_info.get("python_version", "3.13")
    deps = env_info.get("dependency_constraints", ["pytest>=8.0.0"])

    venv_path = os.path.join(VENVS_DIR, tid)
    python_bin = os.path.join(venv_path, "bin", "python")
    pytest_bin = os.path.join(venv_path, "bin", "pytest")

    if os.path.exists(python_bin) and not force_rebuild:
        # Quick health check
        chk = subprocess.run([python_bin, "--version"], capture_output=True, text=True)
        if chk.returncode == 0:
            return {
                "transition_id": tid,
                "status": "READY",
                "python_bin": python_bin,
                "pytest_bin": pytest_bin,
                "python_version": chk.stdout.strip(),
                "dependencies": deps
            }

    os.makedirs(VENVS_DIR, exist_ok=True)
    interp = get_interpreter_for_version(py_ver)

    # 1. Create venv with uv
    create_cmd = ["uv", "venv", "--python", interp, venv_path]
    c_res = subprocess.run(create_cmd, capture_output=True, text=True)
    if c_res.returncode != 0:
        return {
            "transition_id": tid,
            "status": "CREATION_FAILED",
            "error": c_res.stderr.strip()
        }

    # 2. Install dependencies with uv pip
    if deps:
        install_cmd = ["uv", "pip", "install", "--python", python_bin] + deps
        i_res = subprocess.run(install_cmd, capture_output=True, text=True)
        if i_res.returncode != 0:
            return {
                "transition_id": tid,
                "status": "INSTALL_FAILED",
                "error": i_res.stderr.strip()
            }

    chk = subprocess.run([python_bin, "--version"], capture_output=True, text=True)
    return {
        "transition_id": tid,
        "status": "READY",
        "python_bin": python_bin,
        "pytest_bin": pytest_bin,
        "python_version": chk.stdout.strip(),
        "dependencies": deps
    }


def build_all_environments(force_rebuild: bool = False) -> Dict[str, Any]:
    """Build environments for all transition specs in data/specs/."""
    results = {}
    if not os.path.exists(SPECS_DIR):
        print(f"Specs directory not found at {SPECS_DIR}")
        return results

    for fname in sorted(os.listdir(SPECS_DIR)):
        if not fname.endswith(".json"):
            continue
        spec_path = os.path.join(SPECS_DIR, fname)
        with open(spec_path, "r", encoding="utf-8") as f:
            spec = json.load(f)
        tid = spec.get("transition_id")
        res = build_environment_for_spec(spec, force_rebuild=force_rebuild)
        results[tid] = res
        print(f"[{res['status']}] {tid} -> {res.get('python_version', 'error')} ({res.get('python_bin', '')})")

    return results


if __name__ == "__main__":
    force = "--force" in sys.argv
    build_all_environments(force_rebuild=force)
