"""
tests/test_evaluation_context.py

Unit tests for EvaluationContext dataclass and factory functions.
"""

import pytest
from src.evaluation.context import EvaluationContext, build_evaluation_context


def test_evaluation_context_properties():
    base_src = "def add(a, b):\n    return a + b\n"
    target_same = "def add(a, b):\n    return a + b\n"
    target_diff = "def add(a, b, c=0):\n    return a + b + c\n"

    ctx_same = build_evaluation_context(
        repository="test_repo",
        base_commit="c1",
        target_commit="c2",
        file_path="math.py",
        base_source=base_src,
        target_source=target_same,
        diff="",
        memory_statement="Symbol add exists",
        symbol="add"
    )
    assert ctx_same.is_file_unchanged is True
    assert ctx_same.base_file_hash == ctx_same.target_file_hash

    ctx_diff = build_evaluation_context(
        repository="test_repo",
        base_commit="c1",
        target_commit="c2",
        file_path="math.py",
        base_source=base_src,
        target_source=target_diff,
        diff="+ c=0",
        memory_statement="Symbol add exists",
        symbol="add"
    )
    assert ctx_diff.is_file_unchanged is False
    assert ctx_diff.base_file_hash != ctx_diff.target_file_hash


def test_evaluation_context_to_dict():
    ctx = build_evaluation_context(
        repository="test_repo",
        base_commit="c1",
        target_commit="c2",
        file_path="math.py",
        base_source="def foo(): pass",
        target_source="def foo(): pass",
        diff="",
        memory_statement="Symbol foo exists",
        symbol="foo",
        case_id="MV21-000001",
        claim_id="CLM-000001"
    )
    d = ctx.to_dict()
    assert d["case_id"] == "MV21-000001"
    assert d["claim_id"] == "CLM-000001"
    assert d["is_file_unchanged"] is True
