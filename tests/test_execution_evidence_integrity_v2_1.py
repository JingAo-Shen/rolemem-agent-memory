"""
tests/test_execution_evidence_integrity_v2_1.py

Protocol V2.1-R2 Execution Evidence Integrity Test Suite:
1. test_cat_b_execution_worktree_evidence(): Verifies real git worktree execution across distinct base and target commits.
2. test_cat_c_execution_worktree_evidence(): Verifies real counterfactual execution across base and target commits with digest equality.
3. test_no_hardcoded_execution_flags(): Verifies builder uses live execute_contract_at_commit.
4. test_evidence_integrity_artifacts_complete(): Verifies grounding, task mapping, and evidence integrity artifacts for all 30 transitions.
"""

import os
import glob
import json
import pytest

DATA_DIR = "/code/rolemem-agent-memory/data/memory_validity_v2_1"
CONTRACTS_DIR = os.path.join(DATA_DIR, "contracts")
COUNTERFACTUALS_DIR = os.path.join(DATA_DIR, "counterfactuals")
GROUNDING_DIR = "/code/rolemem-agent-memory/data/memory_grounding_v2_1"
TASK_MAPPING_DIR = "/code/rolemem-agent-memory/data/task_mapping_v2_1"
EVIDENCE_INTEGRITY_DIR = "/code/rolemem-agent-memory/data/evidence_integrity_v2_1"
BUILDER_SCRIPT = "/code/rolemem-agent-memory/scripts/build_grounded_memory_validity_benchmark_v2_1.py"


def test_cat_b_execution_worktree_evidence():
    contract_files = sorted(glob.glob(f"{CONTRACTS_DIR}/*.json"))
    assert len(contract_files) >= 8, f"Expected at least 8 Cat B contract files, found {len(contract_files)}"

    for cf in contract_files:
        with open(cf, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert "case_id" in data
        assert "repository" in data
        assert "base_commit" in data and len(data["base_commit"]) == 40
        assert "target_commit" in data and len(data["target_commit"]) == 40
        assert data["base_commit"] != data["target_commit"]

        base_exec = data.get("base_execution", {})
        target_exec = data.get("target_execution", {})

        assert base_exec.get("passed") is True, f"Base execution failed in {cf}"
        assert target_exec.get("passed") is True, f"Target execution failed in {cf}"
        assert base_exec.get("cwd_commit") == data["base_commit"], f"Base cwd_commit mismatch in {cf}"
        assert target_exec.get("cwd_commit") == data["target_commit"], f"Target cwd_commit mismatch in {cf}"
        assert base_exec.get("exit_code") == 0
        assert target_exec.get("exit_code") == 0
        assert "stdout_sha256" in base_exec and len(base_exec["stdout_sha256"]) == 64
        assert "stderr_sha256" in target_exec and len(target_exec["stderr_sha256"]) == 64
        assert data.get("machine_verified") is True


def test_cat_c_execution_worktree_evidence():
    counterfactual_files = sorted(glob.glob(f"{COUNTERFACTUALS_DIR}/*.json"))
    assert len(counterfactual_files) >= 1, f"Expected at least 1 Cat C counterfactual file, found {len(counterfactual_files)}"

    for cff in counterfactual_files:
        with open(cff, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert "case_id" in data
        assert "repository" in data
        assert "base_commit" in data and len(data["base_commit"]) == 40
        assert "target_commit" in data and len(data["target_commit"]) == 40
        assert data["base_commit"] != data["target_commit"]
        assert data.get("symbol_digest_equal") is True
        assert data.get("linkage_verified") is True

        old_b = data.get("old_on_base", {})
        old_t = data.get("old_on_target", {})
        new_t = data.get("new_on_target", {})

        assert old_b.get("passed") is True, f"old_on_base failed in {cff}"
        assert old_t.get("passed") is False, f"old_on_target should fail in {cff}"
        assert new_t.get("passed") is True, f"new_on_target failed in {cff}"

        assert old_b.get("cwd_commit") == data["base_commit"]
        assert old_t.get("cwd_commit") == data["target_commit"]
        assert new_t.get("cwd_commit") == data["target_commit"]
        assert data.get("machine_verified") is True


def test_cat_d2_execution_worktree_evidence():
    bb_dir = os.path.join(DATA_DIR, "behavior_breaks")
    assert os.path.exists(bb_dir)
    bb_files = sorted(glob.glob(f"{bb_dir}/*.json"))
    assert len(bb_files) >= 2, f"Expected at least 2 Cat D2 behavior break files, found {len(bb_files)}"

    for bbf in bb_files:
        with open(bbf, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert "case_id" in data
        assert "repository" in data
        assert data["base_commit"] != data["target_commit"]
        assert data.get("break_verified") is True

        b_exec = data.get("base_execution", {})
        t_exec = data.get("target_execution", {})

        assert b_exec.get("passed") is True, f"base_execution failed in {bbf}"
        assert t_exec.get("passed") is False, f"target_execution should fail in {bbf}"


def test_no_hardcoded_execution_flags():
    assert os.path.exists(BUILDER_SCRIPT), "Builder script must exist"
    with open(BUILDER_SCRIPT, "r", encoding="utf-8") as f:
        src = f.read()

    assert "def execute_contract_at_commit(" in src, "Builder must define execute_contract_at_commit"
    assert "git worktree add" in src or "subprocess.run" in src, "Builder must execute contracts in real worktrees"


def test_evidence_integrity_artifacts_complete():
    assert os.path.exists(GROUNDING_DIR)
    assert os.path.exists(TASK_MAPPING_DIR)
    assert os.path.exists(EVIDENCE_INTEGRITY_DIR)

    g_files = glob.glob(f"{GROUNDING_DIR}/*.json")
    tm_files = glob.glob(f"{TASK_MAPPING_DIR}/*.json")
    ei_files = glob.glob(f"{EVIDENCE_INTEGRITY_DIR}/*.json")

    assert len(g_files) == 30, f"Expected 30 grounding files, found {len(g_files)}"
    assert len(tm_files) == 30, f"Expected 30 task mapping files, found {len(tm_files)}"
    assert len(ei_files) == 30, f"Expected 30 evidence integrity files, found {len(ei_files)}"

    for eif in ei_files:
        with open(eif, "r", encoding="utf-8") as f:
            edata = json.load(f)
        assert edata.get("authenticity_verified") is True
        assert edata.get("pr_url_valid") is True
        assert edata.get("evidence_integrity_verified") is True
