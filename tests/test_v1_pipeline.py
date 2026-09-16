"""
Unit tests for RoleMem v1 pipeline, selective invalidation, and smoke tasks integrity.
"""

import pytest
import hashlib
from src.schema_v1 import MemoryRecordV1, TaskEnvironmentV1
from src.rolemem_core_v1 import RoleMemStoreV1
from src.baselines_v1 import BaselineRunnerV1
from src.smoke_tasks_v1 import get_smoke_tasks_v1


def test_smoke_tasks_integrity():
    tasks = get_smoke_tasks_v1()
    assert len(tasks) == 10
    task_ids = set()
    for t in tasks:
        assert t.task_id not in task_ids, f"Duplicate task_id {t.task_id}"
        task_ids.add(t.task_id)
        assert len(t.target_file) > 0
        assert len(t.hidden_test_code) > 0
        assert len(t.current_task_instruction) > 0


def test_selective_artifact_invalidation():
    store = RoleMemStoreV1()
    file_content_v1 = "SECRET = 'alpha_123'"
    hash_v1 = hashlib.sha256(file_content_v1.encode('utf-8')).hexdigest()

    rec1 = MemoryRecordV1(
        memory_id="m1",
        artifact_uri="auth.py",
        artifact_type="file",
        symbol="SECRET",
        source_commit="c1",
        observed_at=10.0,
        evidence_type="diff",
        evidence_ref="c1.diff",
        valid_from=10.0,
        valid_to=float('inf'),
        statement="Auth secret is alpha_123",
        artifact_digest=hash_v1
    )

    rec2 = MemoryRecordV1(
        memory_id="m2",
        artifact_uri="other.py",
        artifact_type="file",
        symbol="MAX_RETRIES",
        source_commit="c1",
        observed_at=10.0,
        evidence_type="spec",
        evidence_ref="spec.md",
        valid_from=10.0,
        valid_to=float('inf'),
        statement="Max retries is 5",
        artifact_digest="some_other_hash"
    )

    store.add_record(rec1)
    store.add_record(rec2)

    # In workspace, auth.py was modified (new content), but other.py is unchanged
    ws = {
        "auth.py": "SECRET = os.getenv('SECRET')",
        "other.py": "content"
    }

    invalidated = store.selective_artifact_invalidation(ws)
    assert "m1" in invalidated
    assert store.records["m1"].status == "INVALIDATED_BY_ARTIFACT"


def test_causal_dag_supersession():
    store = RoleMemStoreV1()
    
    rec_old = MemoryRecordV1(
        memory_id="m_old",
        artifact_uri="config.py",
        artifact_type="config",
        symbol="TTL",
        source_commit="c1",
        observed_at=10.0,
        evidence_type="spec",
        evidence_ref="spec1.md",
        valid_from=10.0,
        valid_to=float('inf'),
        statement="Use TTL 60"
    )

    rec_new = MemoryRecordV1(
        memory_id="m_new",
        artifact_uri="config.py",
        artifact_type="config",
        symbol="LRU",
        source_commit="c2",
        observed_at=20.0,
        evidence_type="spec",
        evidence_ref="spec2.md",
        valid_from=20.0,
        valid_to=float('inf'),
        supersedes="m_old",
        statement="Use LRU adaptive"
    )

    store.add_record(rec_old)
    assert store.records["m_old"].status == "ACTIVE"
    
    store.add_record(rec_new)
    assert store.records["m_old"].status == "SUPERSEDED"
    assert store.records["m_old"].valid_to == 20.0
    assert store.records["m_new"].status == "ACTIVE"
