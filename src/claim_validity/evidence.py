"""
src/claim_validity/evidence.py

Evidence Aggregator and Integrity Engine for Protocol V2.2:
- Collects, hashes, and aggregates ClaimEvidence items across AST, Git diff, Dependency, and Execution sources.
- Prevents unsupported VALID or STALE decisions (zero groundless assertions).
- Computes aggregated contradiction score and support score.
"""

import hashlib
from typing import List, Dict, Any, Tuple, Optional
from .types import (
    EvidenceType,
    ClaimEvidence,
    ValidationStatus,
    GroundingStatus,
    GroundedClaim
)


class EvidenceAggregator:
    """Aggregates and verifies evidence items supporting or contradicting a MemoryClaim."""

    def __init__(self, contradiction_threshold: float = 0.85, support_threshold: float = 0.80):
        self.contradiction_threshold = contradiction_threshold
        self.support_threshold = support_threshold

    def create_evidence(
        self,
        evidence_type: EvidenceType,
        source: str,
        claim_id: str,
        supports_or_contradicts: str,
        confidence: float,
        content: str,
        detail: str = ""
    ) -> ClaimEvidence:
        artifact_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        return ClaimEvidence(
            evidence_type=evidence_type,
            source=source,
            claim_id=claim_id,
            supports_or_contradicts=supports_or_contradicts,
            confidence=confidence,
            artifact_hash=artifact_hash,
            detail=detail
        )

    def aggregate(
        self,
        evidences: List[ClaimEvidence],
        grounding_status: GroundingStatus
    ) -> Tuple[str, float, List[str]]:
        """
        Aggregates evidence list into a final decision: "VALID", "STALE", or "UNCERTAIN".
        Returns (decision, confidence, reasons).
        """
        if grounding_status in (GroundingStatus.UNRESOLVED, GroundingStatus.AMBIGUOUS):
            # Check if there is explicit contradiction evidence (e.g. symbol deletion in AST/diff)
            contra_evs = [e for e in evidences if e.supports_or_contradicts == "CONTRADICTS" and e.confidence >= self.contradiction_threshold]
            if contra_evs:
                top_contra = max(contra_evs, key=lambda e: e.confidence)
                reasons = [f"Contradicted by {top_contra.source}: {top_contra.detail}"]
                return "STALE", top_contra.confidence, reasons
            
            reasons = [f"Grounding is {grounding_status.value}; cannot make deterministic claim decision."]
            return "UNCERTAIN", 0.50, reasons

        if not evidences:
            return "UNCERTAIN", 0.50, ["Zero empirical evidence items recorded for claim."]

        contra_evs = [e for e in evidences if e.supports_or_contradicts == "CONTRADICTS"]
        support_evs = [e for e in evidences if e.supports_or_contradicts == "SUPPORTS"]

        # 1. Any high-confidence contradiction -> STALE
        if contra_evs:
            max_contra = max(contra_evs, key=lambda e: e.confidence)
            if max_contra.confidence >= self.contradiction_threshold:
                reasons = [f"Contradicted by {e.source}: {e.detail}" for e in contra_evs]
                return "STALE", max_contra.confidence, reasons

        # 2. Strong support with zero contradictions -> VALID
        if support_evs and not contra_evs:
            max_support = max(support_evs, key=lambda e: e.confidence)
            if max_support.confidence >= self.support_threshold:
                reasons = [f"Supported by {e.source}: {e.detail}" for e in support_evs]
                return "VALID", max_support.confidence, reasons

        # 3. Conflicting evidence or insufficient confidence -> UNCERTAIN
        reasons = ["Evidence is insufficient or conflicting between support and contradiction."]
        return "UNCERTAIN", 0.50, reasons
