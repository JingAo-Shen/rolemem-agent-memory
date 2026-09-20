import pytest
import os
import json

BENCHMARK_PATH = "/code/rolemem-agent-memory/data/false_invalidation_cases_v2.jsonl"


def test_benchmark_v2_counts_and_repositories():
    assert os.path.exists(BENCHMARK_PATH), "Benchmark V2 file missing"
    with open(BENCHMARK_PATH, "r", encoding="utf-8") as f:
        cases = [json.loads(line) for line in f if line.strip()]

    valid_cases = [c for c in cases if c["ground_truth_valid"]]
    stale_cases = [c for c in cases if not c["ground_truth_valid"]]
    repos = set(c["repository"] for c in cases)

    assert len(valid_cases) >= 30, f"Expected >= 30 valid cases, got {len(valid_cases)}"
    assert len(stale_cases) >= 15, f"Expected >= 15 stale cases, got {len(stale_cases)}"
    assert len(repos) >= 10, f"Expected >= 10 repositories, got {len(repos)}"


def test_benchmark_v2_zero_fake_hashes():
    with open(BENCHMARK_PATH, "r", encoding="utf-8") as f:
        cases = [json.loads(line) for line in f if line.strip()]

    for c in cases:
        base_dig = c.get("base_symbol_digest")
        assert base_dig is not None, f"Missing base_symbol_digest in {c[case_id]}"
        assert base_dig != "stale_hash_base", f"Found forbidden fake hash in {c[case_id]}"
        assert len(base_dig) == 64, f"Base digest not 64-char sha256 in {c[case_id]}"

        if c["ground_truth_valid"]:
            target_dig = c.get("target_symbol_digest")
            assert target_dig == base_dig, f"Valid case {c[case_id]} target digest mismatch"
            assert c["base_file_sha256"] != c["target_file_sha256"], f"File must be modified in {c[case_id]}"
