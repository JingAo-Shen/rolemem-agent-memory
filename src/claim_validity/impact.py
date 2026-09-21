"""
src/claim_validity/impact.py

AST Dependency Impact Tracer for Protocol V2.2:
- Traces structural AST dependency linkage and downstream changes.
- Positioned strictly as "AST Dependency Linkage" (structural call and import graphs).
- Computes ClaimImpact for fine-grained claim invalidation analysis.
"""

import ast
import textwrap
from typing import List, Dict, Any, Optional, Set, Tuple
from src.validity.dependency_graph import DependencyGraphVerifier
from .types import ClaimImpact, MemoryClaim, GroundedClaim


class ASTDependencyImpactTracer:
    """Traces AST structural call chains and import graphs to evaluate change impacts on claims."""

    def __init__(self):
        self.dep_verifier = DependencyGraphVerifier()

    def trace_impact(
        self,
        grounded_claim: GroundedClaim,
        base_source: str,
        target_source: str,
        diff_hunk: str = "",
        dependency_symbols: Optional[List[str]] = None
    ) -> ClaimImpact:
        claim = grounded_claim.claim
        sym_name = (claim.subject or claim.symbol).split(".")[-1]
        
        impact = ClaimImpact()

        # 1. Direct subject change check
        if diff_hunk and sym_name:
            removed_lines = [l[1:].strip() for l in diff_hunk.splitlines() if l.startswith("-") and not l.startswith("---")]
            added_lines = [l[1:].strip() for l in diff_hunk.splitlines() if l.startswith("+") and not l.startswith("+++")]

            for rline in removed_lines:
                if f"def {sym_name}" in rline or f"class {sym_name}" in rline:
                    impact.direct_subject_changed = True
                    if not any(f"def {sym_name}" in aline or f"class {sym_name}" in aline for aline in added_lines):
                        impact.referenced_symbol_removed = True
                    else:
                        impact.signature_changed = True

                if "import " in rline and sym_name in rline:
                    impact.import_path_changed = True

            for aline in added_lines:
                if "deprecationwarning" in aline.lower() or "deprecated" in aline.lower():
                    if sym_name in aline or not removed_lines:
                        impact.deprecation_changed = True

        # 2. Downstream / Intra-module AST dependency linkage tracing
        if dependency_symbols and base_source:
            for dep_sym in dependency_symbols:
                dep_path_res = self.dep_verifier.verify_linkage(
                    source_code=base_source,
                    source_symbol=sym_name,
                    dependency_symbol=dep_sym
                )
                if dep_path_res.linkage_verified and dep_path_res.path:
                    impact.impact_paths.append(dep_path_res.path)
                    # If the dependency was removed or changed in diff
                    if diff_hunk:
                        dep_unqual = dep_sym.split(".")[-1]
                        for rline in diff_hunk.splitlines():
                            if rline.startswith("-") and (f"def {dep_unqual}" in rline or f"class {dep_unqual}" in rline or dep_unqual in rline):
                                impact.dependency_path_changed = True

        return impact
