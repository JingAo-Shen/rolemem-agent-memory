"""
src/claim_validity/__init__.py

Protocol V2.2 Fine-Grained Claim-Aware Validity Package.
"""

from .types import (
    ClaimType,
    GroundingStatus,
    ValidationStatus,
    EvidenceType,
    MemoryClaim,
    GroundedClaim,
    ClaimEvidence,
    ClaimImpact,
    ClaimEvaluationResult
)
from .claim_extractor import DeterministicClaimExtractor
from .grounding import ClaimGrounder
from .validators import VALIDATOR_REGISTRY, BaseClaimValidator
from .impact import ASTDependencyImpactTracer
from .evidence import EvidenceAggregator
from .engine import ClaimAwareValidityEngine
from .policy import (
    BaseDecisionPolicy,
    SelectivePolicy,
    ForcedBinaryValidDefaultPolicy,
    ForcedBinaryStaleDefaultPolicy
)

__all__ = [
    "ClaimType",
    "GroundingStatus",
    "ValidationStatus",
    "EvidenceType",
    "MemoryClaim",
    "GroundedClaim",
    "ClaimEvidence",
    "ClaimImpact",
    "ClaimEvaluationResult",
    "DeterministicClaimExtractor",
    "ClaimGrounder",
    "BaseClaimValidator",
    "VALIDATOR_REGISTRY",
    "ASTDependencyImpactTracer",
    "EvidenceAggregator",
    "ClaimAwareValidityEngine",
    "BaseDecisionPolicy",
    "SelectivePolicy",
    "ForcedBinaryValidDefaultPolicy",
    "ForcedBinaryStaleDefaultPolicy",
]
