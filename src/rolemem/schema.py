"""
src/rolemem/schema.py

RoleMem Core Memory Schema:
Implements the formal 6-tuple memory representation M = <c, E, R, gamma, tau, Phi>
and epistemic role taxonomy according to the frozen RoleMem Architecture specification.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, List, Optional, Union
import hashlib
import json


class RoleEnum(str, Enum):
    """Epistemic memory roles governing validity invariants and verification channels."""
    API = "API"
    BEHAVIOR = "BEHAVIOR"
    DEPENDENCY = "DEPENDENCY"
    CONFIG = "CONFIG"

    @classmethod
    def from_claim_type(cls, claim_type: str) -> "RoleEnum":
        """Map canonical claim type to epistemic memory role."""
        ctype = str(claim_type).upper().strip()
        if ctype in ("SYMBOL_EXISTS", "CALLABLE", "SIGNATURE_COMPATIBLE", "IMPORT_PATH_VALID", "ATTRIBUTE_EXISTS", "DEPRECATION_STATUS"):
            return cls.API
        elif ctype in ("BEHAVIORAL_CONTRACT", "RETURN_VALUE", "RETURN_VALUE_ASSERTION", "EXCEPTION_HANDLING_CONTRACT"):
            return cls.BEHAVIOR
        elif ctype in ("DEPENDENCY_CONTRACT", "VERSION_CONSTRAINT", "PACKAGE_DEPENDENCY"):
            return cls.DEPENDENCY
        elif ctype in ("DEFAULT_VALUE", "CONFIG_FLAG", "SETTING_KEY"):
            return cls.CONFIG
        else:
            return cls.API


class MemoryStatus(str, Enum):
    """Lifecycle status states of a memory record."""
    ACTIVE = "ACTIVE"
    PRESERVED = "PRESERVED"
    DOWNGRADED = "DOWNGRADED"
    INVALIDATED = "INVALIDATED"


class DeprecationStatus(str, Enum):
    """Canonical deprecation status representing symbol lifecycle state."""
    ACTIVE = "active"
    DEPRECATED = "deprecated"

    @classmethod
    def from_value(cls, val: Any) -> "DeprecationStatus":
        """
        Normalize boolean, string, or object representations into canonical DeprecationStatus enum.
        Eliminates boolean vs string/object discrepancies.
        """
        if isinstance(val, cls):
            return val
        if isinstance(val, bool):
            return cls.DEPRECATED if val else cls.ACTIVE
        if isinstance(val, str):
            clean = val.strip().lower()
            if clean in ("deprecated", "true", "1", "raising deprecationwarning", "soft_deprecated"):
                return cls.DEPRECATED
            return cls.ACTIVE
        if isinstance(val, dict):
            if val.get("is_deprecated") is True or val.get("status") == "deprecated":
                return cls.DEPRECATED
            return cls.ACTIVE
        return cls.ACTIVE



@dataclass
class ClaimPayload:
    """Factual proposition asserted by the agent (structured slots + natural language statement)."""
    structured_claim: Dict[str, Any] = field(default_factory=dict)
    raw_statement: str = ""
    claim_type: str = ""
    repository_name: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "structured_claim": self.structured_claim,
            "raw_statement": self.raw_statement,
            "claim_type": self.claim_type,
            "repository_name": self.repository_name,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ClaimPayload":
        return cls(
            structured_claim=data.get("structured_claim", {}),
            raw_statement=data.get("raw_statement", ""),
            claim_type=data.get("claim_type", ""),
            repository_name=data.get("repository_name", "")
        )


@dataclass
class EvidencePayload:
    """Grounding provenance linking the claim to physical source artifacts at snapshot time."""
    evidence_path: str = ""
    evidence_lineno: int = 1
    evidence_snippet: str = ""
    extraction_channel: str = "AST_ANALYSIS"  # AST_ANALYSIS, DOCUMENTATION_PARSING, PACKAGE_METADATA_PARSING, TEST_ASSERTION_EXTRACTION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "evidence_path": self.evidence_path,
            "evidence_lineno": self.evidence_lineno,
            "evidence_snippet": self.evidence_snippet,
            "extraction_channel": self.extraction_channel,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EvidencePayload":
        return cls(
            evidence_path=data.get("evidence_path", ""),
            evidence_lineno=int(data.get("evidence_lineno", 1)),
            evidence_snippet=data.get("evidence_snippet", ""),
            extraction_channel=data.get("extraction_channel", "AST_ANALYSIS")
        )


@dataclass
class TemporalAnchor:
    """Explicit version and timestamp anchoring for temporal consistency."""
    commit_sha: str = ""
    timestamp_iso8601: str = ""
    release_ref: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "commit_sha": self.commit_sha,
            "timestamp_iso8601": self.timestamp_iso8601,
            "release_ref": self.release_ref,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TemporalAnchor":
        return cls(
            commit_sha=data.get("commit_sha", ""),
            timestamp_iso8601=data.get("timestamp_iso8601", ""),
            release_ref=data.get("release_ref", "")
        )


@dataclass
class RoleMemoryRecord:
    """
    Formal 6-tuple Role Memory unit:
        M = <c, E, R, gamma, tau, Phi>
    """
    memory_id: str
    claim: ClaimPayload
    evidence: EvidencePayload
    role: RoleEnum
    confidence: float = 1.0
    timestamp: TemporalAnchor = field(default_factory=TemporalAnchor)
    fingerprint: str = ""
    status: MemoryStatus = MemoryStatus.ACTIVE
    advisory_notes: List[str] = field(default_factory=list)
    action_history: List[Dict[str, Any]] = field(default_factory=list)

    def __post_init__(self):
        if not self.fingerprint:
            self.fingerprint = self.compute_fingerprint()
        if isinstance(self.role, str):
            self.role = RoleEnum(self.role)
        if isinstance(self.status, str):
            self.status = MemoryStatus(self.status)

    def compute_fingerprint(self) -> str:
        """
        Deterministic SHA-256 fingerprint hash:
            Phi = SHA256(c || E || R || tau)
        """
        canonical_dict = {
            "claim": self.claim.to_dict() if isinstance(self.claim, ClaimPayload) else self.claim,
            "evidence": self.evidence.to_dict() if isinstance(self.evidence, EvidencePayload) else self.evidence,
            "role": self.role.value if isinstance(self.role, RoleEnum) else str(self.role),
            "timestamp": self.timestamp.to_dict() if isinstance(self.timestamp, TemporalAnchor) else self.timestamp,
        }
        canonical_str = json.dumps(canonical_dict, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()

    def verify_integrity(self) -> bool:
        """Verify whether recorded cryptographic fingerprint matches current payload."""
        return self.fingerprint == self.compute_fingerprint()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "memory_id": self.memory_id,
            "claim": self.claim.to_dict(),
            "evidence": self.evidence.to_dict(),
            "role": self.role.value,
            "confidence": round(float(self.confidence), 4),
            "timestamp": self.timestamp.to_dict(),
            "fingerprint": self.fingerprint,
            "status": self.status.value,
            "advisory_notes": list(self.advisory_notes),
            "action_history": list(self.action_history)
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RoleMemoryRecord":
        return cls(
            memory_id=data["memory_id"],
            claim=ClaimPayload.from_dict(data.get("claim", {})),
            evidence=EvidencePayload.from_dict(data.get("evidence", {})),
            role=RoleEnum(data.get("role", "API")),
            confidence=float(data.get("confidence", 1.0)),
            timestamp=TemporalAnchor.from_dict(data.get("timestamp", {})),
            fingerprint=data.get("fingerprint", ""),
            status=MemoryStatus(data.get("status", "ACTIVE")),
            advisory_notes=list(data.get("advisory_notes", [])),
            action_history=list(data.get("action_history", []))
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True)

    @classmethod
    def from_json(cls, json_str: str) -> "RoleMemoryRecord":
        return cls.from_dict(json.loads(json_str))
