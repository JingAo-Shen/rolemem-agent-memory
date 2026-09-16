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
    assert len(tasks) >= 2
    for t in tasks:
        assert t.category == "unresolved_conflict"
        assert len(t.historical_memories) >= 2
        # Memories have conflicting requirements
        statuses = [m.status for m in t.historical_memories]
        assert all(s == "ACTIVE" for s in statuses)


def test_track_b_counterfactual_pairs_have_identical_instructions():
    """Verify that paired Track B tasks have identical task instructions, eliminating leakage."""
    tasks = get_track_b_tasks()
    pairs = [
        ("track_b_01a_monetary_cents", "track_b_01b_monetary_micros"),
        ("track_b_02a_timestamp_epoch_ms", "track_b_02b_timestamp_iso_utc"),
        ("track_b_03a_entity_id_uuid", "track_b_03b_entity_id_ulid"),
    ]
    task_map = {t.task_id: t for t in tasks}
    for id_a, id_b in pairs:
        assert id_a in task_map and id_b in task_map
        t_a = task_map[id_a]
        t_b = task_map[id_b]
        assert t_a.current_task_instruction == t_b.current_task_instruction, (
            f"Instruction mismatch between counterfactual pair {id_a} and {id_b}"
        )
        assert t_a.target_file == t_b.target_file
        # Instructions must NOT contain leaking keywords
        leak_keywords = ["cents", "micros", "price_cents", "iso-8601", "epoch", "uuid", "ulid"]
        for kw in leak_keywords:
            assert kw not in t_a.current_task_instruction.lower(), (
                f"Instruction for {id_a} leaks convention keyword: {kw}"
            )


def test_track_c_has_no_explicit_conflict_prompt_hints():
    """Verify Track C tasks do not spoon-feed conflict or CONFLICT_DETECTED hints."""
    tasks = get_track_c_tasks()
    forbidden_hints = ["conflict_detected", "there is a conflict", "return conflict_detected", "flag the conflict"]
    for t in tasks:
        prompt_lower = t.current_task_instruction.lower()
        for hint in forbidden_hints:
            assert hint not in prompt_lower, f"Track C task {t.task_id} contains forbidden prompt hint: {hint}"

