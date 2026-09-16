"""
Agent-Generated Memory Pipeline and Dual-Track Architecture.
Implements automated memory extraction from Phase 1 agent trajectories/diffs,
evidence attribution verification, and Phase 2 handoff evaluation.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
import hashlib
import json
from src.schema_v1 import MemoryRecordV1
from src.rolemem_core_v1 import RoleMemStoreV1


@dataclass
class AgentTrajectory:
    """Represents a Phase 1 agent execution trace with tool outputs and commit diffs."""
    agent_id: str
    task_id: str
    actions: List[Dict[str, Any]]
    final_diff: str
    test_stdout: str
    source_commit: str
    files_modified: Dict[str, str]


@dataclass
class MemoryExtractionMetrics:
    write_precision: float
    write_recall: float
    evidence_attribution_accuracy: float
    total_extracted: int
    ground_truth_count: int


class AgentMemoryWriter:
    """Extracts structured RoleMem records from raw agent trajectories and execution logs."""

    @staticmethod
    def extract_memories_from_trajectory(
        trajectory: AgentTrajectory,
        timestamp: float = 100.0
    ) -> List[MemoryRecordV1]:
        extracted: List[MemoryRecordV1] = []

        # 1. Extract from commit diff (artifact-bound records)
        for path, content in trajectory.files_modified.items():
            digest = hashlib.sha256(content.encode('utf-8')).hexdigest()
            # Heuristic extraction of decisions/interfaces
            if "class " in content or "def " in content:
                extracted.append(MemoryRecordV1(
                    memory_id=f"agent_mem_{trajectory.agent_id}_{len(extracted)+1:02d}",
                    artifact_uri=path,
                    artifact_type="file",
                    symbol=path.split("/")[-1].replace(".py", ""),
                    source_commit=trajectory.source_commit,
                    observed_at=timestamp,
                    evidence_type="commit_diff",
                    evidence_ref=f"commit_{trajectory.source_commit[:7]}.diff",
                    valid_from=timestamp,
                    valid_to=float('inf'),
                    status="ACTIVE",
                    role_tags=["coder", "reviewer"],
                    statement=f"Implementation in {path} committed at {trajectory.source_commit[:7]}.",
                    artifact_digest=digest
                ))

        # 2. Extract from test verification output
        if "PASSED" in trajectory.test_stdout:
            extracted.append(MemoryRecordV1(
                memory_id=f"agent_mem_{trajectory.agent_id}_test_pass",
                artifact_uri=list(trajectory.files_modified.keys())[0] if trajectory.files_modified else "",
                artifact_type="test",
                symbol="test_suite",
                source_commit=trajectory.source_commit,
                observed_at=timestamp,
                evidence_type="test_run",
                evidence_ref="pytest_verification.log",
                valid_from=timestamp,
                valid_to=float('inf'),
                status="ACTIVE",
                role_tags=["tester", "reviewer"],
                statement="All functional unit tests passed successfully on current interface.",
                artifact_digest=None
            ))

        return extracted

    @staticmethod
    def evaluate_extraction_quality(
        extracted_memories: List[MemoryRecordV1],
        ground_truth_statements: List[str]
    ) -> MemoryExtractionMetrics:
        """Calculate Precision, Recall, and Evidence Attribution Accuracy."""
        if not extracted_memories and not ground_truth_statements:
            return MemoryExtractionMetrics(1.0, 1.0, 1.0, 0, 0)
        if not extracted_memories:
            return MemoryExtractionMetrics(0.0, 0.0, 0.0, 0, len(ground_truth_statements))

        true_positives = 0
        valid_evidence_count = 0

        for mem in extracted_memories:
            # Check evidence attribution
            if mem.evidence_type in ("commit_diff", "test_run", "execution_output") and mem.evidence_ref:
                valid_evidence_count += 1

            # Check semantic match with ground truth statements
            for gt in ground_truth_statements:
                # Key token overlap
                gt_words = set(gt.lower().split())
                mem_words = set(mem.statement.lower().split())
                if len(gt_words & mem_words) >= 2:
                    true_positives += 1
                    break

        precision = true_positives / len(extracted_memories) if extracted_memories else 0.0
        recall = min(1.0, true_positives / len(ground_truth_statements)) if ground_truth_statements else 1.0
        attribution_acc = valid_evidence_count / len(extracted_memories) if extracted_memories else 0.0

        return MemoryExtractionMetrics(
            write_precision=precision,
            write_recall=recall,
            evidence_attribution_accuracy=attribution_acc,
            total_extracted=len(extracted_memories),
            ground_truth_count=len(ground_truth_statements)
        )
