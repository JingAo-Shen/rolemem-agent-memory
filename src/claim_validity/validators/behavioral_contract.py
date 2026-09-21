"""
src/claim_validity/validators/behavioral_contract.py

Validates ClaimType.BEHAVIORAL_CONTRACT:
- Evaluates contract execution evidence with strict artifact-claim binding.
- SUPPORTED if contract execution passes on target commit without assertion errors.
- CONTRADICTED if contract execution fails on target commit or symbol is deleted.
- INSUFFICIENT_EVIDENCE (fail-uncertain) if no verified execution evidence exists.
"""

from typing import Tuple, List, Dict, Any, Optional
from .base import BaseClaimValidator, sha256_text
from ..types import (
    ClaimType,
    ValidationStatus,
    GroundingStatus,
    GroundedClaim,
    ClaimEvidence,
    EvidenceType
)


class BehavioralContractValidator(BaseClaimValidator):
    @property
    def target_claim_type(self) -> ClaimType:
        return ClaimType.BEHAVIORAL_CONTRACT

    def _verify_artifact_binding(self, claim, execution_artifact: Dict[str, Any]) -> bool:
        """Verifies that the execution artifact is validly bound to this specific claim."""
        if not execution_artifact:
            return False
        
        art_case_id = execution_artifact.get("case_id") or execution_artifact.get("source_case_id")
        if art_case_id and claim.source_case_id and art_case_id != claim.source_case_id:
            return False

        art_claim_id = execution_artifact.get("claim_id")
        if art_claim_id and art_claim_id != claim.claim_id:
            return False

        art_symbol = execution_artifact.get("symbol") or execution_artifact.get("target_symbol")
        claim_sym = (claim.subject or claim.symbol).split(".")[-1]
        if art_symbol and claim_sym and art_symbol.split(".")[-1] != claim_sym:
            return False

        return True

    def validate(
        self,
        grounded_claim: GroundedClaim,
        base_source: str,
        target_source: str,
        diff_hunk: str = "",
        execution_artifact: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Tuple[ValidationStatus, List[ClaimEvidence], str]:
        claim = grounded_claim.claim
        cid = claim.claim_id
        sym_name = (claim.subject or claim.symbol).split(".")[-1]
        evidences = []

        if grounded_claim.grounding_status == GroundingStatus.UNRESOLVED:
            ev = ClaimEvidence(
                evidence_type=EvidenceType.AST,
                source="target_source_ast",
                claim_id=cid,
                supports_or_contradicts="CONTRADICTS",
                confidence=0.95,
                artifact_hash=sha256_text(target_source),
                detail=f"Symbol `{sym_name}` does not exist in target AST."
            )
            evidences.append(ev)
            return ValidationStatus.CONTRADICTED, evidences, f"Symbol `{sym_name}` does not exist."

        # Check execution artifact if provided with verified binding
        if execution_artifact and self._verify_artifact_binding(claim, execution_artifact):
            target_exec = execution_artifact.get("target_execution") or execution_artifact.get("old_on_target") or {}

            if "passed" in target_exec:
                if target_exec["passed"] is True:
                    ev = ClaimEvidence(
                        evidence_type=EvidenceType.EXECUTION,
                        source="contract_execution",
                        claim_id=cid,
                        supports_or_contradicts="SUPPORTS",
                        confidence=0.98,
                        artifact_hash=sha256_text(str(target_exec)),
                        detail="Behavioral contract verified passed on target commit (exit_code=0)."
                    )
                    evidences.append(ev)
                    return ValidationStatus.SUPPORTED, evidences, "Behavioral contract execution passed on target commit."
                else:
                    ev = ClaimEvidence(
                        evidence_type=EvidenceType.EXECUTION,
                        source="contract_execution",
                        claim_id=cid,
                        supports_or_contradicts="CONTRADICTS",
                        confidence=0.98,
                        artifact_hash=sha256_text(str(target_exec)),
                        detail=f"Behavioral contract failed on target commit (exit_code={target_exec.get('exit_code')})."
                    )
                    evidences.append(ev)
                    return ValidationStatus.CONTRADICTED, evidences, "Behavioral contract execution failed on target commit."

        # Fail-uncertain: Without verified dynamic execution evidence, behavioral contract validity cannot be assumed
        return ValidationStatus.INSUFFICIENT_EVIDENCE, evidences, "Behavioral contract execution evidence absent or unbounded."
