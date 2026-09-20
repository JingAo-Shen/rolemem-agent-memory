"""
src/validity/types.py

Standardized types and data structures for the RoleMem Production Validity Engine.
Protocol V2.1 specification.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Literal

ValidityDecision = Literal["VALID", "STALE", "UNCERTAIN"]


@dataclass
class ValidityEvidence:
    evidence_type: str
    source: str
    detail: str
    confidence: float


@dataclass
class ValidityResult:
    decision: ValidityDecision
    confidence: float
    reasons: List[str] = field(default_factory=list)
    evidence: List[ValidityEvidence] = field(default_factory=list)

    file_changed: Optional[bool] = None
    symbol_changed: Optional[bool] = None
    symbol_removed: Optional[bool] = None
    dependency_changed: Optional[bool] = None
