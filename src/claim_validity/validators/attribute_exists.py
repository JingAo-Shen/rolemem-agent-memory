"""
src/claim_validity/validators/attribute_exists.py

Validates ClaimType.ATTRIBUTE_EXISTS:
- SUPPORTED if attribute / method exists in parent symbol's class AST or module AST.
- CONTRADICTED if parent exists but attribute is missing/deleted, or parent itself is deleted.
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


class AttributeExistsValidator(BaseClaimValidator):
    @property
    def target_claim_type(self) -> ClaimType:
        return ClaimType.ATTRIBUTE_EXISTS

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
        parent_name = (claim.subject or claim.symbol).split(".")[-1]
        attr_name = claim.object
        evidences = []

        if grounded_claim.grounding_status == GroundingStatus.UNRESOLVED:
            ev = ClaimEvidence(
                evidence_type=EvidenceType.AST,
                source="target_source_ast",
                claim_id=cid,
                supports_or_contradicts="CONTRADICTS",
                confidence=0.92,
                artifact_hash=sha256_text(target_source),
                detail=f"Parent symbol `{parent_name}` is unresolved in target source."
            )
            evidences.append(ev)
            return ValidationStatus.CONTRADICTED, evidences, f"Parent symbol `{parent_name}` does not exist."

        try:
            tree = ast.parse(textwrap.dedent(target_source))
        except Exception as e:
            return ValidationStatus.INSUFFICIENT_EVIDENCE, evidences, f"Failed to parse target AST: {e}"

        parent_node = None
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.ClassDef) and node.name == parent_name:
                parent_node = node
                break

        if parent_node is not None:
            # Check class methods and class-level assignments
            found_attr = False
            for child in parent_node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and child.name == attr_name:
                    found_attr = True
                    break
                elif isinstance(child, (ast.Assign, ast.AnnAssign)):
                    targets = child.targets if isinstance(child, ast.Assign) else [child.target]
                    for tgt in targets:
                        if isinstance(tgt, ast.Name) and tgt.id == attr_name:
                            found_attr = True
                            break

            if found_attr:
                ev = ClaimEvidence(
                    evidence_type=EvidenceType.AST,
                    source="target_source_ast",
                    claim_id=cid,
                    supports_or_contradicts="SUPPORTS",
                    confidence=0.95,
                    artifact_hash=sha256_text(target_source),
                    detail=f"Attribute `{attr_name}` found in class `{parent_name}`."
                )
                evidences.append(ev)
                return ValidationStatus.SUPPORTED, evidences, f"Attribute `{attr_name}` exists on `{parent_name}`."
            else:
                ev = ClaimEvidence(
                    evidence_type=EvidenceType.AST,
                    source="target_source_ast",
                    claim_id=cid,
                    supports_or_contradicts="CONTRADICTS",
                    confidence=0.90,
                    artifact_hash=sha256_text(target_source),
                    detail=f"Attribute `{attr_name}` missing from class `{parent_name}`."
                )
                evidences.append(ev)
                return ValidationStatus.CONTRADICTED, evidences, f"Attribute `{attr_name}` is missing from `{parent_name}`."

        return ValidationStatus.INSUFFICIENT_EVIDENCE, evidences, f"Could not inspect parent node `{parent_name}`."
