"""
src/claim_validity/validators/return_value.py

Validates ClaimType.RETURN_VALUE:
- Checks target function return type annotations or return statements.
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


class ReturnValueValidator(BaseClaimValidator):
    @property
    def target_claim_type(self) -> ClaimType:
        return ClaimType.RETURN_VALUE

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
        expected_ret = claim.object
        evidences = []

        if grounded_claim.grounding_status == GroundingStatus.UNRESOLVED:
            ev = ClaimEvidence(
                evidence_type=EvidenceType.AST,
                source="target_source_ast",
                claim_id=cid,
                supports_or_contradicts="CONTRADICTS",
                confidence=0.90,
                artifact_hash=sha256_text(target_source),
                detail=f"Symbol `{sym_name}` is unresolved in target source."
            )
            evidences.append(ev)
            return ValidationStatus.CONTRADICTED, evidences, f"Symbol `{sym_name}` does not exist."

        try:
            tree = ast.parse(textwrap.dedent(target_source))
        except Exception as e:
            return ValidationStatus.INSUFFICIENT_EVIDENCE, evidences, f"AST parsing failed: {e}"

        target_func = None
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == sym_name:
                target_func = node
                break

        if target_func is None:
            return ValidationStatus.INSUFFICIENT_EVIDENCE, evidences, f"Function `{sym_name}` not found in AST."

        # Check return annotation if available
        if target_func.returns:
            ret_str = ast.unparse(target_func.returns) if hasattr(ast, "unparse") else str(target_func.returns)
            clean_actual = ret_str.strip()
            clean_exp = expected_ret.strip()
            if clean_exp in clean_actual or clean_actual in clean_exp:
                ev = ClaimEvidence(
                    evidence_type=EvidenceType.AST,
                    source="target_source_ast",
                    claim_id=cid,
                    supports_or_contradicts="SUPPORTS",
                    confidence=0.94,
                    artifact_hash=sha256_text(target_source),
                    detail=f"Function `{sym_name}` return type annotation matches: `{ret_str}`."
                )
                evidences.append(ev)
                return ValidationStatus.SUPPORTED, evidences, f"Return value type matches `{clean_exp}`."

        # Check return expressions inside body
        return_nodes = [n for n in ast.walk(target_func) if isinstance(n, ast.Return) and n.value is not None]
        if return_nodes:
            for rn in return_nodes:
                ret_expr = ast.unparse(rn.value) if hasattr(ast, "unparse") else ""
                if expected_ret.strip() in ret_expr:
                    ev = ClaimEvidence(
                        evidence_type=EvidenceType.AST,
                        source="target_source_ast",
                        claim_id=cid,
                        supports_or_contradicts="SUPPORTS",
                        confidence=0.92,
                        artifact_hash=sha256_text(target_source),
                        detail=f"Function `{sym_name}` contains return statement: `return {ret_expr}`."
                    )
                    evidences.append(ev)
                    return ValidationStatus.SUPPORTED, evidences, f"Return statement matches `{expected_ret}`."

        return ValidationStatus.INSUFFICIENT_EVIDENCE, evidences, "Return value verification inconclusive."
