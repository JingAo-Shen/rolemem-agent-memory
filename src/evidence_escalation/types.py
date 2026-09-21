"""
src/evidence_escalation/types.py

Core Type Definitions and Data Models for Protocol V2.2-V1.1 Selective Evidence Escalation:
- EvidenceActionType: Types of evidence acquisition actions.
- BindingStrength: Strength of grounding/binding of discovered artifact to claim (STRONG, WEAK, UNBOUND).
- ExecutionStatus: Status of targeted execution (PASS, FAIL, ERROR, TIMEOUT, UNAVAILABLE).
- SourceOriginStatus: Verification status of execution package origin (VERIFIED_TARGET_WORKTREE, SOURCE_ORIGIN_UNVERIFIED).
- DecisionEvidenceStatus: Audit status of final evidence (VERIFIED_WITNESS, WEAK_WITNESS, UNVERIFIED_SOURCE, INCONCLUSIVE).
- CostBudget: Budget limits for evidence acquisition with standard development presets (B10, B25, B50, B100).
- PipelineConfig: Granular enablement of escalation stages for independent ablation studies.
- AcquiredEvidence: Standardized representation of acquired evidence with full provenance hashes.
- TestCandidate: Discovered test candidate in the native repository with function-level SHA256.
- EvidenceAcquisitionRequest: Standardized request interface for evidence escalation.
- EscalationTrace & EscalationTraceStep: Full execution trace of selective escalation.
"""

from __future__ import annotations
import json
import hashlib
from enum import Enum
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional, Set, Tuple

from src.claim_validity.types import (
    MemoryClaim,
    ClaimEvaluationResult,
    GroundingStatus,
    ValidationStatus,
    EvidenceType,
    ClaimEvidence
)
from src.evaluation.context import EvaluationContext


class EvidenceActionType(str, Enum):
    REPOSITORY_SEARCH = "REPOSITORY_SEARCH"
    DEPENDENCY_INSPECTION = "DEPENDENCY_INSPECTION"
    TEST_DISCOVERY = "TEST_DISCOVERY"
    TEST_INSPECTION = "TEST_INSPECTION"
    TARGETED_EXECUTION = "TARGETED_EXECUTION"
    GIT_HISTORY_INSPECTION = "GIT_HISTORY_INSPECTION"


class BindingStrength(str, Enum):
    STRONG = "STRONG"
    WEAK = "WEAK"
    UNBOUND = "UNBOUND"


class ExecutionStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    ERROR = "ERROR"
    TIMEOUT = "TIMEOUT"
    UNAVAILABLE = "UNAVAILABLE"


class SourceOriginStatus(str, Enum):
    VERIFIED_TARGET_WORKTREE = "VERIFIED_TARGET_WORKTREE"
    SOURCE_ORIGIN_UNVERIFIED = "SOURCE_ORIGIN_UNVERIFIED"


class DecisionEvidenceStatus(str, Enum):
    VERIFIED_WITNESS = "VERIFIED_WITNESS"
    WEAK_WITNESS = "WEAK_WITNESS"
    UNVERIFIED_SOURCE = "UNVERIFIED_SOURCE"
    INCONCLUSIVE = "INCONCLUSIVE"


@dataclass
class CostBudget:
    max_files_scanned: int = 500
    max_tests_inspected: int = 50
    max_executions_run: int = 5
    execution_timeout_sec: int = 15
    max_total_actions: int = 10

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> CostBudget:
        return cls(**data)

    @classmethod
    def get_preset(cls, name: str) -> CostBudget:
        name_u = name.upper()
        if name_u == "B10":
            return cls(max_files_scanned=20, max_tests_inspected=10, max_executions_run=1, max_total_actions=3)
        elif name_u == "B25":
            return cls(max_files_scanned=50, max_tests_inspected=25, max_executions_run=2, max_total_actions=5)
        elif name_u == "B50":
            return cls(max_files_scanned=100, max_tests_inspected=50, max_executions_run=3, max_total_actions=8)
        elif name_u == "B100":
            return cls(max_files_scanned=300, max_tests_inspected=100, max_executions_run=5, max_total_actions=15)
        return cls()

    @classmethod
    def from_preset(cls, name: str) -> CostBudget:
        return cls.get_preset(name)


@dataclass
class PipelineConfig:
    repo_search: bool = True
    dependency_inspection: bool = True
    test_discovery: bool = True
    targeted_execution: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> PipelineConfig:
        return cls(**data)


@dataclass
class AcquiredEvidence:
    evidence_id: str
    claim_id: str
    action_type: EvidenceActionType
    source_type: str
    repository: str
    commit: str
    file_path: str
    content_hash: str  # defined as test_function_sha256 or AST segment hash
    binding_strength: BindingStrength
    supports_or_contradicts: str  # "SUPPORTS", "CONTRADICTS", "INCONCLUSIVE"
    confidence: float
    test_file_sha256: str = ""
    test_function_sha256: str = ""
    stdout_sha256: str = ""
    stderr_sha256: str = ""
    command_sha256: str = ""
    source_origin_status: str = "SOURCE_ORIGIN_UNVERIFIED"
    dependency_environment_status: str = "CURRENT_ENVIRONMENT_NOT_HISTORICALLY_RESTORED"
    cost: Dict[str, Any] = field(default_factory=dict)
    detail: str = ""
    extra_metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "claim_id": self.claim_id,
            "action_type": self.action_type.value if isinstance(self.action_type, Enum) else str(self.action_type),
            "source_type": self.source_type,
            "repository": self.repository,
            "commit": self.commit,
            "file_path": self.file_path,
            "content_hash": self.content_hash,
            "binding_strength": self.binding_strength.value if isinstance(self.binding_strength, Enum) else str(self.binding_strength),
            "supports_or_contradicts": self.supports_or_contradicts,
            "confidence": self.confidence,
            "test_file_sha256": self.test_file_sha256,
            "test_function_sha256": self.test_function_sha256,
            "stdout_sha256": self.stdout_sha256,
            "stderr_sha256": self.stderr_sha256,
            "command_sha256": self.command_sha256,
            "source_origin_status": self.source_origin_status,
            "dependency_environment_status": self.dependency_environment_status,
            "cost": self.cost,
            "detail": self.detail,
            "extra_metadata": self.extra_metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> AcquiredEvidence:
        action = EvidenceActionType(data["action_type"]) if isinstance(data["action_type"], str) else data["action_type"]
        strength = BindingStrength(data["binding_strength"]) if isinstance(data["binding_strength"], str) else data["binding_strength"]
        return cls(
            evidence_id=data["evidence_id"],
            claim_id=data["claim_id"],
            action_type=action,
            source_type=data.get("source_type", ""),
            repository=data.get("repository", ""),
            commit=data.get("commit", ""),
            file_path=data.get("file_path", ""),
            content_hash=data.get("content_hash", ""),
            binding_strength=strength,
            supports_or_contradicts=data.get("supports_or_contradicts", "INCONCLUSIVE"),
            confidence=float(data.get("confidence", 0.0)),
            test_file_sha256=data.get("test_file_sha256", ""),
            test_function_sha256=data.get("test_function_sha256", ""),
            stdout_sha256=data.get("stdout_sha256", ""),
            stderr_sha256=data.get("stderr_sha256", ""),
            command_sha256=data.get("command_sha256", ""),
            source_origin_status=data.get("source_origin_status", "SOURCE_ORIGIN_UNVERIFIED"),
            dependency_environment_status=data.get("dependency_environment_status", "CURRENT_ENVIRONMENT_NOT_HISTORICALLY_RESTORED"),
            cost=data.get("cost", {}),
            detail=data.get("detail", ""),
            extra_metadata=data.get("extra_metadata", {})
        )

    def to_claim_evidence(self) -> ClaimEvidence:
        """Converts acquired evidence into standard ClaimEvidence."""
        return ClaimEvidence(
            evidence_type=EvidenceType.EXECUTION if self.action_type == EvidenceActionType.TARGETED_EXECUTION else EvidenceType.AST,
            source=f"{self.action_type.value}:{self.file_path}",
            claim_id=self.claim_id,
            supports_or_contradicts=self.supports_or_contradicts,
            confidence=self.confidence,
            artifact_hash=self.content_hash,
            detail=f"[{self.binding_strength.value}] {self.detail}"
        )


@dataclass
class TestCandidate:
    __test__ = False
    test_file: str
    test_name: str
    subject_mentions: int
    object_mentions: int
    dependency_mentions: int
    assertion_count: int
    target_commit: str
    source_hash: str
    binding_strength: BindingStrength
    discovery_reason: str
    test_source: str = ""
    test_file_sha256: str = ""
    test_function_sha256: str = ""
    line_start: int = 1
    line_end: int = 1
    witness_binding: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_file": self.test_file,
            "test_name": self.test_name,
            "subject_mentions": self.subject_mentions,
            "object_mentions": self.object_mentions,
            "dependency_mentions": self.dependency_mentions,
            "assertion_count": self.assertion_count,
            "target_commit": self.target_commit,
            "source_hash": self.source_hash,
            "test_file_sha256": self.test_file_sha256,
            "test_function_sha256": self.test_function_sha256,
            "binding_strength": self.binding_strength.value if isinstance(self.binding_strength, Enum) else str(self.binding_strength),
            "discovery_reason": self.discovery_reason,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "witness_binding": self.witness_binding
        }


@dataclass
class EvidenceAcquisitionRequest:
    claim: MemoryClaim
    evaluation_context: Optional[EvaluationContext] = None
    repository_root: str = ""
    static_result: Optional[ClaimEvaluationResult] = None
    available_budget: CostBudget = field(default_factory=CostBudget)
    config: PipelineConfig = field(default_factory=PipelineConfig)
    base_commit: str = ""
    target_commit: str = ""


@dataclass
class EscalationTraceStep:
    step_number: int
    action_type: EvidenceActionType
    target: str
    outcome: str
    evidence_id: Optional[str] = None
    binding_strength: Optional[BindingStrength] = None
    cost_increment: Dict[str, Any] = field(default_factory=dict)
    detail: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_number": self.step_number,
            "action_type": self.action_type.value if isinstance(self.action_type, Enum) else str(self.action_type),
            "target": self.target,
            "outcome": self.outcome,
            "evidence_id": self.evidence_id,
            "binding_strength": self.binding_strength.value if self.binding_strength else None,
            "cost_increment": self.cost_increment,
            "detail": self.detail
        }


@dataclass
class EscalationTrace:
    claim_id: str
    static_decision: str
    steps: List[EscalationTraceStep] = field(default_factory=list)
    final_decision: str = "UNCERTAIN"
    total_actions: int = 0
    total_cost: Dict[str, Any] = field(default_factory=dict)
    stop_reason: str = ""
    acquired_evidences: List[Dict[str, Any]] = field(default_factory=list)
    selected_witness: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "static_decision": self.static_decision,
            "final_decision": self.final_decision,
            "total_actions": self.total_actions,
            "total_cost": self.total_cost,
            "stop_reason": self.stop_reason,
            "selected_witness": self.selected_witness,
            "steps": [s.to_dict() for s in self.steps],
            "acquired_evidences": self.acquired_evidences
        }
