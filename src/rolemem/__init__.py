"""
src/rolemem/__init__.py

RoleMem: An Epistemic Role-Based Agent Memory Framework.
Provides structured 6-tuple schema, multi-index store, role-aware hybrid retriever,
dynamic lifecycle engine, and evaluation / agent adapters.
"""

from .schema import (
    RoleMemoryRecord,
    RoleEnum,
    MemoryStatus,
    ClaimPayload,
    EvidencePayload,
    TemporalAnchor
)
from .store import RoleMemStore
from .retriever import RoleAwareRetriever, BM25RetrieverScorer
from .lifecycle import RoleMemLifecycleEngine, LifecycleUpdateResult
from .adapter import RoleMemEvaluationAdapter, RoleMemAgentInterface

__all__ = [
    "RoleMemoryRecord",
    "RoleEnum",
    "MemoryStatus",
    "ClaimPayload",
    "EvidencePayload",
    "TemporalAnchor",
    "RoleMemStore",
    "RoleAwareRetriever",
    "BM25RetrieverScorer",
    "RoleMemLifecycleEngine",
    "LifecycleUpdateResult",
    "RoleMemEvaluationAdapter",
    "RoleMemAgentInterface",
]
