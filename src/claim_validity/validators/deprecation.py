"""
src/claim_validity/validators/deprecation.py

Validates ClaimType.DEPRECATION_STATUS:
- Checks if symbol triggers deprecation warning / deprecation decorator in target AST.
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


class DeprecationValidator(BaseClaimValidator):
    @property
    def target_claim_type(self) -> ClaimType:
        return ClaimType.DEPRECATION_STATUS

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
        expected_status = claim.object.lower()
        evidences = []

        if grounded_claim.grounding_status == GroundingStatus.UNRESOLVED:
            ev = ClaimEvidence(
                evidence_type=EvidenceType.AST,
                source="target_source_ast",
                claim_id=cid,
                supports_or_contradicts="CONTRADICTS",
                confidence=0.90,
                artifact_hash=sha256_text(target_source),
                detail=f"Symbol `{sym_name}` does not exist in target AST."
            )
            evidences.append(ev)
            return ValidationStatus.CONTRADICTED, evidences, f"Symbol `{sym_name}` is removed."

        # Scan target AST or source text for deprecation indications
        is_deprecated_in_target = False
        detail_reason = ""

        try:
            tree = ast.parse(textwrap.dedent(target_source))
            target_node = None
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.name == sym_name:
                    target_node = node
                    break

            if target_node is not None:
                # Check decorators
                for dec in getattr(target_node, "decorator_list", []):
                    dec_name = ast.unparse(dec) if hasattr(ast, "unparse") else str(dec)
                    if "deprecated" in dec_name.lower():
                        is_deprecated_in_target = True
                        detail_reason = f"Decorated with `{dec_name}`"
                        break

                # Check body for warnings.warn(..., DeprecationWarning)
                if not is_deprecated_in_target:
                    for child in ast.walk(target_node):
                        if isinstance(child, ast.Call):
                            call_str = ast.unparse(child) if hasattr(ast, "unparse") else ""
                            if "deprecationwarning" in call_str.lower() or "warnings.warn" in call_str.lower():
                                is_deprecated_in_target = True
                                detail_reason = f"Explicit warning call in body: `{call_str[:80]}`"
                                break
        except Exception:
            pass

        if not is_deprecated_in_target and "warnings.warn" in target_source and sym_name in target_source:
            if "deprecationwarning" in target_source.lower():
                is_deprecated_in_target = True
                detail_reason = "DeprecationWarning call present in module."

        if expected_status in ("deprecated", "raising deprecationwarning"):
            if is_deprecated_in_target:
                ev = ClaimEvidence(
                    evidence_type=EvidenceType.AST,
                    source="target_source_ast",
                    claim_id=cid,
                    supports_or_contradicts="SUPPORTS",
                    confidence=0.95,
                    artifact_hash=sha256_text(target_source),
                    detail=f"Symbol `{sym_name}` is deprecated in target: {detail_reason}"
                )
                evidences.append(ev)
                return ValidationStatus.SUPPORTED, evidences, f"Symbol `{sym_name}` is confirmed deprecated."
            else:
                ev = ClaimEvidence(
                    evidence_type=EvidenceType.AST,
                    source="target_source_ast",
                    claim_id=cid,
                    supports_or_contradicts="CONTRADICTS",
                    confidence=0.90,
                    artifact_hash=sha256_text(target_source),
                    detail=f"Symbol `{sym_name}` contains no deprecation warnings in target source."
                )
                evidences.append(ev)
                return ValidationStatus.CONTRADICTED, evidences, f"Symbol `{sym_name}` is not deprecated in target."

        elif expected_status in ("active", "supported", "not deprecated"):
            if not is_deprecated_in_target:
                ev = ClaimEvidence(
                    evidence_type=EvidenceType.AST,
                    source="target_source_ast",
                    claim_id=cid,
                    supports_or_contradicts="SUPPORTS",
                    confidence=0.92,
                    artifact_hash=sha256_text(target_source),
                    detail=f"Symbol `{sym_name}` remains active without deprecation."
                )
                evidences.append(ev)
                return ValidationStatus.SUPPORTED, evidences, f"Symbol `{sym_name}` remains active."
            else:
                ev = ClaimEvidence(
                    evidence_type=EvidenceType.AST,
                    source="target_source_ast",
                    claim_id=cid,
                    supports_or_contradicts="CONTRADICTS",
                    confidence=0.92,
                    artifact_hash=sha256_text(target_source),
                    detail=f"Symbol `{sym_name}` is newly deprecated in target: {detail_reason}"
                )
                evidences.append(ev)
                return ValidationStatus.CONTRADICTED, evidences, f"Symbol `{sym_name}` became deprecated."

        return ValidationStatus.INSUFFICIENT_EVIDENCE, evidences, "Deprecation status inconclusive."
