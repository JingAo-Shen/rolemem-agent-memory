"""
RoleMem v1 Core Schema: Formal Data Models for Evidence-Scoped Memory and Benchmarks.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
import hashlib
import json


@dataclass
class MemoryRecordV1:
    """Formal structured memory record with artifact hash binding and causal invalidation."""
    memory_id: str
    artifact_uri: str
    artifact_type: str  # 'file', 'symbol', 'config', 'schema', 'doc'
    symbol: Optional[str]
    source_commit: Optional[str]
    observed_at: float
    evidence_type: str  # 'test_run', 'execution_output', 'diff_analysis', 'user_spec'
    evidence_ref: str
    valid_from: float
    valid_to: float = float('inf')
    supersedes: Optional[str] = None
    depends_on: List[str] = field(default_factory=list)
    status: str = "ACTIVE"  # 'ACTIVE', 'SUPERSEDED', 'INVALIDATED_BY_ARTIFACT', 'DISPUTED'
    role_tags: List[str] = field(default_factory=lambda: ["coder", "reviewer"])
    statement: str = ""
    artifact_digest: Optional[str] = None
    symbol_qualified_name: Optional[str] = None
    symbol_digest: Optional[str] = None
    validity_granularity: str = "file"  # 'file' | 'symbol'

    def compute_hash(self, content: str) -> str:
        """Compute standard SHA-256 digest of file content."""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    def is_artifact_valid(self, workspace_files: Dict[str, str]) -> bool:
        """
        Verify artifact validity against current workspace files.
        File-level invalidation: If artifact_uri exists in workspace, compute its real SHA-256.
        If hash differs from recorded artifact_digest, this memory is invalidated.
        """
        if not self.artifact_digest or not self.artifact_uri:
            return True
        
        current_content = workspace_files.get(self.artifact_uri)
        if current_content is None:
            # Artifact was deleted/renamed
            return False
        
        current_digest = hashlib.sha256(current_content.encode('utf-8')).hexdigest()
        return current_digest == self.artifact_digest

    def is_symbol_valid(self, workspace_files: Dict[str, str]) -> bool:
        """
        Verify symbol-level validity against current workspace files.
        Symbol-level invalidation: Check if symbol_qualified_name exists with matching symbol_digest.
        """
        if not self.artifact_uri:
            return True
        if not self.artifact_digest and not self.symbol_digest:
            return True
        current_content = workspace_files.get(self.artifact_uri)
        if current_content is None:
            return False
        if not self.symbol_qualified_name or not self.symbol_digest:
            return self.is_artifact_valid(workspace_files)

        from src.symbol_validity import SymbolDigestExtractor
        digests = SymbolDigestExtractor.extract_symbol_digests(current_content)
        qname = self.symbol_qualified_name
        short_name = qname.split(".")[-1]
        target_info = digests.get(qname) or digests.get(short_name)
        if not target_info:
            return False
        return target_info["symbol_digest"] == self.symbol_digest

    def to_dict(self) -> Dict[str, Any]:
        return {
            "memory_id": self.memory_id,
            "artifact_uri": self.artifact_uri,
            "artifact_type": self.artifact_type,
            "symbol": self.symbol,
            "symbol_qualified_name": self.symbol_qualified_name,
            "symbol_digest": self.symbol_digest,
            "validity_granularity": self.validity_granularity,
            "source_commit": self.source_commit,
            "observed_at": self.observed_at,
            "evidence_type": self.evidence_type,
            "evidence_ref": self.evidence_ref,
            "valid_from": self.valid_from,
            "valid_to": self.valid_to if self.valid_to != float('inf') else "inf",
            "supersedes": self.supersedes,
            "depends_on": self.depends_on,
            "status": self.status,
            "role_tags": self.role_tags,
            "statement": self.statement,
            "artifact_digest": self.artifact_digest,
        }


@dataclass
class TaskEnvironmentV1:
    """Independent task fixture for dynamic multi-agent handoffs."""
    task_id: str
    task_family: str
    category: str  # 'no_update', 'explicit_update', 'stale_evidence', 'unresolved_conflict'
    title: str
    description: str
    initial_workspace: Dict[str, str]
    historical_memories: List[MemoryRecordV1]
    workspace_transition: Dict[str, str]
    current_task_instruction: str
    target_file: str
    target_symbol: str
    hidden_test_code: str
    stale_patterns: List[str] = field(default_factory=list)
    required_patterns: List[str] = field(default_factory=list)

    def get_current_workspace(self) -> Dict[str, str]:
        """Apply workspace transition over initial workspace to get current real state."""
        ws = dict(self.initial_workspace)
        ws.update(self.workspace_transition)
        return ws
