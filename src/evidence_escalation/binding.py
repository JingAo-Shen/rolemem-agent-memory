"""
src/evidence_escalation/binding.py

Evidence Aggregation and Decision Synthesis for Protocol V2.2-V1 Evidence Escalation:
- Aggregates static AST evaluation result with newly acquired dynamic and repository evidences.
- Strictly enforces confidence and binding strength thresholds:
  - STRONG supporting evidence -> VALID
  - STRONG contradicting evidence -> STALE
  - WEAK or INCONCLUSIVE evidence -> UNCERTAIN (fail-uncertain preservation)
"""

from __future__ import annotations
from typing import Dict, Any, List, Optional, Tuple

from src.claim_validity.types import (
    ClaimEvaluationResult,
    ValidationStatus,
    ClaimEvidence
)
from .types import AcquiredEvidence, BindingStrength


class EscalatedEvidenceAggregator:
    """Combines static evaluation results with acquired escalation evidences."""

    def __init__(self, strong_confidence_threshold: float = 0.85):
        self.strong_confidence_threshold = strong_confidence_threshold

    def aggregate(
        self,
        static_result: ClaimEvaluationResult,
        acquired_evidences: List[AcquiredEvidence]
    ) -> ClaimEvaluationResult:
        """
        Synthesizes a final ClaimEvaluationResult by combining static result with acquired evidences.
        """
        if not acquired_evidences:
            return static_result

        all_claim_evidences = list(static_result.evidences)
        reasons = list(static_result.reasons)

        # Separate strong supporting and strong contradicting evidences
        strong_supports: List[AcquiredEvidence] = []
        strong_contradicts: List[AcquiredEvidence] = []
        weak_evidences: List[AcquiredEvidence] = []

        for acq in acquired_evidences:
            all_claim_evidences.append(acq.to_claim_evidence())

            if acq.binding_strength == BindingStrength.STRONG and acq.confidence >= self.strong_confidence_threshold:
                if acq.supports_or_contradicts == "SUPPORTS":
                    strong_supports.append(acq)
                elif acq.supports_or_contradicts == "CONTRADICTS":
                    strong_contradicts.append(acq)
            else:
                weak_evidences.append(acq)

        # Decision logic
        if strong_contradicts and not strong_supports:
            decision = "STALE"
            v_status = ValidationStatus.CONTRADICTED
            max_conf = max(e.confidence for e in strong_contradicts)
            reasons.append(f"Resolved to STALE via {len(strong_contradicts)} strong contradicting evidence(s): {strong_contradicts[0].detail}")
        elif strong_supports and not strong_contradicts:
            decision = "VALID"
            v_status = ValidationStatus.SUPPORTED
            max_conf = max(e.confidence for e in strong_supports)
            reasons.append(f"Resolved to VALID via {len(strong_supports)} strong supporting evidence(s): {strong_supports[0].detail}")
        elif strong_supports and strong_contradicts:
            # Conflicting strong evidence -> stay uncertain
            decision = "UNCERTAIN"
            v_status = ValidationStatus.INSUFFICIENT_EVIDENCE
            max_conf = 0.50
            reasons.append("Conflicting strong evidence detected during escalation; maintaining UNCERTAIN.")
        else:
            # Only weak or inconclusive evidence -> maintain static decision
            decision = "UNCERTAIN"
            v_status = static_result.validation_status
            max_conf = static_result.confidence
            if weak_evidences:
                reasons.append(f"Acquired {len(weak_evidences)} weak/inconclusive evidence(s), insufficient for deterministic decision.")

        return ClaimEvaluationResult(
            claim_id=static_result.claim_id,
            decision=decision,
            grounding_status=static_result.grounding_status,
            validation_status=v_status,
            confidence=max_conf,
            evidences=all_claim_evidences,
            reasons=reasons,
            impact=static_result.impact
        )
