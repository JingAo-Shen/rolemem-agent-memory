"""
Gate 9 Automated Tests: Agent-Generated Memory Pipeline and Extraction Metrics.
"""

import pytest
from src.agent_memory_generator import AgentTrajectory, AgentMemoryWriter


def test_agent_memory_extraction_demo1():
    """Demo Task 1: Developer agent implements Redis-backed rate limiter."""
    traj = AgentTrajectory(
        agent_id="dev_agent_01",
        task_id="task_redis_limiter",
        actions=[{"tool": "write_file", "path": "src/limiter.py"}],
        final_diff="+class RedisRateLimiter:\n+    def __init__(self, host='localhost', port=6379): pass",
        test_stdout="================ 3 passed in 0.05s ================\nPASSED",
        source_commit="a1b2c3d4e5f6",
        files_modified={"src/limiter.py": "class RedisRateLimiter:\n    def __init__(self, host='localhost', port=6379):\n        self.host = host\n"}
    )

    extracted = AgentMemoryWriter.extract_memories_from_trajectory(traj, timestamp=150.0)
    assert len(extracted) == 2  # 1 artifact memory, 1 test verification memory
    
    # Check artifact memory
    art_mem = next(m for m in extracted if m.artifact_type == "file")
    assert art_mem.artifact_uri == "src/limiter.py"
    assert art_mem.artifact_digest is not None
    assert art_mem.evidence_type == "commit_diff"
    assert "a1b2c3d" in art_mem.evidence_ref

    # Evaluate metrics against ground truth
    metrics = AgentMemoryWriter.evaluate_extraction_quality(
        extracted,
        ground_truth_statements=["Implementation in src/limiter.py", "functional tests passed"]
    )
    assert metrics.write_precision > 0.0
    assert metrics.write_recall > 0.0
    assert metrics.evidence_attribution_accuracy == 1.0  # 100% of extracted memories have evidence refs!


def test_agent_memory_extraction_demo2():
    """Demo Task 2: DB engineer adds composite indexing."""
    traj = AgentTrajectory(
        agent_id="dba_agent_02",
        task_id="task_db_indexing",
        actions=[{"tool": "edit_schema", "file": "migrations/001_orders.sql"}],
        final_diff="+CREATE INDEX idx_user_orders ON orders (user_id, created_at);",
        test_stdout="PASSED: Query latency reduced by 85%",
        source_commit="f9e8d7c6b5a4",
        files_modified={"src/models/orders.py": "class Order:\n    user_id: int\n"}
    )

    extracted = AgentMemoryWriter.extract_memories_from_trajectory(traj, timestamp=200.0)
    assert len(extracted) == 2
    metrics = AgentMemoryWriter.evaluate_extraction_quality(
        extracted,
        ground_truth_statements=["Implementation in src/models/orders.py"]
    )
    assert metrics.evidence_attribution_accuracy == 1.0
