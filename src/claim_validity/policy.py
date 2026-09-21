"""
src/claim_validity/policy.py

Decision Policy Layer for Protocol V2.2:
- Decouples intrinsic Claim-Aware validity evaluation from downstream retrieval decision policies.
- Policies:
  - SelectivePolicy: Preserves UNCERTAIN for selective abstention analysis.
  - ForcedBinaryValidDefaultPolicy: Coerces UNCERTAIN -> VALID (optimistic retrieval default).
  - ForcedBinaryStaleDefaultPolicy: Coerces UNCERTAIN -> STALE (cautious cache eviction default).
"""

import abc
from typing import List, Dict, Any, Tuple
from .types import ClaimEvaluationResult


class BaseDecisionPolicy(abc.ABC):
    """Abstract retrieval decision policy."""

    @property
    @abc.abstractmethod
    def policy_name(self) -> str:
        pass

    @abc.abstractmethod
    def decide(self, result: ClaimEvaluationResult) -> str:
        """Translates engine evaluation result to final retrieval decision."""
        pass

    def decide_batch(self, results: List[ClaimEvaluationResult]) -> List[str]:
        return [self.decide(r) for r in results]


class SelectivePolicy(BaseDecisionPolicy):
    """Preserves UNCERTAIN for selective prediction with abstention."""

    @property
    def policy_name(self) -> str:
        return "SelectivePolicy"

    def decide(self, result: ClaimEvaluationResult) -> str:
        return result.decision


class ForcedBinaryValidDefaultPolicy(BaseDecisionPolicy):
    """Coerces UNCERTAIN -> VALID (optimistic retrieval: retain memory unless proven stale)."""

    @property
    def policy_name(self) -> str:
        return "ForcedBinaryValidDefaultPolicy"

    def decide(self, result: ClaimEvaluationResult) -> str:
        if result.decision == "UNCERTAIN":
            return "VALID"
        return result.decision


class ForcedBinaryStaleDefaultPolicy(BaseDecisionPolicy):
    """Coerces UNCERTAIN -> STALE (cautious invalidation: evict memory if uncertainty exists)."""

    @property
    def policy_name(self) -> str:
        return "ForcedBinaryStaleDefaultPolicy"

    def decide(self, result: ClaimEvaluationResult) -> str:
        if result.decision == "UNCERTAIN":
            return "STALE"
        return result.decision
