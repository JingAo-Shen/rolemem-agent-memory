"""
Anti-leakage and boundary condition tests.
Verifies that future events cannot be retrieved, cross-task events are isolated, and hash changes trigger invalidation.
"""
import pytest
from src.memory import RoleMemoryStore

def test_future_evidence_denial():
    store = RoleMemoryStore()
    store.write_record({
        "id": "future_mem",
        "task_scope": "task_leak",
        "statement": "Secret update revealed at step 10",
        "valid_from": 10,
        "valid_to": 20
    }, as_of=10)

    # Attempt retrieval at step 5
    res = store.retrieve(query="Secret update", role="coder", as_of=5, task_scope="task_leak", method="full")
    assert len(res) == 0, "Future evidence valid_from=10 must NOT be retrieved at step 5!"
    store.close()

def test_artifact_hash_invalidation():
    store = RoleMemoryStore()
    store.write_record({
        "id": "hash_mem",
        "task_scope": "task_hash",
        "statement": "Facts bound to old commit hash",
        "valid_from": 1,
        "artifact_hash": "commit_v1"
    }, as_of=1)

    # When current artifact hash is commit_v2, old memory must be excluded
    res = store.retrieve(query="Facts", role="coder", as_of=2, task_scope="task_hash", current_artifact_hash="commit_v2", method="full")
    assert len(res) == 0, "Memory bound to old hash must be invalidated when artifact hash changes!"
    store.close()

def test_cross_task_scope_isolation():
    store = RoleMemoryStore()
    store.write_record({
        "id": "task_a_mem",
        "task_scope": "task_A",
        "statement": "Private memory belonging to task A",
        "valid_from": 1
    }, as_of=1)

    # Querying from task B should not leak task A's memory
    res = store.retrieve(query="Private memory", role="coder", as_of=2, task_scope="task_B", method="full")
    assert len(res) == 0, "Cross-task memory leak must be strictly prevented!"
    store.close()
