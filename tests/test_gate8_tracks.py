"""
Gate 8 Automated Tests: Benchmark Tracks Verification (Track A, B, C).
"""

import pytest
from src.benchmark_tracks import get_track_a_tasks, get_track_b_tasks, get_track_c_tasks


def test_track_a_integrity():
    tasks = get_track_a_tasks()
    assert len(tasks) == 10
    for t in tasks:
        assert t.category in ("stale_evidence", "explicit_update", "no_update")


def test_track_b_memory_utility_integrity():
    tasks = get_track_b_tasks()
    assert len(tasks) >= 3
    for t in tasks:
        assert t.category == "memory_required"
        assert len(t.historical_memories) > 0
        # The memory must contain actionable project conventions
        for m in t.historical_memories:
            assert m.status == "ACTIVE"
            assert len(m.statement) > 10


def test_track_c_conflict_integrity():
    tasks = get_track_c_tasks()
    assert len(tasks) >= 1
    for t in tasks:
        assert t.category == "unresolved_conflict"
        assert len(t.historical_memories) >= 2
        # Memories have conflicting requirements
        statuses = [m.status for m in t.historical_memories]
        assert all(s == "ACTIVE" for s in statuses)
