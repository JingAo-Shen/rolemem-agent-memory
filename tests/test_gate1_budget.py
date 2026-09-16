"""
Gate 1 Automated Tests: Token Budget Enforcement across Baselines.
"""

import pytest
from src.schema_v1 import MemoryRecordV1
from src.baselines_v1 import BaselineRunnerV1
from src.budgeter import MemoryBudgeter


def make_dummy_memories(count: int = 20) -> list:
    mems = []
    for i in range(count):
        mems.append(MemoryRecordV1(
            memory_id=f"mem_{i:02d}",
            artifact_uri=f"src/module_{i}.py",
            artifact_type="file",
            symbol=f"func_{i}",
            source_commit=f"commit_{i}",
            observed_at=100.0 + i,
            evidence_type="test_run",
            evidence_ref=f"test_{i}.log",
            valid_from=100.0 + i,
            valid_to=float('inf'),
            statement=f"Detailed project memory record number {i} with exhaustive context describing architecture requirements and constraints.",
            artifact_digest="d41d8cd98f00b204e9800998ecf8427e"
        ))
    return mems


@pytest.mark.parametrize("budget", [128, 256, 512, 1024])
def test_all_baselines_comply_with_token_budget(budget: int):
    mems = make_dummy_memories(25)
    ws = {f"src/module_{i}.py": "content" for i in range(25)}
    budgeter = MemoryBudgeter(max_memory_tokens=budget)

    # Test B1
    txt, tokens = BaselineRunnerV1.run_B1_recent_raw_history(
        query="architecture", role="coder", current_time=500.0,
        workspace_files=ws, all_memories=mems, budgeter=budgeter
    )
    assert tokens <= budget, f"B1 exceeded budget: {tokens} > {budget}"

    # Test B2
    txt, tokens = BaselineRunnerV1.run_B2_chronological_history(
        query="architecture", role="coder", current_time=500.0,
        workspace_files=ws, all_memories=mems, budgeter=budgeter
    )
    assert tokens <= budget, f"B2 exceeded budget: {tokens} > {budget}"

    # Test B3
    txt, tokens = BaselineRunnerV1.run_B3_bm25_unscoped(
        query="architecture", role="coder", current_time=500.0,
        workspace_files=ws, all_memories=mems, budgeter=budgeter
    )
    assert tokens <= budget, f"B3 exceeded budget: {tokens} > {budget}"

    # Test B4
    txt, tokens = BaselineRunnerV1.run_B4_bm25_temporal(
        query="architecture", role="coder", current_time=500.0,
        workspace_files=ws, all_memories=mems, budgeter=budgeter
    )
    assert tokens <= budget, f"B4 exceeded budget: {tokens} > {budget}"

    # Test B5
    txt, tokens = BaselineRunnerV1.run_B5_memstrata_temporal_supersession(
        query="architecture", role="coder", current_time=500.0,
        workspace_files=ws, all_memories=mems, budgeter=budgeter
    )
    assert tokens <= budget, f"B5 exceeded budget: {tokens} > {budget}"

    # Test F
    txt, tokens = BaselineRunnerV1.run_F_rolemem_full(
        query="architecture", role="coder", current_time=500.0,
        workspace_files=ws, all_memories=mems, budgeter=budgeter
    )
    assert tokens <= budget, f"F exceeded budget: {tokens} > {budget}"


def test_b0_returns_zero_tokens():
    mems = make_dummy_memories(5)
    txt, tokens = BaselineRunnerV1.run_B0_no_memory(
        query="test", role="coder", current_time=500.0,
        workspace_files={}, all_memories=mems
    )
    assert txt == ""
    assert tokens == 0
