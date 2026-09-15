"""
Unit tests for RoleMemoryStore: verifying validity bounds, supersedes handling, role projection bonus.
"""
import pytest
from src.memory import RoleMemoryStore

def test_memory_supersedes_invalidation():
    store = RoleMemoryStore()
    m1 = store.write_record({
        "id": "mem_01",
        "task_scope": "task_1",
        "statement": "Old legacy config TTL 60",
        "valid_from": 1,
        "valid_to": 10,
        "role_tags": ["coder"]
    }, as_of=1)

    m2 = store.write_record({
        "id": "mem_02",
        "task_scope": "task_1",
        "statement": "Updated dynamic LRU config",
        "valid_from": 5,
        "valid_to": 99999,
        "supersedes": "mem_01",
        "role_tags": ["coder"]
    }, as_of=5)

    # Retrieval at as_of=6 should only return mem_02
    results = store.retrieve(query="config", role="coder", as_of=6, task_scope="task_1", method="full")
    ids = [r["id"] for r in results]
    assert "mem_02" in ids
    assert "mem_01" not in ids, "Old superseded memory must not be returned!"
    store.close()

def test_role_projection_bonus():
    store = RoleMemoryStore()
    store.write_record({
        "id": "mem_coder",
        "task_scope": "task_2",
        "statement": "Implementation detail failure constraint",
        "valid_from": 1,
        "role_tags": ["coder"]
    }, as_of=1)

    store.write_record({
        "id": "mem_reviewer",
        "task_scope": "task_2",
        "statement": "Verification acceptance requirement",
        "valid_from": 1,
        "role_tags": ["reviewer"]
    }, as_of=1)

    # Coder retrieval should rank mem_coder first
    coder_res = store.retrieve(query="detail requirement", role="coder", as_of=2, task_scope="task_2", method="full")
    assert coder_res[0]["id"] == "mem_coder"

    # Reviewer retrieval should rank mem_reviewer first
    rev_res = store.retrieve(query="detail requirement", role="reviewer", as_of=2, task_scope="task_2", method="full")
    assert rev_res[0]["id"] == "mem_reviewer"
    store.close()
