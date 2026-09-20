"""
src/validity/engine.py

RoleMem Unified Production Validity Engine.
Protocol V2.1 specification.

Combines Symbol-level canonical AST digests with Static AST Dependency verification
to provide structured, explainable, and machine-verified memory validity decisions.
Zero benchmark-specific keyword heuristics.
"""

from typing import Optional, List, Dict, Any
from .types import ValidityDecision, ValidityResult, ValidityEvidence
from .symbol_validity import SymbolValidityChecker
from .dependency_validity import DependencyValidityChecker
from .file_validity import FileValidityChecker


class RoleMemValidityEngine:
    """Unified Production Engine for evaluating Agent Memory validity across software transitions."""

    def __init__(self):
        self.symbol_checker = SymbolValidityChecker()
        self.dep_checker = DependencyValidityChecker()
        self.file_checker = FileValidityChecker()

    def evaluate(
        self,
        *,
        memory_statement: str = "",
        symbol_qualified_name: str,
        base_source: str,
        target_source: str,
        repository_root: Optional[str] = None,
        base_commit: Optional[str] = None,
        target_commit: Optional[str] = None,
        file_path: Optional[str] = None,
        diff_hunk: Optional[str] = None,
    ) -> ValidityResult:
        """
        Evaluates memory validity:
        1. Symbol removed in target -> STALE
        2. Symbol unchanged (digest match):
           - Dependency broken -> STALE
           - Dependency intact -> VALID
           - Dependency uncertain -> VALID (with symbol unchanged confidence)
        3. Symbol digest changed -> UNCERTAIN (Structural edit != semantic invalidation)
        """
        # Step 1: Symbol-level AST digest check
        sym_res = self.symbol_checker.evaluate(
            base_source=base_source,
            target_source=target_source,
            symbol_qualified_name=symbol_qualified_name,
        )

        # Case 1: Symbol removed -> STALE
        if sym_res.symbol_removed:
            return ValidityResult(
                decision="STALE",
                confidence=sym_res.confidence,
                reasons=sym_res.reasons,
                evidence=sym_res.evidence,
                file_changed=(base_source != target_source),
                symbol_changed=True,
                symbol_removed=True,
                dependency_changed=None
            )

        # Case 2: Symbol unchanged (identical AST digest)
        if sym_res.decision == "VALID" and not sym_res.symbol_changed:
            # Check dependencies
            dep_res = self.dep_checker.evaluate(
                base_source=base_source,
                target_source=target_source,
                symbol_qualified_name=symbol_qualified_name,
                diff_hunk=diff_hunk or ""
            )

            all_evidence = list(sym_res.evidence) + list(dep_res.evidence)

            if dep_res.decision == "STALE" and dep_res.dependency_changed:
                return ValidityResult(
                    decision="STALE",
                    confidence=dep_res.confidence,
                    reasons=[f"Symbol `{symbol_qualified_name}` unchanged, but referenced dependency was broken."] + dep_res.reasons,
                    evidence=all_evidence,
                    file_changed=(base_source != target_source),
                    symbol_changed=False,
                    symbol_removed=False,
                    dependency_changed=True
                )
            else:
                # Symbol unchanged and dependencies intact/unbroken
                return ValidityResult(
                    decision="VALID",
                    confidence=min(sym_res.confidence, dep_res.confidence if dep_res.decision == "VALID" else 0.90),
                    reasons=sym_res.reasons + dep_res.reasons,
                    evidence=all_evidence,
                    file_changed=(base_source != target_source),
                    symbol_changed=False,
                    symbol_removed=False,
                    dependency_changed=False
                )

        # Case 3: Symbol digest changed (AST modified)
        if sym_res.symbol_changed and not sym_res.symbol_removed:
            return ValidityResult(
                decision="UNCERTAIN",
                confidence=0.50,
                reasons=[f"Symbol `{symbol_qualified_name}` AST digest changed; behavioral semantic claim requires verification."] + sym_res.reasons,
                evidence=sym_res.evidence,
                file_changed=(base_source != target_source),
                symbol_changed=True,
                symbol_removed=False,
                dependency_changed=None
            )

        # Fallback / baseline check
        return sym_res
