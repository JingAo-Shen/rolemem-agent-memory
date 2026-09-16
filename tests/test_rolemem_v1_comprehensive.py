"""
Gate 4 Comprehensive Unit Test Suite for RoleMem v1 Core and Associated Modules.
Tests cover Artifact Invalidation, Causal Supersession DAG, Temporal Bounds,
Dependencies, Cycle Detection, and Retrieval Ranking.
"""

import pytest
import hashlib
from src.schema_v1 import MemoryRecordV1
from src.rolemem_core_v1 import RoleMemStoreV1


def _sha256(content: str) -> str:
    return hashlib.sha256(content.encode('utf-8')).hexdigest()


# -----------------------------------------------------------------------------
# 1. Artifact Verification Tests
# -----------------------------------------------------------------------------

def test_artifact_changed_triggers_invalidation():
    store = RoleMemStoreV1()
    old_content = "TIMEOUT = 5000"
    m = MemoryRecordV1(
        memory_id="m1", artifact_uri="src/cfg.py", artifact_type="file",
        symbol="TIMEOUT", source_commit="c1", observed_at=10.0,
        evidence_type="test", evidence_ref="log.txt", valid_from=10.0,
        valid_to=float('inf'), statement="Timeout is 5000ms",
        artifact_digest=_sha256(old_content)
    )
    store.add_record(m)

    # Workspace with changed content
    ws = {"src/cfg.py": "TIMEOUT = 10000"}
    invalidated = store.selective_artifact_invalidation(ws)
    assert "m1" in invalidated
    assert store.records["m1"].status == "INVALIDATED_BY_ARTIFACT"


def test_artifact_unchanged_remains_active():
    store = RoleMemStoreV1()
    content = "TIMEOUT = 5000"
    m = MemoryRecordV1(
        memory_id="m1", artifact_uri="src/cfg.py", artifact_type="file",
        symbol="TIMEOUT", source_commit="c1", observed_at=10.0,
        evidence_type="test", evidence_ref="log.txt", valid_from=10.0,
        valid_to=float('inf'), statement="Timeout is 5000ms",
        artifact_digest=_sha256(content)
    )
    store.add_record(m)

    # Workspace with identical content
    ws = {"src/cfg.py": content}
    invalidated = store.selective_artifact_invalidation(ws)
    assert len(invalidated) == 0
    assert store.records["m1"].status == "ACTIVE"


def test_artifact_unrelated_remains_active():
    store = RoleMemStoreV1()
    content_a = "CLASS_A = True"
    content_b = "CLASS_B = True"
    mA = MemoryRecordV1(
        memory_id="mA", artifact_uri="src/a.py", artifact_type="file",
        symbol="CLASS_A", source_commit="c1", observed_at=10.0,
        evidence_type="test", evidence_ref="logA.txt", valid_from=10.0,
        valid_to=float('inf'), statement="Class A enabled",
        artifact_digest=_sha256(content_a)
    )
    store.add_record(mA)

    # Only b.py changes; a.py remains unchanged
    ws = {"src/a.py": content_a, "src/b.py": "MODIFIED"}
    invalidated = store.selective_artifact_invalidation(ws)
    assert "mA" not in invalidated
    assert store.records["mA"].status == "ACTIVE"


def test_artifact_deleted_triggers_invalidation():
    store = RoleMemStoreV1()
    content = "OLD_MODULE = True"
    m = MemoryRecordV1(
        memory_id="m1", artifact_uri="src/legacy.py", artifact_type="file",
        symbol="OLD_MODULE", source_commit="c1", observed_at=10.0,
        evidence_type="test", evidence_ref="log.txt", valid_from=10.0,
        valid_to=float('inf'), statement="Legacy module active",
        artifact_digest=_sha256(content)
    )
    store.add_record(m)

    # File src/legacy.py was deleted from workspace
    ws = {"src/other.py": "x = 1"}
    invalidated = store.selective_artifact_invalidation(ws)
    assert "m1" in invalidated
    assert store.records["m1"].status == "INVALIDATED_BY_ARTIFACT"


def test_artifact_renamed_triggers_invalidation_of_old_uri():
    store = RoleMemStoreV1()
    content = "CODE = 1"
    m = MemoryRecordV1(
        memory_id="m1", artifact_uri="src/old_name.py", artifact_type="file",
        symbol="CODE", source_commit="c1", observed_at=10.0,
        evidence_type="test", evidence_ref="log.txt", valid_from=10.0,
        valid_to=float('inf'), statement="Code is 1",
        artifact_digest=_sha256(content)
    )
    store.add_record(m)

    # Renamed to new_name.py in workspace
    ws = {"src/new_name.py": content}
    invalidated = store.selective_artifact_invalidation(ws)
    assert "m1" in invalidated
    assert store.records["m1"].status == "INVALIDATED_BY_ARTIFACT"


# -----------------------------------------------------------------------------
# 2. Causal Supersession DAG Tests
# -----------------------------------------------------------------------------

def test_supersession_two_hop_chain():
    store = RoleMemStoreV1()
    m1 = MemoryRecordV1(
        memory_id="m1", artifact_uri="cfg.py", artifact_type="config",
        symbol="TTL", source_commit="c1", observed_at=10.0,
        evidence_type="spec", evidence_ref="spec1.md", valid_from=10.0,
        valid_to=float('inf'), statement="TTL is 60"
    )
    m2 = MemoryRecordV1(
        memory_id="m2", artifact_uri="cfg.py", artifact_type="config",
        symbol="TTL", source_commit="c2", observed_at=20.0,
        evidence_type="spec", evidence_ref="spec2.md", valid_from=20.0,
        valid_to=float('inf'), supersedes="m1", statement="TTL is 120"
    )
    store.add_record(m1)
    store.add_record(m2)

    assert store.records["m1"].status == "SUPERSEDED"
    assert store.records["m1"].valid_to == 20.0
    assert store.records["m2"].status == "ACTIVE"


def test_supersession_multi_hop_chain():
    store = RoleMemStoreV1()
    m1 = MemoryRecordV1(memory_id="m1", artifact_uri="a", artifact_type="f", symbol="s", source_commit="c1", observed_at=1.0, evidence_type="s", evidence_ref="r", valid_from=1.0, valid_to=float('inf'), statement="v1")
    m2 = MemoryRecordV1(memory_id="m2", artifact_uri="a", artifact_type="f", symbol="s", source_commit="c2", observed_at=2.0, evidence_type="s", evidence_ref="r", valid_from=2.0, valid_to=float('inf'), supersedes="m1", statement="v2")
    m3 = MemoryRecordV1(memory_id="m3", artifact_uri="a", artifact_type="f", symbol="s", source_commit="c3", observed_at=3.0, evidence_type="s", evidence_ref="r", valid_from=3.0, valid_to=float('inf'), supersedes="m2", statement="v3")

    store.add_record(m1)
    store.add_record(m2)
    store.add_record(m3)

    assert store.records["m1"].status == "SUPERSEDED"
    assert store.records["m2"].status == "SUPERSEDED"
    assert store.records["m3"].status == "ACTIVE"


def test_supersession_dependent_memory_propagation():
    store = RoleMemStoreV1()
    m_parent = MemoryRecordV1(memory_id="p", artifact_uri="a", artifact_type="f", symbol="p", source_commit="c1", observed_at=10.0, evidence_type="s", evidence_ref="r", valid_from=10.0, valid_to=float('inf'), statement="parent base")
    m_child = MemoryRecordV1(memory_id="c", artifact_uri="b", artifact_type="f", symbol="c", source_commit="c1", observed_at=15.0, evidence_type="s", evidence_ref="r", valid_from=15.0, valid_to=float('inf'), depends_on=["p"], statement="child derived from parent")
    m_new_parent = MemoryRecordV1(memory_id="p_new", artifact_uri="a", artifact_type="f", symbol="p", source_commit="c2", observed_at=25.0, evidence_type="s", evidence_ref="r", valid_from=25.0, valid_to=float('inf'), supersedes="p", statement="parent updated")

    store.add_record(m_parent)
    store.add_record(m_child)
    assert store.records["c"].status == "ACTIVE"

    store.add_record(m_new_parent)
    assert store.records["p"].status == "SUPERSEDED"
    # Child depending on old parent must be transitively invalidated
    assert store.records["c"].status == "SUPERSEDED"
    assert store.records["c"].valid_to == 25.0


def test_dependency_multiple_parents_one_invalidated():
    store = RoleMemStoreV1()
    m_p1 = MemoryRecordV1(memory_id="p1", artifact_uri="a", artifact_type="f", symbol="p1", source_commit="c1", observed_at=10.0, evidence_type="s", evidence_ref="r", valid_from=10.0, valid_to=float('inf'), statement="parent 1")
    m_p2 = MemoryRecordV1(memory_id="p2", artifact_uri="b", artifact_type="f", symbol="p2", source_commit="c1", observed_at=10.0, evidence_type="s", evidence_ref="r", valid_from=10.0, valid_to=float('inf'), statement="parent 2")
    m_child = MemoryRecordV1(memory_id="child", artifact_uri="c", artifact_type="f", symbol="ch", source_commit="c1", observed_at=12.0, evidence_type="s", evidence_ref="r", valid_from=12.0, valid_to=float('inf'), depends_on=["p1", "p2"], statement="child depending on both")

    store.add_record(m_p1)
    store.add_record(m_p2)
    store.add_record(m_child)

    # Invalidate p1
    m_p1_new = MemoryRecordV1(memory_id="p1_new", artifact_uri="a", artifact_type="f", symbol="p1", source_commit="c2", observed_at=20.0, evidence_type="s", evidence_ref="r", valid_from=20.0, valid_to=float('inf'), supersedes="p1", statement="p1 update")
    store.add_record(m_p1_new)

    assert store.records["p1"].status == "SUPERSEDED"
    assert store.records["p2"].status == "ACTIVE"
    assert store.records["child"].status == "SUPERSEDED"


# -----------------------------------------------------------------------------
# 3. Temporal Validity Bounds Tests
# -----------------------------------------------------------------------------

def test_time_future_memory_cannot_be_retrieved():
    store = RoleMemStoreV1()
    m_future = MemoryRecordV1(
        memory_id="mf", artifact_uri="a", artifact_type="f", symbol="s",
        source_commit="c", observed_at=100.0, evidence_type="s", evidence_ref="r",
        valid_from=500.0, valid_to=float('inf'), statement="Future deployment rule"
    )
    store.add_record(m_future)
    res = store.retrieve("deployment", "coder", current_time=200.0, workspace_files={})
    assert len(res) == 0


def test_time_expired_memory_cannot_be_retrieved():
    store = RoleMemStoreV1()
    m_expired = MemoryRecordV1(
        memory_id="me", artifact_uri="a", artifact_type="f", symbol="s",
        source_commit="c", observed_at=10.0, evidence_type="s", evidence_ref="r",
        valid_from=10.0, valid_to=50.0, statement="Temporary hotfix rule"
    )
    store.add_record(m_expired)
    res = store.retrieve("hotfix", "coder", current_time=60.0, workspace_files={})
    assert len(res) == 0


def test_time_active_memory_can_be_retrieved():
    store = RoleMemStoreV1()
    m_active = MemoryRecordV1(
        memory_id="ma", artifact_uri="a", artifact_type="f", symbol="s",
        source_commit="c", observed_at=10.0, evidence_type="s", evidence_ref="r",
        valid_from=10.0, valid_to=100.0, statement="Active policy rule"
    )
    store.add_record(m_active)
    res = store.retrieve("policy", "coder", current_time=50.0, workspace_files={})
    assert len(res) == 1
    assert res[0].memory_id == "ma"


# -----------------------------------------------------------------------------
# 4. Cycle Detection & Retrieval Ranking Tests
# -----------------------------------------------------------------------------

def test_cycle_in_supersession_dag_does_not_hang():
    """Verify that circular dependency graph terminates cleanly without RecursionError."""
    store = RoleMemStoreV1()
    m1 = MemoryRecordV1(memory_id="c1", artifact_uri="a", artifact_type="f", symbol="s", source_commit="c", observed_at=10.0, evidence_type="s", evidence_ref="r", valid_from=10.0, valid_to=float('inf'), depends_on=["c2"], statement="c1")
    m2 = MemoryRecordV1(memory_id="c2", artifact_uri="a", artifact_type="f", symbol="s", source_commit="c", observed_at=10.0, evidence_type="s", evidence_ref="r", valid_from=10.0, valid_to=float('inf'), depends_on=["c1"], statement="c2")
    store.add_record(m1)
    store.add_record(m2)

    # Invalidate c1 - cycle must be caught by visited set
    m1_new = MemoryRecordV1(memory_id="c1_new", artifact_uri="a", artifact_type="f", symbol="s", source_commit="c2", observed_at=20.0, evidence_type="s", evidence_ref="r", valid_from=20.0, valid_to=float('inf'), supersedes="c1", statement="c1 new")
    store.add_record(m1_new)

    assert store.records["c1"].status == "SUPERSEDED"
    assert store.records["c2"].status == "SUPERSEDED"


def test_retrieval_bm25_semantic_ranking_sanity():
    store = RoleMemStoreV1()
    m_irrelevant = MemoryRecordV1(memory_id="m_irr", artifact_uri="a", artifact_type="f", symbol="s", source_commit="c", observed_at=10.0, evidence_type="s", evidence_ref="r", valid_from=10.0, valid_to=float('inf'), statement="The weather in Paris is sunny.")
    m_relevant = MemoryRecordV1(memory_id="m_rel", artifact_uri="b", artifact_type="f", symbol="s", source_commit="c", observed_at=10.0, evidence_type="s", evidence_ref="r", valid_from=10.0, valid_to=float('inf'), statement="Database connection timeout pool configuration setting.")
    store.add_record(m_irrelevant)
    store.add_record(m_relevant)

    results = store.retrieve("database timeout", "coder", current_time=50.0, workspace_files={})
    assert len(results) > 0
    assert results[0].memory_id == "m_rel"


def test_retrieval_role_projection_bonus_sanity():
    store = RoleMemStoreV1()
    m_coder = MemoryRecordV1(memory_id="m_code", artifact_uri="a", artifact_type="f", symbol="s", source_commit="c", observed_at=10.0, evidence_type="s", evidence_ref="r", valid_from=10.0, valid_to=float('inf'), role_tags=["coder"], statement="API endpoint implementation guide.")
    m_reviewer = MemoryRecordV1(memory_id="m_rev", artifact_uri="b", artifact_type="f", symbol="s", source_commit="c", observed_at=10.0, evidence_type="s", evidence_ref="r", valid_from=10.0, valid_to=float('inf'), role_tags=["reviewer"], statement="API endpoint review criteria checklist.")
    store.add_record(m_coder)
    store.add_record(m_reviewer)

    # When queried by coder
    res_coder = store.retrieve("API endpoint", "coder", current_time=50.0, workspace_files={}, use_role_bonus=True, role_bonus_weight=5.0)
    assert res_coder[0].memory_id == "m_code"

    # When queried by reviewer
    res_rev = store.retrieve("API endpoint", "reviewer", current_time=50.0, workspace_files={}, use_role_bonus=True, role_bonus_weight=5.0)
    assert res_rev[0].memory_id == "m_rev"
