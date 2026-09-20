#!/usr/bin/env python3
"""
scripts/export_benchmark_v2.py

Deterministic exporter for Protocol V2 Benchmark manifests:
- data/benchmark_v2/track_a_core.jsonl (15 items)
- data/benchmark_v2/track_a_controls.jsonl (4 items)
- data/benchmark_v2/excluded.jsonl (8 items)
- data/benchmark_v2/rebuild_remaining.jsonl (3 items)
- data/benchmark_v2/manifest_summary.json
"""

import os
import sys
import json
import hashlib
from typing import Dict, Any, List

sys.path.insert(0, "/code/rolemem-agent-memory")

POOL_PATH = "/code/rolemem-agent-memory/data/curation/track_a_pool_v1.jsonl"
SPECS_DIR = "/code/rolemem-agent-memory/data/specs"
BENCHMARK_V2_DIR = "/code/rolemem-agent-memory/data/benchmark_v2"
ARCHIVE_EXCLUDED_DIR = "/code/rolemem-agent-memory/data/archive/excluded"

os.makedirs(BENCHMARK_V2_DIR, exist_ok=True)
os.makedirs(ARCHIVE_EXCLUDED_DIR, exist_ok=True)


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def export_benchmark_v2():
    core_records = []
    control_records = []
    excluded_records = []
    rebuild_records = []

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
            with open(os.path.join(ARCHIVE_EXCLUDED_DIR, f"{tid}.json"), "w", encoding="utf-8") as af:
                json.dump(full_spec or record, af, indent=2)
        elif decision == "REBUILD_CANDIDATE":
            rebuild_records.append(record)

    # Save manifests
    core_path = os.path.join(BENCHMARK_V2_DIR, "track_a_core.jsonl")
    control_path = os.path.join(BENCHMARK_V2_DIR, "track_a_controls.jsonl")
    excluded_path = os.path.join(BENCHMARK_V2_DIR, "excluded.jsonl")
    rebuild_path = os.path.join(BENCHMARK_V2_DIR, "rebuild_remaining.jsonl")
    summary_path = os.path.join(BENCHMARK_V2_DIR, "manifest_summary.json")

    for path, data in [(core_path, core_records), (control_path, control_records), (excluded_path, excluded_records), (rebuild_path, rebuild_records)]:
        with open(path, "w", encoding="utf-8") as f:
            for r in data:
                f.write(json.dumps(r) + "\n")

    summary = {
        "protocol_version": "2.0",
        "total_evaluated_transitions": len(pool),
        "core_benchmark_count": len(core_records),
        "control_benchmark_count": len(control_records),
        "rebuild_candidate_count": len(rebuild_records),
        "excluded_count": len(excluded_records),
        "core_transitions": [r["transition_id"] for r in core_records],
        "control_transitions": [r["transition_id"] for r in control_records],
        "rebuild_transitions": [r["transition_id"] for r in rebuild_records],
        "excluded_transitions": [r["transition_id"] for r in excluded_records],
        "distinct_repositories_core": len(set(r["repo_name"] for r in core_records)),
        "distinct_repositories_all": len(set(r["repo_name"] for r in pool)),
        "manifest_sha256": {
            "track_a_core.jsonl": sha256_text(open(core_path, "r", encoding="utf-8").read()),
            "track_a_controls.jsonl": sha256_text(open(control_path, "r", encoding="utf-8").read()),
            "excluded.jsonl": sha256_text(open(excluded_path, "r", encoding="utf-8").read()),
            "rebuild_remaining.jsonl": sha256_text(open(rebuild_path, "r", encoding="utf-8").read())
        }
    }

    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(f"=== Export Benchmark V2 Complete ===")
    print(f"  Core Benchmark: {len(core_records)} -> {core_path}")
    print(f"  Control Benchmark: {len(control_records)} -> {control_path}")
    print(f"  Rebuild Remaining: {len(rebuild_records)} -> {rebuild_path}")
    print(f"  Excluded: {len(excluded_records)} -> {excluded_path}")
    print(f"  Summary: {summary_path}")


if __name__ == "__main__":
    export_benchmark_v2()
