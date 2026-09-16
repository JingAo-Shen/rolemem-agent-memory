"""
Fine-Grained Symbol-Level Artifact Digest Prototype.
Parses Python source files into individual AST symbol definitions (functions, classes, constants)
and computes canonical SHA-256 digests to prevent false invalidation of unmodified symbols.
"""

import ast
import hashlib
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass


@dataclass
class SymbolDigest:
    symbol_name: str
    symbol_type: str  # 'function', 'class', 'assignment'
    canonical_digest: str
    lineno: int


class SymbolDigestExtractor:
    """Extracts canonical AST digests for top-level symbols in Python source code."""

    @staticmethod
    def extract_symbol_digests(source_code: str) -> Dict[str, SymbolDigest]:
        digests: Dict[str, SymbolDigest] = {}
        try:
            tree = ast.parse(source_code)
        except SyntaxError:
            return digests

        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Canonical representation: dump AST without lineno/col_offset
                canonical_ast = ast.dump(node, annotate_fields=True, include_attributes=False)
                digest = hashlib.sha256(canonical_ast.encode('utf-8')).hexdigest()
                digests[node.name] = SymbolDigest(
                    symbol_name=node.name,
                    symbol_type="function",
                    canonical_digest=digest,
                    lineno=node.lineno
                )
            elif isinstance(node, ast.ClassDef):
                canonical_ast = ast.dump(node, annotate_fields=True, include_attributes=False)
                digest = hashlib.sha256(canonical_ast.encode('utf-8')).hexdigest()
                digests[node.name] = SymbolDigest(
                    symbol_name=node.name,
                    symbol_type="class",
                    canonical_digest=digest,
                    lineno=node.lineno
                )
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        canonical_ast = ast.dump(node, annotate_fields=True, include_attributes=False)
                        digest = hashlib.sha256(canonical_ast.encode('utf-8')).hexdigest()
                        digests[target.id] = SymbolDigest(
                            symbol_name=target.id,
                            symbol_type="assignment",
                            canonical_digest=digest,
                            lineno=node.lineno
                        )
        return digests


class FineGrainedValidityEvaluator:
    """Evaluates symbol-level validity and calculates False Invalidation Rate."""

    @staticmethod
    def check_symbol_validity(
        symbol_name: str,
        recorded_symbol_digest: str,
        current_file_content: str
    ) -> bool:
        """
        Check if specific symbol is still valid in current file.
        Returns True if symbol exists and its AST canonical digest is identical.
        """
        current_digests = SymbolDigestExtractor.extract_symbol_digests(current_file_content)
        if symbol_name not in current_digests:
            return False
        return current_digests[symbol_name].canonical_digest == recorded_symbol_digest

    @staticmethod
    def compute_invalidation_metrics(
        total_valid_memories: int,
        falsely_invalidated_memories: int,
        total_retrieved_memories: int,
        exposed_stale_memories: int
    ) -> Dict[str, float]:
        false_invalidation_rate = (
            falsely_invalidated_memories / max(1, total_valid_memories)
        )
        stale_exposure_rate = (
            exposed_stale_memories / max(1, total_retrieved_memories)
        )
        return {
            "false_invalidation_rate": false_invalidation_rate,
            "stale_exposure_rate": stale_exposure_rate
        }
