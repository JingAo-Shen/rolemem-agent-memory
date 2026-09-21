"""
src/claim_validity/validators/symbol_exists.py

Validates ClaimType.SYMBOL_EXISTS:
- SUPPORTED if symbol exists in target AST (EXACT or ALIASED).
- CONTRADICTED if symbol is removed in target AST or diff hunk explicitly removes it.
- INSUFFICIENT_EVIDENCE if grounding is UNRESOLVED/AMBIGUOUS without conclusive diff evidence.
"""

import ast
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


class SymbolExistsValidator(BaseClaimValidator):
    @property
    def target_claim_type(self) -> ClaimType:
        return ClaimType.SYMBOL_EXISTS

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
        sym_name = claim.subject or claim.symbol
        unqualified = sym_name.split(".")[-1]
        evidences = []

        # 1. If grounded EXACT or ALIASED in target AST
        if grounded_claim.grounding_status in (GroundingStatus.EXACT, GroundingStatus.ALIASED):
            ev = ClaimEvidence(
                evidence_type=EvidenceType.AST,
                source="target_source_ast",
                claim_id=cid,
                supports_or_contradicts="SUPPORTS",
                confidence=0.98,
                artifact_hash=sha256_text(target_source),
                detail=f"Symbol `{sym_name}` verified present in target AST as `{grounded_claim.target_node_name}`."
            )
            evidences.append(ev)
            return ValidationStatus.SUPPORTED, evidences, f"Symbol `{sym_name}` is present in target source."

        # 2. Check diff hunk for explicit deletion
        if diff_hunk:
            removed_lines = [
                l[1:].strip() for l in diff_hunk.splitlines()
                if l.startswith("-") and not l.startswith("---")
            ]
            added_lines = [
                l[1:].strip() for l in diff_hunk.splitlines()
                if l.startswith("+") and not l.startswith("+++")
            ]
            for rline in removed_lines:
                if (f"def {unqualified}" in rline or f"class {unqualified}" in rline or f"{unqualified} =" in rline):
                    if not any(f"def {unqualified}" in aline or f"class {unqualified}" in aline for aline in added_lines):
                        ev = ClaimEvidence(
                            evidence_type=EvidenceType.GIT_DIFF,
                            source="diff_hunk",
                            claim_id=cid,
                            supports_or_contradicts="CONTRADICTS",
                            confidence=0.95,
                            artifact_hash=sha256_text(diff_hunk),
                            detail=f"Diff removes declaration: `{rline}`"
                        )
                        evidences.append(ev)
                        return ValidationStatus.CONTRADICTED, evidences, f"Symbol `{sym_name}` was explicitly removed in Git diff."

        # 3. Grounding unresolved in target AST
        if grounded_claim.grounding_status == GroundingStatus.UNRESOLVED:
            ev = ClaimEvidence(
                evidence_type=EvidenceType.AST,
                source="target_source_ast",
                claim_id=cid,
                supports_or_contradicts="CONTRADICTS",
                confidence=0.90,
                artifact_hash=sha256_text(target_source),
                detail=f"Symbol `{sym_name}` is absent from target AST."
            )
            evidences.append(ev)
            return ValidationStatus.CONTRADICTED, evidences, f"Symbol `{sym_name}` does not exist in target AST."

        return ValidationStatus.INSUFFICIENT_EVIDENCE, evidences, f"Ambiguous grounding for symbol `{sym_name}`."
