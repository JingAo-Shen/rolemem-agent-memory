"""
src/claim_validity/validators/signature.py

Validates ClaimType.SIGNATURE_COMPATIBLE:
- Checks target function/method parameter list in AST against claimed parameters.
- SUPPORTED if parameter constraints are satisfied.
- CONTRADICTED if required parameters are missing or signature incompatible.
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


class SignatureValidator(BaseClaimValidator):
    @property
    def target_claim_type(self) -> ClaimType:
        return ClaimType.SIGNATURE_COMPATIBLE

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
                confidence=0.90,
                artifact_hash=sha256_text(target_source),
                detail=f"Function `{sym_name}` is absent from target AST."
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

        # Extract parameter names
        actual_params = [a.arg for a in target_func.args.args]
        if target_func.args.vararg:
            actual_params.append(f"*{target_func.args.vararg.arg}")
        if target_func.args.kwarg:
            actual_params.append(f"**{target_func.args.kwarg.arg}")

        expected_params = claim.qualifiers.get("expected_parameters", [])
        if not expected_params and claim.object:
            expected_params = [p.strip() for p in claim.object.split(",") if p.strip()]

        if expected_params:
            missing = [ep for ep in expected_params if ep not in actual_params and f"**{ep}" not in actual_params and not any(a.startswith("*") for a in actual_params)]
            if missing:
                ev = ClaimEvidence(
                    evidence_type=EvidenceType.AST,
                    source="target_source_ast",
                    claim_id=cid,
                    supports_or_contradicts="CONTRADICTS",
                    confidence=0.92,
                    artifact_hash=sha256_text(target_source),
                    detail=f"Function `{sym_name}` signature lacks required parameters: {missing} (Actual: {actual_params})."
                )
                evidences.append(ev)
                return ValidationStatus.CONTRADICTED, evidences, f"Signature missing required parameters: {missing}."
            else:
                ev = ClaimEvidence(
                    evidence_type=EvidenceType.AST,
                    source="target_source_ast",
                    claim_id=cid,
                    supports_or_contradicts="SUPPORTS",
                    confidence=0.95,
                    artifact_hash=sha256_text(target_source),
                    detail=f"Function `{sym_name}` signature satisfies expected parameters {expected_params}."
                )
                evidences.append(ev)
                return ValidationStatus.SUPPORTED, evidences, f"Signature parameters match expectation."

        ev = ClaimEvidence(
            evidence_type=EvidenceType.AST,
            source="target_source_ast",
            claim_id=cid,
            supports_or_contradicts="SUPPORTS",
            confidence=0.90,
            artifact_hash=sha256_text(target_source),
            detail=f"Function `{sym_name}` is a valid callable with parameters {actual_params}."
        )
        evidences.append(ev)
        return ValidationStatus.SUPPORTED, evidences, f"Callable signature verified."
