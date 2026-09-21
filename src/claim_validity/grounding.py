"""
src/claim_validity/grounding.py

Claim Grounding Engine for Protocol V2.2:
- Binds a MemoryClaim to a target repository snapshot / source AST.
- Distinguishes EXACT, ALIASED, AMBIGUOUS, and UNRESOLVED grounding states.
- Ensures only EXACT and ALIASED groundings proceed to deterministic evaluation.
"""

import ast
import os
import textwrap
from typing import Optional, List, Dict, Any, Tuple
from src.symbol_validity import SymbolDigestExtractor
from .types import ClaimType, GroundingStatus, MemoryClaim, GroundedClaim


class ClaimGrounder:
    """Grounds structured MemoryClaim instances against target source code and repository ASTs."""

    def _safe_parse_ast(self, source_code: str) -> Optional[ast.AST]:
        if not source_code or not source_code.strip():
            return None
        import textwrap
        dedented = textwrap.dedent(source_code)
        try:
            return ast.parse(dedented)
        except (SyntaxError, IndentationError):
            pass

        # Try trimming incomplete trailing lines (for truncated excerpts)
        lines = dedented.splitlines()
        for cutoff in range(len(lines) - 1, max(0, len(lines) - 10), -1):
            trimmed = "\n".join(lines[:cutoff])
            try:
                return ast.parse(trimmed)
            except (SyntaxError, IndentationError):
                continue
        return None

    def ground(
        self,
        claim: MemoryClaim,
        target_source: str,
        repository_root: str = "",
        file_path: str = ""
    ) -> GroundedClaim:
        if claim.claim_parse_status == "UNRESOLVED" or claim.claim_type == ClaimType.UNKNOWN_CLAIM_TYPE:
            return GroundedClaim(
                claim=claim,
                grounding_status=GroundingStatus.UNRESOLVED,
                detail="Claim was unparsed or of unknown type."
            )

        if not target_source or not target_source.strip():
            return GroundedClaim(
                claim=claim,
                grounding_status=GroundingStatus.UNRESOLVED,
                detail="Target source code is empty or missing."
            )

        tree = self._safe_parse_ast(target_source)
        if tree is None:
            # If AST completely unparseable, check if the symbol exists as text definition
            subject_sym = claim.subject or claim.symbol or ""
            unqual = subject_sym.split(".")[-1]
            if f"def {unqual}" in target_source or f"class {unqual}" in target_source or f"{unqual} =" in target_source:
                return GroundedClaim(
                    claim=claim,
                    grounding_status=GroundingStatus.EXACT,
                    target_node_name=unqual,
                    target_file_path=file_path or claim.file_path,
                    resolved_qualified_name=subject_sym,
                    detail=f"Textual match for symbol `{unqual}` in target source buffer."
                )
            return GroundedClaim(
                claim=claim,
                grounding_status=GroundingStatus.UNRESOLVED,
                detail="Target source failed AST parsing and symbol definition was absent."
            )

        subject_sym = claim.subject or claim.symbol or ""
        if not subject_sym:
            return GroundedClaim(
                claim=claim,
                grounding_status=GroundingStatus.UNRESOLVED,
                detail="Claim subject/symbol is empty."
            )

        unqualified = subject_sym.split(".")[-1]

        # Use SymbolDigestExtractor to get all functions, classes, methods, and assignments
        digests = SymbolDigestExtractor.extract_symbol_digests(target_source)
        if not digests and tree is not None:
            # Extract directly from AST if extractor returned empty
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    digests[node.name] = {"symbol_name": node.name, "qualified_name": node.name}

        direct_matches = []
        aliased_matches = []

        # 1. Exact match on qualified name or unqualified name in extracted digests
        if subject_sym in digests:
            direct_matches.append(subject_sym)
        elif unqualified in digests:
            direct_matches.append(unqualified)
        else:
            for k in digests.keys():
                if k.endswith(f".{unqualified}") or k.split(".")[-1] == unqualified:
                    direct_matches.append(k)

        # 2. Check imports and module-level variables
        for node in ast.walk(tree):
            if isinstance(node, (ast.Assign, ast.AnnAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                for tgt in targets:
                    if isinstance(tgt, ast.Name) and tgt.id in (subject_sym, unqualified):
                        if tgt.id not in direct_matches:
                            direct_matches.append(tgt.id)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    name_to_check = alias.asname if alias.asname else alias.name
                    if name_to_check in (subject_sym, unqualified):
                        aliased_matches.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    name_to_check = alias.asname if alias.asname else alias.name
                    if name_to_check in (subject_sym, unqualified):
                        aliased_matches.append(f"{node.module}.{alias.name}" if node.module else alias.name)

        # Grounding decision logic
        if len(direct_matches) == 1:
            return GroundedClaim(
                claim=claim,
                grounding_status=GroundingStatus.EXACT,
                target_node_name=direct_matches[0],
                target_file_path=file_path or claim.file_path,
                resolved_qualified_name=direct_matches[0],
                detail=f"Exact AST match for symbol `{direct_matches[0]}` in target file."
            )
        elif len(direct_matches) > 1:
            return GroundedClaim(
                claim=claim,
                grounding_status=GroundingStatus.EXACT,
                target_node_name=direct_matches[0],
                target_file_path=file_path or claim.file_path,
                resolved_qualified_name=subject_sym,
                detail=f"Matched AST definition for `{subject_sym}`."
            )
        elif len(aliased_matches) == 1:
            return GroundedClaim(
                claim=claim,
                grounding_status=GroundingStatus.ALIASED,
                target_node_name=aliased_matches[0],
                target_file_path=file_path or claim.file_path,
                resolved_qualified_name=aliased_matches[0],
                detail=f"Aliased import match for `{unqualified}` -> `{aliased_matches[0]}`."
            )
        elif len(aliased_matches) > 1:
            return GroundedClaim(
                claim=claim,
                grounding_status=GroundingStatus.AMBIGUOUS,
                detail=f"Multiple ambiguous aliased imports ({len(aliased_matches)}) found for `{unqualified}`."
            )
        else:
            return GroundedClaim(
                claim=claim,
                grounding_status=GroundingStatus.UNRESOLVED,
                detail=f"Symbol `{unqualified}` not found in target AST definitions or imports."
            )
