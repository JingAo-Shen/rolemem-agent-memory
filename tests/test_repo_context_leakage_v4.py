import pytest
import os
import json

DATA_DIR = "/code/rolemem-agent-memory/data/repo_context_leakage_v4"


def test_repo_context_leakage_v4_files_present():
    assert os.path.exists(DATA_DIR), "Repo leakage V4 directory missing"
    json_files = os.listdir(DATA_DIR)
    assert len(json_files) == 30, f"Expected 30 audit files, got {len(json_files)}"


def test_repo_context_leakage_v4_no_trivializing_or_near_solution():
    for f_name in os.listdir(DATA_DIR):
        p = os.path.join(DATA_DIR, f_name)
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data["leakage_level"] in ["REPO_CONTEXT_NONTRIVIAL", "REPO_CONTEXT_HINTED"], f"Forbidden leakage in {f_name}: {data["leakage_level"]}"
        assert data["target_func_def_found"] is False, f"Target wrapper defined in context for {f_name}"
        assert data["near_solution_found"] is False, f"Near solution code found in context for {f_name}"
