"""
src/claim_validity/validators/behavioral_contract.py

Validates ClaimType.BEHAVIORAL_CONTRACT:
- Evaluates contract execution evidence (e.g. from Cat B contracts or behavior break artifacts).
- SUPPORTED if contract execution passes on target commit without assertion errors.
- CONTRADICTED if contract execution fails on target commit or symbol is missing.
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

        # Check execution artifact if provided (e.g. contract run results or behavior break run results)
        if execution_artifact:
            # 1. Cat B Contract execution artifact
            target_exec = execution_artifact.get("target_execution") or {}
            base_exec = execution_artifact.get("base_execution") or {}

            if "passed" in target_exec:
                if target_exec["passed"] is True:
                    ev = ClaimEvidence(
                        evidence_type=EvidenceType.EXECUTION,
                        source="contract_execution",
                        claim_id=cid,
                        supports_or_contradicts="SUPPORTS",
                        confidence=0.98,
                        artifact_hash=sha256_text(str(target_exec)),
                        detail=f"Behavioral contract verified passed on target commit (exit_code=0)."
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

        # If AST grounding is EXACT/ALIASED and target source has the symbol
        if grounded_claim.grounding_status in (GroundingStatus.EXACT, GroundingStatus.ALIASED):
            ev = ClaimEvidence(
                evidence_type=EvidenceType.AST,
                source="target_source_ast",
                claim_id=cid,
                supports_or_contradicts="SUPPORTS",
                confidence=0.80,
                artifact_hash=sha256_text(target_source),
                detail=f"Symbol `{sym_name}` definition preserved in target AST."
            )
            evidences.append(ev)
            return ValidationStatus.SUPPORTED, evidences, "Symbol structure preserved in target AST."

        return ValidationStatus.INSUFFICIENT_EVIDENCE, evidences, "Contract verification inconclusive."
