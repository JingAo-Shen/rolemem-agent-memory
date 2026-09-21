"""
src/claim_validity/validators/base.py

Abstract Base Class for Protocol V2.2 Claim Validators.
Every validator must return:
- ValidationStatus (SUPPORTED, CONTRADICTED, INSUFFICIENT_EVIDENCE)
- List[ClaimEvidence]
- detail / explanation string
"""

import abc
import hashlib
from typing import Tuple, List, Dict, Any, Optional
from ..types import (
    ClaimType,
    ValidationStatus,
    GroundingStatus,
    GroundedClaim,
    ClaimEvidence,
    EvidenceType
)


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


class BaseClaimValidator(abc.ABC):
    """Abstract interface for claim-specific validity evaluators."""

    @property
    @abc.abstractmethod
    def target_claim_type(self) -> ClaimType:
        """The ClaimType this validator handles."""
        pass

    @abc.abstractmethod
    def validate(
        self,
        grounded_claim: GroundedClaim,
        base_source: str,
        target_source: str,
        diff_hunk: str = "",
        execution_artifact: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Tuple[ValidationStatus, List[ClaimEvidence], str]:
        """
        Evaluates the claim against base and target sources and evidence.
        Returns (ValidationStatus, evidences, explanation).
        """
        pass
