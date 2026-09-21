"""
src/evidence_escalation/__init__.py

Protocol V2.2-V1 Evidence Escalation Package Exports.
"""

from .types import (
    EvidenceActionType,
    BindingStrength,
    ExecutionStatus,
    CostBudget,
    AcquiredEvidence,
    TestCandidate,
    EvidenceAcquisitionRequest,
    EscalationTrace,
    EscalationTraceStep
)
from .cost import CostTracker
from .trace import EscalationTracer
from .repository_search import RepositorySearchEngine
from .test_discovery import NativeTestDiscoveryEngine
from .test_binding import ClaimTestBinder
from .executor import TargetedWorktreeExecutor
from .binding import EscalatedEvidenceAggregator
from .planner import DeterministicEscalationPlanner
from .pipeline import EvidenceEscalationPipeline

__all__ = [
    "EvidenceActionType",
    "BindingStrength",
    "ExecutionStatus",
    "CostBudget",
    "AcquiredEvidence",
    "TestCandidate",
    "EvidenceAcquisitionRequest",
    "EscalationTrace",
    "EscalationTraceStep",
    "CostTracker",
    "EscalationTracer",
    "RepositorySearchEngine",
    "NativeTestDiscoveryEngine",
    "ClaimTestBinder",
    "TargetedWorktreeExecutor",
    "EscalatedEvidenceAggregator",
    "DeterministicEscalationPlanner",
    "EvidenceEscalationPipeline"
]
