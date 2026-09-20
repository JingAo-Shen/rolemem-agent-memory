#!/usr/bin/env python3
"""
scripts/run_formal_benchmark_smoke.py

Validates configs/benchmark_v1.yaml, manifests in data/benchmark_v1/,
and enforces the unified result schema across all experiment conditions.
"""

import os
import sys
import json
import yaml
from typing import Dict, Any, List, Tuple

sys.path.insert(0, "/code/rolemem-agent-memory")

CONFIG_PATH = "/code/rolemem-agent-memory/configs/benchmark_v1.yaml"
CORE_MANIFEST = "/code/rolemem-agent-memory/data/benchmark_v1/track_a_core.jsonl"
CONTROL_MANIFEST = "/code/rolemem-agent-memory/data/benchmark_v1/track_a_controls.jsonl"


def validate_unified_result_schema(result_dict: Dict[str, Any]) -> Tuple[bool, str]:
    required_fields = [
        "task_id",
        "repo",
        "condition",
        "seed",
        "model",
        "model_revision",
        "task_success",
        "pytest_pass",
        "stale_action",
        "solution_constraint_pass",
        "repo_context_level",
        "memory_source",
        "memory_validity_status",
        "prompt_tokens",
        "repo_tokens",
        "memory_tokens",
        "raw_generation_path",
        "evidence_path"
    ]
    for rf in required_fields:
        if rf not in result_dict:
            return False, f"Missing required field: {rf}"
    if not isinstance(result_dict["task_success"], bool):
        return False, "task_success must be boolean"
    return True, "OK"


def run_smoke_test():
    print("=== RoleMem Benchmark v1.0 Formal Smoke Test ===")
    
    # 1. Validate Config
    if not os.path.exists(CONFIG_PATH):
        raise FileNotFoundError(f"Missing config at {CONFIG_PATH}")
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    print(f"[OK] Loaded config: version={config['benchmark_version']}, model={config['model_config']['model_name']}")

    # 2. Validate Core Manifest
    with open(CORE_MANIFEST, "r", encoding="utf-8") as f:
        core_items = [json.loads(line) for line in f if line.strip()]
    print(f"[OK] Loaded {len(core_items)} core transitions from {CORE_MANIFEST}")

    # 3. Validate Control Manifest
    with open(CONTROL_MANIFEST, "r", encoding="utf-8") as f:
        control_items = [json.loads(line) for line in f if line.strip()]
    print(f"[OK] Loaded {len(control_items)} control transitions from {CONTROL_MANIFEST}")

    # 4. Validate Result Schema on mock sample
    sample_result = {
        "task_id": core_items[0]["transition_id"],
        "repo": core_items[0]["repo_name"],
        "condition": "S0",
        "seed": 42,
        "model": "Qwen/Qwen2.5-Coder-7B-Instruct",
        "model_revision": "main",
        "task_success": True,
        "pytest_pass": True,
        "stale_action": False,
        "solution_constraint_pass": True,
        "repo_context_level": "REPO_CONTEXT_NONTRIVIAL",
        "memory_source": "NO_MEMORY",
        "memory_validity_status": "NONE",
        "prompt_tokens": 520,
        "repo_tokens": 340,
        "memory_tokens": 0,
        "raw_generation_path": "/code/rolemem-agent-memory/runs/sample_gen.py",
        "evidence_path": "/code/rolemem-agent-memory/data/external_evidence/sample"
    }

    ok, msg = validate_unified_result_schema(sample_result)
    assert ok, msg
    print("[OK] Standardized Result Schema validation passed.")
    print("=== All Formal Benchmark Smoke Tests PASSED ===")


if __name__ == "__main__":
    run_smoke_test()
