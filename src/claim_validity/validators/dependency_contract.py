"""
src/claim_validity/validators/dependency_contract.py

Validates ClaimType.DEPENDENCY_CONTRACT:
- Checks if cross-symbol dependency linkage remains valid.
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


class DependencyContractValidator(BaseClaimValidator):
    @property
    def target_claim_type(self) -> ClaimType:
        return ClaimType.DEPENDENCY_CONTRACT

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
        dep_name = claim.object
        evidences = []

        if grounded_claim.grounding_status == GroundingStatus.UNRESOLVED:
            ev = ClaimEvidence(
                evidence_type=EvidenceType.AST,
                source="target_source_ast",
                claim_id=cid,
                supports_or_contradicts="CONTRADICTS",
                confidence=0.92,
                artifact_hash=sha256_text(target_source),
                detail=f"Symbol `{sym_name}` does not exist in target AST."
            )
            evidences.append(ev)
            return ValidationStatus.CONTRADICTED, evidences, f"Symbol `{sym_name}` does not exist."

        # Check counterfactual / execution artifact if available
        if execution_artifact:
            target_exec = execution_artifact.get("old_on_target") or execution_artifact.get("target_execution") or {}
            if "passed" in target_exec:
                if target_exec["passed"] is False:
                    ev = ClaimEvidence(
                        evidence_type=EvidenceType.EXECUTION,
                        source="dependency_counterfactual",
                        claim_id=cid,
                        supports_or_contradicts="CONTRADICTS",
                        confidence=0.98,
                        artifact_hash=sha256_text(str(target_exec)),
                        detail=f"Dependency `{dep_name}` broken on target commit (execution failed)."
                    )
                    evidences.append(ev)
                    return ValidationStatus.CONTRADICTED, evidences, f"Dependency contract `{dep_name}` broken."
                elif target_exec["passed"] is True:
                    ev = ClaimEvidence(
                        evidence_type=EvidenceType.EXECUTION,
                        source="dependency_counterfactual",
                        claim_id=cid,
                        supports_or_contradicts="SUPPORTS",
                        confidence=0.98,
                        artifact_hash=sha256_text(str(target_exec)),
                        detail=f"Dependency contract verified valid on target commit."
                    )
                    evidences.append(ev)
                    return ValidationStatus.SUPPORTED, evidences, f"Dependency contract `{dep_name}` intact."

        # Check if diff explicitly removes the dependency
        if diff_hunk and dep_name:
            dep_unqual = dep_name.split(".")[-1]
            removed_lines = [l[1:].strip() for l in diff_hunk.splitlines() if l.startswith("-") and not l.startswith("---")]
            for rline in removed_lines:
                if f"def {dep_unqual}" in rline or f"class {dep_unqual}" in rline or f"import {dep_unqual}" in rline:
                    ev = ClaimEvidence(
                        evidence_type=EvidenceType.GIT_DIFF,
                        source="diff_hunk",
                        claim_id=cid,
                        supports_or_contradicts="CONTRADICTS",
                        confidence=0.90,
                        artifact_hash=sha256_text(diff_hunk),
                        detail=f"Dependency `{dep_name}` removed in diff: `{rline}`."
                    )
                    evidences.append(ev)
                    return ValidationStatus.CONTRADICTED, evidences, f"Dependency `{dep_name}` removed."

        return ValidationStatus.INSUFFICIENT_EVIDENCE, evidences, f"Dependency verification for `{dep_name}` inconclusive."
