"""
tests/test_symbol_validity_benchmark_v3.py
Unit tests for Independent Memory Validity Benchmark V3.
"""

import os
import json
import pytest

BENCHMARK_PATH = "/code/rolemem-agent-memory/data/memory_validity_cases_v3.jsonl"
EVAL_PATH = "/code/rolemem-agent-memory/data/symbol_validity_evaluation_v3.json"


def test_benchmark_v3_structure():
    assert os.path.exists(BENCHMARK_PATH)
    with open(BENCHMARK_PATH, "r", encoding="utf-8") as f:
        cases = [json.loads(line) for line in f if line.strip()]

    assert len(cases) >= 40
    categories = {c["ground_truth_category"] for c in cases}
    assert "CAT_A" in categories
    assert "CAT_B" in categories
    assert "CAT_C" in categories
    assert "CAT_D" in categories

    repos = {c["repository"] for c in cases}
    assert len(repos) >= 10


def test_benchmark_v3_case_fields():
    with open(BENCHMARK_PATH, "r", encoding="utf-8") as f:
        cases = [json.loads(line) for line in f if line.strip()]

    for c in cases:
        assert "case_id" in c
        assert "repository" in c
        assert "ground_truth_valid" in c
        assert isinstance(c["ground_truth_valid"], bool)
        assert "ground_truth_category" in c
        assert "scientific_rationale" in c
        assert "memory_statement" in c


def test_symbol_validity_evaluation_metrics():
    assert os.path.exists(EVAL_PATH)
    with open(EVAL_PATH, "r", encoding="utf-8") as f:
        eval_data = json.load(f)

    mechs = eval_data["mechanisms"]
    assert "File_Level_Baseline" in mechs
    assert "Pure_Symbol_AST_Baseline" in mechs
    assert "RoleMem_Hybrid_Validity" in mechs

    file_fir = mechs["File_Level_Baseline"]["False_Invalidation_Rate_FIR"]
    assert file_fir == 1.0  # 100% false invalidation on valid cases in modified files

    rolemem_fir = mechs["RoleMem_Hybrid_Validity"]["False_Invalidation_Rate_FIR"]
    assert rolemem_fir == 0.0  # 0% false invalidation
