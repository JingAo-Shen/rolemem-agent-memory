"""
src/claim_validity/validators/default_value.py

Validates ClaimType.DEFAULT_VALUE:
- Checks target function parameter default value in AST.
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


class DefaultValueValidator(BaseClaimValidator):
    @property
    def target_claim_type(self) -> ClaimType:
        return ClaimType.DEFAULT_VALUE

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
        param_name = claim.qualifiers.get("parameter_name", "")
        expected_default = claim.qualifiers.get("expected_default", claim.object)
        evidences = []

        if grounded_claim.grounding_status == GroundingStatus.UNRESOLVED:
            ev = ClaimEvidence(
                evidence_type=EvidenceType.AST,
                source="target_source_ast",
                claim_id=cid,
                supports_or_contradicts="CONTRADICTS",
                confidence=0.90,
                artifact_hash=sha256_text(target_source),
                detail=f"Function `{sym_name}` is unresolved in target source."
            )
            evidences.append(ev)
            return ValidationStatus.CONTRADICTED, evidences, f"Function `{sym_name}` does not exist."

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
            return ValidationStatus.INSUFFICIENT_EVIDENCE, evidences, f"Function node `{sym_name}` not found in AST."

        # Match parameter default
        # In Python AST, args.defaults aligns with the last N args in args.args
        args = target_func.args.args
        defaults = target_func.args.defaults
        offset = len(args) - len(defaults)
        
        found_param = False
        actual_val_str = None
        for i, arg in enumerate(args):
            if arg.arg == param_name:
                found_param = True
                if i >= offset:
                    def_node = defaults[i - offset]
                    actual_val_str = ast.unparse(def_node) if hasattr(ast, "unparse") else str(def_node)
                break

        if not found_param:
            ev = ClaimEvidence(
                evidence_type=EvidenceType.AST,
                source="target_source_ast",
                claim_id=cid,
                supports_or_contradicts="CONTRADICTS",
                confidence=0.92,
                artifact_hash=sha256_text(target_source),
                detail=f"Parameter `{param_name}` not found in function `{sym_name}`."
            )
            evidences.append(ev)
            return ValidationStatus.CONTRADICTED, evidences, f"Parameter `{param_name}` does not exist on `{sym_name}`."

        if actual_val_str is not None:
            clean_actual = actual_val_str.strip().strip("'\"")
            clean_expected = str(expected_default).strip().strip("'\"")
            if clean_actual == clean_expected:
                ev = ClaimEvidence(
                    evidence_type=EvidenceType.AST,
                    source="target_source_ast",
                    claim_id=cid,
                    supports_or_contradicts="SUPPORTS",
                    confidence=0.95,
                    artifact_hash=sha256_text(target_source),
                    detail=f"Parameter `{param_name}` default value is `{actual_val_str}`."
                )
                evidences.append(ev)
                return ValidationStatus.SUPPORTED, evidences, f"Default value matches expectation."
            else:
                ev = ClaimEvidence(
                    evidence_type=EvidenceType.AST,
                    source="target_source_ast",
                    claim_id=cid,
                    supports_or_contradicts="CONTRADICTS",
                    confidence=0.92,
                    artifact_hash=sha256_text(target_source),
                    detail=f"Parameter `{param_name}` default changed: expected `{clean_expected}`, found `{clean_actual}`."
                )
                evidences.append(ev)
                return ValidationStatus.CONTRADICTED, evidences, f"Default value altered from `{clean_expected}` to `{clean_actual}`."

        return ValidationStatus.INSUFFICIENT_EVIDENCE, evidences, f"Parameter `{param_name}` has no default value."
