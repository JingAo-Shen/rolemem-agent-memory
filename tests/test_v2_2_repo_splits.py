"""
tests/test_v2_2_repo_splits.py

Unit tests verifying Protocol V2.2 repository universe and holdout split integrity.
"""

import os
import json
import hashlib
import pytest

SPLITS_DIR = "/code/rolemem-agent-memory/data/splits"
UNIVERSE_PATH = os.path.join(SPLITS_DIR, "v2_2_repository_universe.json")
SPLIT_PATH = os.path.join(SPLITS_DIR, "v2_2_repo_split.json")
V2_1_STATS_PATH = "/code/rolemem-agent-memory/data/memory_validity_v2_1/benchmark_stats.json"


def test_universe_file_integrity():
    assert os.path.exists(UNIVERSE_PATH), "Universe file must exist"
    with open(UNIVERSE_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["protocol_version"] == "2.2-claim-aware-v0"
    assert data["total_repositories"] == 29
    assert len(data["repositories"]) == 29
    assert data["random_seed"] == 42
    assert "universe_sha256" in data


def test_split_file_partitions():
    assert os.path.exists(SPLIT_PATH), "Split file must exist"
    with open(SPLIT_PATH, "r", encoding="utf-8") as f:
        split_data = json.load(f)

    with open(V2_1_STATS_PATH, "r", encoding="utf-8") as f:
        v2_1_stats = json.load(f)
    v2_1_dev_repos = set(v2_1_stats["cases_per_repository"].keys())

    dev_partition = set(split_data["partitions"]["DEVELOPMENT"]["repositories"])
    sealed_partition = set(split_data["partitions"]["SEALED_TEST"]["repositories"])

    # 1. Exact 22 V2.1 repos in DEVELOPMENT
    assert dev_partition == v2_1_dev_repos, "DEVELOPMENT partition must exactly equal 22 V2.1 repos"
    assert len(dev_partition) == 22

    # 2. Strict disjointness between DEVELOPMENT and SEALED_TEST
    assert dev_partition.isdisjoint(sealed_partition), "DEVELOPMENT and SEALED_TEST must be strictly disjoint"
    assert len(sealed_partition) == 7

    # 3. Sealed test contains expected unseen repos
    expected_sealed = {"cachelib", "cryptography", "dateutil", "pydantic", "pytest", "sqlalchemy", "uvicorn"}
    assert sealed_partition == expected_sealed
