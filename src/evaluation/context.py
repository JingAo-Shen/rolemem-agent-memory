"""
src/evaluation/context.py

Unified Evaluation Context for Protocol V2.2:
- Encapsulates all code snapshots, commit metadata, statements, and artifacts needed for evaluation.
- Ensures all baselines and claim-aware engines operate on identical source representations (parity).
"""

import os
import json
import hashlib
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List


@dataclass
class EvaluationContext:
    """Unified evaluation context provided to all validity verification mechanisms."""
    repository: str
    base_commit: str
    target_commit: str
    file_path: str
    base_full_source: str
    target_full_source: str
    diff: str
    memory_statement: str
    symbol: str = ""
    repository_root: Optional[str] = None
    optional_execution_evidence: Optional[Dict[str, Any]] = None
    case_id: Optional[str] = None
    claim_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def base_file_hash(self) -> str:
        return hashlib.sha256(self.base_full_source.encode("utf-8")).hexdigest()

    @property
    def target_file_hash(self) -> str:
        return hashlib.sha256(self.target_full_source.encode("utf-8")).hexdigest()

    @property
    def is_file_unchanged(self) -> bool:
        return self.base_file_hash == self.target_file_hash

    def to_dict(self) -> Dict[str, Any]:
        return {
            "case_id": self.case_id,
            "claim_id": self.claim_id,
            "repository": self.repository,
            "base_commit": self.base_commit,
            "target_commit": self.target_commit,
            "file_path": self.file_path,
            "symbol": self.symbol,
            "memory_statement": self.memory_statement,
            "base_file_hash": self.base_file_hash,
            "target_file_hash": self.target_file_hash,
            "is_file_unchanged": self.is_file_unchanged,
            "has_execution_evidence": self.optional_execution_evidence is not None,
            "metadata": self.metadata
        }


def build_evaluation_context(
    repository: str,
    base_commit: str,
    target_commit: str,
    file_path: str,
    base_source: str,
    target_source: str,
    diff: str,
    memory_statement: str,
    symbol: str = "",
    repository_root: Optional[str] = None,
    execution_evidence: Optional[Dict[str, Any]] = None,
    case_id: Optional[str] = None,
    claim_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> EvaluationContext:
    """Constructs an EvaluationContext instance with validation."""
    return EvaluationContext(
        repository=repository,
        base_commit=base_commit,
        target_commit=target_commit,
        file_path=file_path,
        base_full_source=base_source or "",
        target_full_source=target_source or "",
        diff=diff or "",
        memory_statement=memory_statement or "",
        symbol=symbol or "",
        repository_root=repository_root,
        optional_execution_evidence=execution_evidence,
        case_id=case_id,
        claim_id=claim_id,
        metadata=metadata or {}
    )
