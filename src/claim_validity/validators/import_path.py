"""
src/claim_validity/validators/import_path.py

Validates ClaimType.IMPORT_PATH_VALID:
- SUPPORTED if symbol is importable from claimed path (or exported in __all__).
- CONTRADICTED if symbol is removed from __all__ or target module import fails.
"""

import ast
import textwrap
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


class ImportPathValidator(BaseClaimValidator):
    @property
    def target_claim_type(self) -> ClaimType:
        return ClaimType.IMPORT_PATH_VALID

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

        if not target_source or not target_source.strip():
            ev = ClaimEvidence(
                evidence_type=EvidenceType.AST,
                source="target_source_ast",
                claim_id=cid,
                supports_or_contradicts="CONTRADICTS",
                confidence=0.92,
                artifact_hash="",
                detail=f"Target source is missing or empty."
            )
            evidences.append(ev)
            return ValidationStatus.CONTRADICTED, evidences, f"Target source missing."

        # Parse AST to check __all__ definition
        all_names = None
        try:
            tree = ast.parse(textwrap.dedent(target_source))
            for node in ast.iter_child_nodes(tree):
                if isinstance(node, (ast.Assign, ast.AnnAssign)):
                    targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                    for tgt in targets:
                        if isinstance(tgt, ast.Name) and tgt.id == "__all__":
                            if isinstance(node.value, (ast.List, ast.Tuple, ast.Set)):
                                all_names = [
                                    elt.value for elt in node.value.elts
                                    if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
                                ]
        except Exception:
            pass

        # If claim is specifically about __all__ export or if __all__ is explicitly defined
        if all_names is not None:
            if sym_name not in all_names:
                ev = ClaimEvidence(
                    evidence_type=EvidenceType.AST,
                    source="target_source_ast",
                    claim_id=cid,
                    supports_or_contradicts="CONTRADICTS",
                    confidence=0.95,
                    artifact_hash=sha256_text(target_source),
                    detail=f"Symbol `{sym_name}` is absent from `__all__` in target module."
                )
                evidences.append(ev)
                return ValidationStatus.CONTRADICTED, evidences, f"Symbol `{sym_name}` removed from `__all__` export."
            else:
                ev = ClaimEvidence(
                    evidence_type=EvidenceType.AST,
                    source="target_source_ast",
                    claim_id=cid,
                    supports_or_contradicts="SUPPORTS",
                    confidence=0.95,
                    artifact_hash=sha256_text(target_source),
                    detail=f"Symbol `{sym_name}` is exported in `__all__` in target module."
                )
                evidences.append(ev)
                return ValidationStatus.SUPPORTED, evidences, f"Symbol `{sym_name}` is exported in `__all__`."

        # If __all__ is not defined, check whether symbol exists/is imported in target AST
        if grounded_claim.grounding_status in (GroundingStatus.EXACT, GroundingStatus.ALIASED):
            ev = ClaimEvidence(
                evidence_type=EvidenceType.AST,
                source="target_source_ast",
                claim_id=cid,
                supports_or_contradicts="SUPPORTS",
                confidence=0.92,
                artifact_hash=sha256_text(target_source),
                detail=f"Symbol `{sym_name}` validly defined/imported in target module."
            )
            evidences.append(ev)
            return ValidationStatus.SUPPORTED, evidences, f"Import path for `{sym_name}` is valid."

        if grounded_claim.grounding_status == GroundingStatus.UNRESOLVED:
            ev = ClaimEvidence(
                evidence_type=EvidenceType.AST,
                source="target_source_ast",
                claim_id=cid,
                supports_or_contradicts="CONTRADICTS",
                confidence=0.92,
                artifact_hash=sha256_text(target_source),
                detail=f"Symbol `{sym_name}` cannot be resolved in target module."
            )
            evidences.append(ev)
            return ValidationStatus.CONTRADICTED, evidences, f"Import path for `{sym_name}` is broken."

        return ValidationStatus.INSUFFICIENT_EVIDENCE, evidences, "Import path verification inconclusive."
