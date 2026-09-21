#!/usr/bin/env python3
"""
scripts/create_v2_2_repository_splits.py

Generates the strict repository-level holdout split for Protocol V2.2:
- data/splits/v2_2_repository_universe.json
- data/splits/v2_2_repo_split.json

Rules:
1. 22 repositories used in Protocol V2.1 are assigned strictly to DEVELOPMENT.
2. Unseen repositories (e.g. cryptography, pydantic, pytest, sqlalchemy, etc.) are assigned to SEALED_TEST.
3. Records fixed random seed, universe SHA256 hash, and split SHA256 hash.
"""

import os
import sys
import json
import hashlib
import random

REPO_CACHE_ROOT = "/code/repo_cache"
SPLITS_DIR = "/code/rolemem-agent-memory/data/splits"
V2_1_STATS_PATH = "/code/rolemem-agent-memory/data/memory_validity_v2_1/benchmark_stats.json"

os.makedirs(SPLITS_DIR, exist_ok=True)

RANDOM_SEED = 42


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def generate_splits():
    # 1. Discover all repositories in repo_cache
    all_repos = sorted([
        d for d in os.listdir(REPO_CACHE_ROOT)
        if os.path.isdir(os.path.join(REPO_CACHE_ROOT, d)) and not d.startswith(".")
    ])

    # 2. Read V2.1 development repositories
    with open(V2_1_STATS_PATH, "r", encoding="utf-8") as f:
        v2_1_stats = json.load(f)
    v2_1_dev_repos = sorted(list(v2_1_stats["cases_per_repository"].keys()))

    # Ensure all V2.1 dev repos are present in all_repos
    for r in v2_1_dev_repos:
        if r not in all_repos:
            all_repos.append(r)
    all_repos = sorted(list(set(all_repos)))

    # 3. Create Universe JSON
    universe_data = {
        "protocol_version": "2.2-claim-aware-v0",
        "random_seed": RANDOM_SEED,
        "total_repositories": len(all_repos),
        "repositories": all_repos
    }
    universe_json_str = json.dumps(universe_data, indent=2, sort_keys=True)
    universe_hash = sha256_text(universe_json_str)
    universe_data["universe_sha256"] = universe_hash

    universe_path = os.path.join(SPLITS_DIR, "v2_2_repository_universe.json")
    with open(universe_path, "w", encoding="utf-8") as f:
        f.write(json.dumps(universe_data, indent=2))

    # 4. Partition into DEVELOPMENT vs SEALED_TEST
    # 22 V2.1 repositories are strictly DEVELOPMENT
    dev_set = set(v2_1_dev_repos)
    sealed_test_repos = sorted([r for r in all_repos if r not in dev_set])

    split_data = {
        "protocol_version": "2.2-claim-aware-v0",
        "random_seed": RANDOM_SEED,
        "universe_sha256": universe_hash,
        "partitions": {
            "DEVELOPMENT": {
                "count": len(v2_1_dev_repos),
                "description": "Historical 22 development repositories used in Protocol V2.1.",
                "repositories": v2_1_dev_repos
            },
            "SEALED_TEST": {
                "count": len(sealed_test_repos),
                "description": "Strictly unseen holdout repositories. Inspection of target transitions/labels forbidden until formal algorithm freeze.",
                "repositories": sealed_test_repos
            }
        }
    }

    split_json_str = json.dumps(split_data, indent=2, sort_keys=True)
    split_hash = sha256_text(split_json_str)
    split_data["split_sha256"] = split_hash

    split_path = os.path.join(SPLITS_DIR, "v2_2_repo_split.json")
    with open(split_path, "w", encoding="utf-8") as f:
        f.write(json.dumps(split_data, indent=2))

    print(f"=== Protocol V2.2 Repository Splits Generated ===")
    print(f"  Total Universe Repositories: {len(all_repos)} -> {universe_path} (SHA: {universe_hash[:12]}...)")
    print(f"  DEVELOPMENT Repositories ({len(v2_1_dev_repos)}): {', '.join(v2_1_dev_repos)}")
    print(f"  SEALED_TEST Repositories ({len(sealed_test_repos)}): {', '.join(sealed_test_repos)}")
    print(f"  Split File: {split_path} (SHA: {split_hash[:12]}...)")


if __name__ == "__main__":
    generate_splits()
