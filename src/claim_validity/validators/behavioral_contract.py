"""
src/claim_validity/validators/behavioral_contract.py

Validates ClaimType.BEHAVIORAL_CONTRACT:
- Uses ClaimEvidenceBinder to verify execution artifact integrity and binding.
- SUPPORTED if contract execution passes on target commit with verified binding.
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
from ..binding import ClaimEvidenceBinder


class BehavioralContractValidator(BaseClaimValidator):
    def __init__(self):
        self.binder = ClaimEvidenceBinder()

    @property
    def target_claim_type(self) -> ClaimType:
        return ClaimType.BEHAVIORAL_CONTRACT

    def validate(
        self,
        grounded_claim: GroundedClaim,
        base_source: str,
        target_source: str,
        diff_hunk: str = "",
        execution_artifact: Optional[Dict[str, Any]] = None,
        base_commit: str = "",
        target_commit: str = "",
        repository: str = "",
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

        # Verify execution artifact binding
        binding = self.binder.verify(
            claim=claim,
            execution_artifact=execution_artifact,
            base_commit=base_commit,
            target_commit=target_commit,
            repository=repository
        )

        if binding.binding_status == "VERIFIED" and execution_artifact:
            target_exec = execution_artifact.get("target_execution") or execution_artifact.get("old_on_target") or {}

            if "passed" in target_exec:
                if target_exec["passed"] is True:
                    ev = ClaimEvidence(
                        evidence_type=EvidenceType.EXECUTION,
                        source="contract_execution",
                        claim_id=cid,
                        supports_or_contradicts="SUPPORTS",
                        confidence=0.98,
                        artifact_hash=binding.evidence_artifact_sha256,
                        detail=f"Behavioral contract verified passed on target commit (contract_hash={binding.contract_hash[:8] if binding.contract_hash else 'N/A'})."
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
                        artifact_hash=binding.evidence_artifact_sha256,
                        detail=f"Behavioral contract failed on target commit (exit_code={target_exec.get('exit_code')})."
                    )
                    evidences.append(ev)
                    return ValidationStatus.CONTRADICTED, evidences, "Behavioral contract execution failed on target commit."

        return ValidationStatus.INSUFFICIENT_EVIDENCE, evidences, f"Behavioral contract binding status: {binding.binding_status} ({'; '.join(binding.binding_reasons)})."
