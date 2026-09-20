#!/usr/bin/env python3
"""
scripts/evaluate_symbol_validity_v2.py
Evaluates RoleMem symbol validity mechanism and file-level baseline against False Invalidation Benchmark V2.
Uses real RoleMemStoreV1 and MemoryRecordV1 retrieval and invalidation.

Outputs:
- data/symbol_validity_evaluation_v2.json
- reports/symbol-validity-v2.md
"""

import os
import sys
import json
import subprocess
from typing import Dict, Any, List
from collections import Counter

sys.path.insert(0, "/code/rolemem-agent-memory")
from src.schema_v1 import MemoryRecordV1
from src.rolemem_core_v1 import RoleMemStoreV1
from src.symbol_validity import ValidityMetricsCalculator

BENCHMARK_PATH = "/code/rolemem-agent-memory/data/false_invalidation_cases_v2.jsonl"
OUT_JSON = "/code/rolemem-agent-memory/data/symbol_validity_evaluation_v2.json"
OUT_REPORT = "/code/rolemem-agent-memory/reports/symbol-validity-v2.md"

REPO_DIRS = {
    "click": "/code/repo_cache/click",
    "flask": "/code/repo_cache/flask",
    "werkzeug": "/code/repo_cache/werkzeug",
    "markupsafe": "/code/repo_cache/markupsafe",
    "pluggy": "/code/repo_cache/pluggy",
    "attrs": "/code/repo_cache/attrs",
    "virtualenv": "/code/repo_cache/virtualenv",
    "httpx": "/code/repo_cache/httpx",
    "requests": "/code/repo_cache/requests",
    "urllib3": "/code/repo_cache/urllib3",
    "starlette": "/code/repo_cache/starlette",
    "fastapi": "/code/repo_cache/fastapi",
    "more-itertools": "/code/repo_cache/more-itertools",
    "rich": "/code/repo_cache/rich",
    "celery": "/code/repo_cache/celery",
    "iniconfig": "/code/repo_cache/iniconfig",
    "packaging": "/code/repo_cache/packaging",
    "dateutil": "/code/repo_cache/dateutil",
    "tqdm": "/code/repo_cache/tqdm",
    "cachelib": "/code/repo_cache/cachelib",
    "uvicorn": "/code/repo_cache/uvicorn",
}


def evaluate_symbol_validity_v2():
    with open(BENCHMARK_PATH, "r", encoding="utf-8") as f:
        cases = [json.loads(line) for line in f if line.strip()]

    ground_truth_valid = []
    file_predicted_active = []
    symbol_predicted_active = []

    repo_stats = Counter()
    type_stats = Counter()
    stale_kind_stats = Counter()

    detailed_results = []

    for c in cases:
        gt_valid = c["ground_truth_valid"]
        ground_truth_valid.append(gt_valid)

        repo = c["repository"]
        repo_stats[repo] += 1
        type_stats[c["symbol_type"]] += 1
        if not gt_valid:
            stale_kind_stats[c.get("stale_kind", "UNKNOWN")] += 1

        repo_dir = REPO_DIRS.get(repo)
        f_p = c["file_path"]
        t_commit = c["target_commit"]

        # Get real target content from git
        t_cmd = subprocess.run(["git", "show", f"{t_commit}:{f_p}"], cwd=repo_dir, capture_output=True, text=True)
        target_content = t_cmd.stdout if t_cmd.returncode == 0 else ""
        target_ws = {f_p: target_content}

        # 1. Test F-file baseline in RoleMemStoreV1
        store_file = RoleMemStoreV1()
        rec_file = MemoryRecordV1(
            memory_id=c["case_id"],
            artifact_uri=f_p,
            artifact_type="file",
            symbol=c["symbol_name"],
            symbol_qualified_name=c["symbol_qualified_name"],
            symbol_digest=c["base_symbol_digest"],
            validity_granularity="file",
            source_commit=c["base_commit"],
            observed_at=10.0,
            evidence_type="diff_analysis",
            evidence_ref="repo_commit",
            valid_from=10.0,
            statement=f"Memory regarding {c["symbol_qualified_name"]}",
            artifact_digest=c["base_file_sha256"]
        )
        store_file.add_record(rec_file)
        retrieved_file = store_file.retrieve(
            query=c["symbol_qualified_name"],
            role="coder",
            current_time=50.0,
            workspace_files=target_ws,
            validity_mode="file"
        )
        is_file_active = len(retrieved_file) > 0
        file_predicted_active.append(is_file_active)

        # 2. Test F-symbol mechanism in RoleMemStoreV1
        store_sym = RoleMemStoreV1()
        rec_sym = MemoryRecordV1(
            memory_id=c["case_id"],
            artifact_uri=f_p,
            artifact_type="symbol",
            symbol=c["symbol_name"],
            symbol_qualified_name=c["symbol_qualified_name"],
            symbol_digest=c["base_symbol_digest"],
            validity_granularity="symbol",
            source_commit=c["base_commit"],
            observed_at=10.0,
            evidence_type="diff_analysis",
            evidence_ref="repo_commit",
            valid_from=10.0,
            statement=f"Memory regarding {c["symbol_qualified_name"]}",
            artifact_digest=c["base_file_sha256"]
        )
        store_sym.add_record(rec_sym)
        retrieved_sym = store_sym.retrieve(
            query=c["symbol_qualified_name"],
            role="coder",
            current_time=50.0,
            workspace_files=target_ws,
            validity_mode="symbol"
        )
        is_sym_active = len(retrieved_sym) > 0
        symbol_predicted_active.append(is_sym_active)

        detailed_results.append({
            "case_id": c["case_id"],
            "repository": repo,
            "symbol": c["symbol_qualified_name"],
            "symbol_type": c["symbol_type"],
            "ground_truth_valid": gt_valid,
            "file_mode_active": is_file_active,
            "symbol_mode_active": is_sym_active
        })

    metrics_file = ValidityMetricsCalculator.compute(ground_truth_valid, file_predicted_active)
    metrics_sym = ValidityMetricsCalculator.compute(ground_truth_valid, symbol_predicted_active)

    summary_data = {
        "benchmark_cases_count": len(cases),
        "total_repositories": len(repo_stats),
        "repository_distribution": dict(repo_stats),
        "symbol_type_distribution": dict(type_stats),
        "stale_kind_distribution": dict(stale_kind_stats),
        "file_level_baseline": metrics_file,
        "symbol_level_mechanism": metrics_sym,
        "detailed_results": detailed_results
    }

    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=2)

    print("=== Symbol-Level Validity Evaluation V2 ===")
    print(f"Total Cases: {len(cases)} across {len(repo_stats)} repositories")
    print(f"File-Level Baseline (F-file):")
    print(f"  False Invalidation Rate (FIR): {metrics_file["false_invalidation_rate"]*100:.1f}%")
    print(f"  Valid Memory Recall (VMR):     {metrics_file["valid_memory_recall"]*100:.1f}%")
    print(f"  Stale Exposure Rate (SER):     {metrics_file["stale_exposure_rate"]*100:.1f}%")
    print(f"  Stale Memory Recall:           {metrics_file["stale_memory_recall"]*100:.1f}%")
    print(f"Symbol-Level Mechanism (F-symbol):")
    print(f"  False Invalidation Rate (FIR): {metrics_sym["false_invalidation_rate"]*100:.1f}%")
    print(f"  Valid Memory Recall (VMR):     {metrics_sym["valid_memory_recall"]*100:.1f}%")
    print(f"  Stale Exposure Rate (SER):     {metrics_sym["stale_exposure_rate"]*100:.1f}%")
    print(f"  Stale Memory Recall:           {metrics_sym["stale_memory_recall"]*100:.1f}%")


if __name__ == "__main__":
    evaluate_symbol_validity_v2()
