"""
src/validity/symbol_validity.py

AST-based Symbol-level validity checker.
Protocol V2.1 specification.

Uses SymbolDigestExtractor to compare canonical AST dumps of specific symbols.
- Unchanged digest -> VALID
- Removed symbol -> STALE
- Changed digest -> UNCERTAIN (Structural edit != semantic staleness)
"""

from typing import Dict, Any, Optional
from src.symbol_validity import SymbolDigestExtractor
from .types import ValidityResult, ValidityEvidence


class SymbolValidityChecker:
    """Evaluates memory validity by comparing canonical AST digests of specific symbols."""

    def __init__(self):
        self.extractor = SymbolDigestExtractor

    def evaluate(
        self,
        base_source: str,
        target_source: str,
        symbol_qualified_name: str,
    ) -> ValidityResult:
        base_digests = self.extractor.extract_symbol_digests(base_source)
        target_digests = self.extractor.extract_symbol_digests(target_source)

        base_info = base_digests.get(symbol_qualified_name)
        target_info = target_digests.get(symbol_qualified_name)

        if not base_info:
            # Fallback: check unqualified base name if qualified name has dotted prefix
            unqualified = symbol_qualified_name.split(".")[-1]
            for k, v in base_digests.items():
                if k == unqualified or k.endswith(f".{unqualified}"):
                    base_info = v
                    symbol_qualified_name = k
                    break

        if not base_info:
            return ValidityResult(
                decision="UNCERTAIN",
                confidence=0.30,
                reasons=[f"Symbol `{symbol_qualified_name}` not found in base source."],
                evidence=[
                    ValidityEvidence(
                        evidence_type="base_symbol_not_found",
                        source="base_source",
                        detail=f"AST parse could not locate `{symbol_qualified_name}` in base file.",
                        confidence=0.30
                    )
                ],
                file_changed=None,
                symbol_changed=None,
                symbol_removed=None,
                dependency_changed=None
            )

        # Check in target
        if not target_info:
            unqualified = symbol_qualified_name.split(".")[-1]
            for k, v in target_digests.items():
                if k == unqualified or k.endswith(f".{unqualified}"):
                    target_info = v
                    break

        if not target_info:
            return ValidityResult(
                decision="STALE",
                confidence=1.0,
                reasons=[f"Symbol `{symbol_qualified_name}` was removed or renamed in target source."],
                evidence=[
                    ValidityEvidence(
                        evidence_type="symbol_removed",
                        source="target_source",
                        detail=f"Target AST contains no definition for `{symbol_qualified_name}`.",
                        confidence=1.0
                    )
                ],
                file_changed=None,
                symbol_changed=True,
                symbol_removed=True,
                dependency_changed=None
            )

        base_digest = base_info["symbol_digest"]
        target_digest = target_info["symbol_digest"]

        if base_digest == target_digest:
            return ValidityResult(
                decision="VALID",
                confidence=0.95,
                reasons=[f"Symbol `{symbol_qualified_name}` AST digest identical ({base_digest[:12]}...)."],
                evidence=[
                    ValidityEvidence(
                        evidence_type="symbol_digest_match",
                        source="ast_comparison",
                        detail=f"Canonical AST digest unchanged: {base_digest}",
                        confidence=0.95
                    )
                ],
                file_changed=None,
                symbol_changed=False,
                symbol_removed=False,
                dependency_changed=None
            )
        else:
            return ValidityResult(
                decision="UNCERTAIN",
                confidence=0.50,
                reasons=[f"Symbol `{symbol_qualified_name}` AST digest changed (base: {base_digest[:8]}..., target: {target_digest[:8]}...)."],
                evidence=[
                    ValidityEvidence(
                        evidence_type="symbol_digest_mismatch",
                        source="ast_comparison",
                        detail=f"Canonical AST digest altered from {base_digest} to {target_digest}",
                        confidence=0.50
                    )
                ],
                file_changed=None,
                symbol_changed=True,
                symbol_removed=False,
                dependency_changed=None
            )
