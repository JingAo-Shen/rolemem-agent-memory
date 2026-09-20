#!/usr/bin/env python3
"""
src/symbol_validity.py
RoleMem Formal Symbol-Level Validity Architecture.

Distinction:
- ASTStaleActionDetector = Output behavior evaluator (evaluating agent generated code).
- SymbolValidity = Memory validity mechanism (governing memory record lifecycle: ACTIVE vs INVALID).

Baselines & Methods:
1. F-file (File-Level Validity Baseline):
   - Computes whole-file SHA-256 (artifact_digest).
   - If current file SHA != recorded artifact_digest -> Mark INVALID (even if target symbol is untouched).
2. F-symbol (Symbol-Level Validity Mechanism):
   - Computes canonical AST digest of target symbol (symbol_digest).
   - If target symbol AST digest is identical -> Keep ACTIVE (resilient to unrelated file edits).
   - If target symbol is modified, renamed, or deleted -> Mark INVALID.
"""

import ast
import hashlib
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field


@dataclass
class MemoryRecord:
    memory_id: str
    artifact_uri: str
    artifact_type: str  # 'file', 'module'
    symbol_qualified_name: str
    symbol_digest: str  # SHA-256 of canonical AST dump of target symbol
    artifact_digest: str  # SHA-256 of whole file
    statement: str
    status: str = "ACTIVE"  # "ACTIVE" | "INVALID"
    evidence_ref: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class SymbolDigestExtractor:
    """Extracts canonical AST digests for top-level and class-nested symbols."""

    @staticmethod
    def _canonical_ast_dump(node: ast.AST) -> str:
        """Serializes AST without line/col annotations for pure structural/semantic comparison."""
        return ast.dump(node, annotate_fields=True, include_attributes=False)

    @classmethod
    def extract_symbol_digests(cls, source_code: str) -> Dict[str, Dict[str, Any]]:
        """
        Parses source code and returns mapping:
        qualified_name -> {
            'symbol_name': str,
            'qualified_name': str,
            'symbol_type': 'function' | 'class' | 'method' | 'assignment',
            'symbol_digest': str (sha256),
            'lineno': int
        }
        """
        digests: Dict[str, Dict[str, Any]] = {}
        try:
            tree = ast.parse(source_code)
        except SyntaxError:
            return digests

        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                canonical = cls._canonical_ast_dump(node)
                digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
                digests[node.name] = {
                    "symbol_name": node.name,
                    "qualified_name": node.name,
                    "symbol_type": "function",
                    "symbol_digest": digest,
                    "lineno": node.lineno
                }
            elif isinstance(node, ast.ClassDef):
                canonical = cls._canonical_ast_dump(node)
                digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
                digests[node.name] = {
                    "symbol_name": node.name,
                    "qualified_name": node.name,
                    "symbol_type": "class",
                    "symbol_digest": digest,
                    "lineno": node.lineno
                }
                # Also index class methods and attributes
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        qname = f"{node.name}.{item.name}"
                        m_canon = cls._canonical_ast_dump(item)
                        m_dig = hashlib.sha256(m_canon.encode("utf-8")).hexdigest()
                        digests[qname] = {
                            "symbol_name": item.name,
                            "qualified_name": qname,
                            "symbol_type": "method",
                            "symbol_digest": m_dig,
                            "lineno": item.lineno
                        }
                    elif isinstance(item, ast.Assign):
                        for target in item.targets:
                            if isinstance(target, ast.Name):
                                qname = f"{node.name}.{target.id}"
                                a_canon = cls._canonical_ast_dump(item)
                                a_dig = hashlib.sha256(a_canon.encode("utf-8")).hexdigest()
                                digests[qname] = {
                                    "symbol_name": target.id,
                                    "qualified_name": qname,
                                    "symbol_type": "assignment",
                                    "symbol_digest": a_dig,
                                    "lineno": item.lineno
                                }
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        canonical = cls._canonical_ast_dump(node)
                        digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
                        digests[target.id] = {
                            "symbol_name": target.id,
                            "qualified_name": target.id,
                            "symbol_type": "assignment",
                            "symbol_digest": digest,
                            "lineno": node.lineno
                        }
        return digests


class FileLevelValidityEvaluator:
    """F-file Baseline: Invalidate memory if file SHA-256 changes."""

    @staticmethod
    def evaluate(record: MemoryRecord, current_file_content: str) -> str:
        current_sha = hashlib.sha256(current_file_content.encode("utf-8")).hexdigest()
        if current_sha == record.artifact_digest:
            return "ACTIVE"
        return "INVALID"


class SymbolLevelValidityEvaluator:
    """F-symbol Mechanism: Invalidate memory only if target symbol AST digest changes or symbol is removed."""

    @staticmethod
    def evaluate(record: MemoryRecord, current_file_content: str) -> str:
        digests = SymbolDigestExtractor.extract_symbol_digests(current_file_content)
        qname = record.symbol_qualified_name
        short_name = qname.split(".")[-1]

        target_info = digests.get(qname) or digests.get(short_name)
        if not target_info:
            return "INVALID"

        if target_info["symbol_digest"] == record.symbol_digest:
            return "ACTIVE"
        return "INVALID"


class ValidityMetricsCalculator:
    """Computes False Invalidation Rate, Stale Exposure Rate, and Recall."""

    @staticmethod
    def compute(
        ground_truth_valid: List[bool],  # True if memory is truly valid at target state
        predicted_active: List[bool]      # True if validity mechanism kept memory ACTIVE
    ) -> Dict[str, float]:
        assert len(ground_truth_valid) == len(predicted_active), "Length mismatch"
        total_valid = sum(1 for g in ground_truth_valid if g)
        total_stale = sum(1 for g in ground_truth_valid if not g)
        total_active = sum(1 for p in predicted_active if p)

        # False Invalidation: truly valid, but mechanism predicted INVALID (not active)
        false_invalidations = sum(1 for g, p in zip(ground_truth_valid, predicted_active) if g and not p)
        false_invalidation_rate = (false_invalidations / total_valid) if total_valid > 0 else 0.0

        # Stale Exposure: truly stale, but mechanism kept ACTIVE
        stale_exposures = sum(1 for g, p in zip(ground_truth_valid, predicted_active) if not g and p)
        stale_exposure_rate = (stale_exposures / total_active) if total_active > 0 else 0.0

        # Valid Memory Recall: truly valid and kept ACTIVE / total valid
        valid_recalled = sum(1 for g, p in zip(ground_truth_valid, predicted_active) if g and p)
        valid_memory_recall = (valid_recalled / total_valid) if total_valid > 0 else 0.0

        return {
            "total_samples": len(ground_truth_valid),
            "total_valid_ground_truth": total_valid,
            "total_stale_ground_truth": total_stale,
            "false_invalidations": false_invalidations,
            "false_invalidation_rate": false_invalidation_rate,
            "stale_exposures": stale_exposures,
            "stale_exposure_rate": stale_exposure_rate,
            "valid_memory_recall": valid_memory_recall
        }
