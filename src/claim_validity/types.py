"""
src/claim_validity/types.py

Core Type Definitions and Data Models for Protocol V2.2 Claim-Aware Validity:
- ClaimType: Fine-grained taxonomy of memory claim semantics.
- GroundingStatus: AST and snapshot grounding state (EXACT, ALIASED, AMBIGUOUS, UNRESOLVED).
- ValidationStatus: Tri-state validator evaluation (SUPPORTED, CONTRADICTED, INSUFFICIENT_EVIDENCE).
- EvidenceType: Evidence origin provenance (AST, GIT_DIFF, DEPENDENCY, EXECUTION, METADATA).
- MemoryClaim, GroundedClaim, ClaimEvidence, ClaimImpact, ClaimEvaluationResult.
"""

from __future__ import annotations
import json
import hashlib
from enum import Enum
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional, Set, Tuple


class ClaimType(str, Enum):
    SYMBOL_EXISTS = "SYMBOL_EXISTS"
    ATTRIBUTE_EXISTS = "ATTRIBUTE_EXISTS"
    IMPORT_PATH_VALID = "IMPORT_PATH_VALID"
    CALLABLE = "CALLABLE"
    SIGNATURE_COMPATIBLE = "SIGNATURE_COMPATIBLE"
    DEFAULT_VALUE = "DEFAULT_VALUE"
    RETURN_VALUE = "RETURN_VALUE"
    DEPRECATION_STATUS = "DEPRECATION_STATUS"
    BEHAVIORAL_CONTRACT = "BEHAVIORAL_CONTRACT"
    DEPENDENCY_CONTRACT = "DEPENDENCY_CONTRACT"
    UNKNOWN_CLAIM_TYPE = "UNKNOWN_CLAIM_TYPE"


class GroundingStatus(str, Enum):
    EXACT = "EXACT"
    ALIASED = "ALIASED"
    AMBIGUOUS = "AMBIGUOUS"
    UNRESOLVED = "UNRESOLVED"


class ValidationStatus(str, Enum):
    SUPPORTED = "SUPPORTED"
    CONTRADICTED = "CONTRADICTED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class EvidenceType(str, Enum):
    AST = "AST"
    GIT_DIFF = "GIT_DIFF"
    DEPENDENCY = "DEPENDENCY"
    EXECUTION = "EXECUTION"
    METADATA = "METADATA"


@dataclass
class ClaimEvidence:
    evidence_type: EvidenceType
    source: str
    claim_id: str
    supports_or_contradicts: str  # "SUPPORTS", "CONTRADICTS", "INCONCLUSIVE"
    confidence: float
    artifact_hash: str
    detail: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "evidence_type": self.evidence_type.value if isinstance(self.evidence_type, Enum) else str(self.evidence_type),
            "source": self.source,
            "claim_id": self.claim_id,
            "supports_or_contradicts": self.supports_or_contradicts,
            "confidence": self.confidence,
            "artifact_hash": self.artifact_hash,
            "detail": self.detail
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ClaimEvidence:
        ev_type = EvidenceType(data["evidence_type"]) if isinstance(data["evidence_type"], str) else data["evidence_type"]
        return cls(
            evidence_type=ev_type,
            source=data.get("source", ""),
            claim_id=data.get("claim_id", ""),
            supports_or_contradicts=data.get("supports_or_contradicts", "INCONCLUSIVE"),
            confidence=float(data.get("confidence", 0.0)),
            artifact_hash=data.get("artifact_hash", ""),
            detail=data.get("detail", "")
        )


@dataclass
class ClaimImpact:
    direct_subject_changed: bool = False
    dependency_path_changed: bool = False
    referenced_symbol_removed: bool = False
    signature_changed: bool = False
    import_path_changed: bool = False
    deprecation_changed: bool = False
    impact_paths: List[List[str]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ClaimImpact:
        return cls(
            direct_subject_changed=bool(data.get("direct_subject_changed", False)),
            dependency_path_changed=bool(data.get("dependency_path_changed", False)),
            referenced_symbol_removed=bool(data.get("referenced_symbol_removed", False)),
            signature_changed=bool(data.get("signature_changed", False)),
            import_path_changed=bool(data.get("import_path_changed", False)),
            deprecation_changed=bool(data.get("deprecation_changed", False)),
            impact_paths=data.get("impact_paths", [])
        )


@dataclass
class MemoryClaim:
    claim_id: str
    raw_statement: str
    claim_type: ClaimType
    subject: str
    predicate: str
    object: str
    qualifiers: Dict[str, Any] = field(default_factory=dict)
    repository: str = ""
    file_path: str = ""
    symbol: str = ""
    evidence_refs: List[str] = field(default_factory=list)
    confidence: float = 1.0
    source_case_id: Optional[str] = None
    claim_parse_status: str = "PARSED"  # "PARSED" | "UNRESOLVED"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "raw_statement": self.raw_statement,
            "claim_type": self.claim_type.value if isinstance(self.claim_type, Enum) else str(self.claim_type),
            "subject": self.subject,
            "predicate": self.predicate,
            "object": self.object,
            "qualifiers": self.qualifiers,
            "repository": self.repository,
            "file_path": self.file_path,
            "symbol": self.symbol,
            "evidence_refs": self.evidence_refs,
            "confidence": self.confidence,
            "source_case_id": self.source_case_id,
            "claim_parse_status": self.claim_parse_status
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> MemoryClaim:
        ctype = ClaimType(data["claim_type"]) if isinstance(data["claim_type"], str) else data["claim_type"]
        return cls(
            claim_id=data["claim_id"],
            raw_statement=data["raw_statement"],
            claim_type=ctype,
            subject=data.get("subject", ""),
            predicate=data.get("predicate", ""),
            object=data.get("object", ""),
            qualifiers=data.get("qualifiers", {}),
            repository=data.get("repository", ""),
            file_path=data.get("file_path", ""),
            symbol=data.get("symbol", ""),
            evidence_refs=data.get("evidence_refs", []),
            confidence=float(data.get("confidence", 1.0)),
            source_case_id=data.get("source_case_id"),
            claim_parse_status=data.get("claim_parse_status", "PARSED")
        )


@dataclass
class GroundedClaim:
    claim: MemoryClaim
    grounding_status: GroundingStatus
    target_node_name: Optional[str] = None
    target_file_path: Optional[str] = None
    resolved_qualified_name: Optional[str] = None
    detail: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "claim": self.claim.to_dict(),
            "grounding_status": self.grounding_status.value if isinstance(self.grounding_status, Enum) else str(self.grounding_status),
            "target_node_name": self.target_node_name,
            "target_file_path": self.target_file_path,
            "resolved_qualified_name": self.resolved_qualified_name,
            "detail": self.detail
        }


@dataclass
class ClaimEvaluationResult:
    claim_id: str
    decision: str  # "VALID", "STALE", "UNCERTAIN"
    grounding_status: GroundingStatus
    validation_status: ValidationStatus
    confidence: float
    evidences: List[ClaimEvidence] = field(default_factory=list)
    reasons: List[str] = field(default_factory=list)
    impact: Optional[ClaimImpact] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "decision": self.decision,
            "grounding_status": self.grounding_status.value if isinstance(self.grounding_status, Enum) else str(self.grounding_status),
            "validation_status": self.validation_status.value if isinstance(self.validation_status, Enum) else str(self.validation_status),
            "confidence": self.confidence,
            "evidences": [e.to_dict() for e in self.evidences],
            "reasons": self.reasons,
            "impact": self.impact.to_dict() if self.impact else None
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ClaimEvaluationResult:
        gstatus = GroundingStatus(data["grounding_status"]) if isinstance(data["grounding_status"], str) else data["grounding_status"]
        vstatus = ValidationStatus(data["validation_status"]) if isinstance(data["validation_status"], str) else data["validation_status"]
        evs = [ClaimEvidence.from_dict(e) for e in data.get("evidences", [])]
        impact = ClaimImpact.from_dict(data["impact"]) if data.get("impact") else None
        return cls(
            claim_id=data["claim_id"],
            decision=data["decision"],
            grounding_status=gstatus,
            validation_status=vstatus,
            confidence=float(data.get("confidence", 0.0)),
            evidences=evs,
            reasons=data.get("reasons", []),
            impact=impact
        )
