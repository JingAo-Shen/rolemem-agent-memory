#!/usr/bin/env python3
"""
scripts/export_benchmark_v1.py

Deterministic exporter from data/curation/reviews/ and pool_v1.jsonl to:
- data/benchmark_v1/track_a_core.jsonl
- data/benchmark_v1/track_a_controls.jsonl
- data/benchmark_v1/excluded.jsonl
- data/archive/excluded/<tid>.json
"""

import os
import sys
import json
import shutil
from typing import Dict, Any, List

sys.path.insert(0, "/code/rolemem-agent-memory")

POOL_PATH = "/code/rolemem-agent-memory/data/curation/track_a_pool_v1.jsonl"
SPECS_DIR = "/code/rolemem-agent-memory/data/specs"
BENCHMARK_V1_DIR = "/code/rolemem-agent-memory/data/benchmark_v1"
ARCHIVE_EXCLUDED_DIR = "/code/rolemem-agent-memory/data/archive/excluded"

os.makedirs(BENCHMARK_V1_DIR, exist_ok=True)
os.makedirs(ARCHIVE_EXCLUDED_DIR, exist_ok=True)


def export_benchmark_v1():
    core_records = []
    control_records = []
    excluded_records = []

    with open(POOL_PATH, "r", encoding="utf-8") as f:
        pool = [json.loads(line) for line in f if line.strip()]

    for item in pool:
        tid = item["transition_id"]
        decision = item["curation_decision"]

        spec_file = os.path.join(SPECS_DIR, f"{tid}.json")
        full_spec = {}
        if os.path.exists(spec_file):
            with open(spec_file, "r", encoding="utf-8") as sf:
                full_spec = json.load(sf)

        record = {
            "transition_id": tid,
            "repo_name": item["repo_name"],
            "benchmark_role": "CORE" if decision == "CORE_BENCHMARK" else ("CONTROL" if decision == "CONTROL_BENCHMARK" else decision),
            "transition_type": item["transition_type"],
            "stale_sensitive": item["stale_sensitive"],
            "pr_url": item.get("pr_url"),
            "base_commit": item["base_commit"],
            "target_commit": item["target_commit"],
            "primary_file": full_spec.get("primary_file"),
            "target_symbol": full_spec.get("target_symbol"),
            "current_task": full_spec.get("current_task"),
            "stale_memory_candidate": full_spec.get("stale_memory_candidate"),
            "valid_memory_candidate": full_spec.get("valid_memory_candidate"),
            "curation_decision": decision,
            "evidence_hashes": item["evidence_hashes"]
        }

        if decision == "CORE_BENCHMARK":
            core_records.append(record)
        elif decision == "CONTROL_BENCHMARK":
            control_records.append(record)
        elif decision == "EXCLUDED":
            excluded_records.append(record)
            # Save archive
            with open(os.path.join(ARCHIVE_EXCLUDED_DIR, f"{tid}.json"), "w", encoding="utf-8") as af:
                json.dump(full_spec or record, af, indent=2)
        elif decision == "REBUILD_CANDIDATE":
            # Kept in pool, not in core/control manifest
            pass

    # Save manifests
    core_path = os.path.join(BENCHMARK_V1_DIR, "track_a_core.jsonl")
    control_path = os.path.join(BENCHMARK_V1_DIR, "track_a_controls.jsonl")
    excluded_path = os.path.join(BENCHMARK_V1_DIR, "excluded.jsonl")

    with open(core_path, "w", encoding="utf-8") as f:
        for r in core_records:
            f.write(json.dumps(r) + "\n")

    with open(control_path, "w", encoding="utf-8") as f:
        for r in control_records:
            f.write(json.dumps(r) + "\n")

    with open(excluded_path, "w", encoding="utf-8") as f:
        for r in excluded_records:
            f.write(json.dumps(r) + "\n")

    print(f"=== Export Benchmark V1 Complete ===")
    print(f"  Core Benchmark: {len(core_records)} -> {core_path}")
    print(f"  Control Benchmark: {len(control_records)} -> {control_path}")
    print(f"  Excluded: {len(excluded_records)} -> {excluded_path} (Archived to {ARCHIVE_EXCLUDED_DIR})")


if __name__ == "__main__":
    export_benchmark_v1()
