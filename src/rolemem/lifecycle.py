"""
src/rolemem/lifecycle.py

RoleMem Dynamic Memory Lifecycle Engine:
Evaluates active memory records against evolving repository target states S_target,
executes budget-bounded evidence escalation (Tiers 0-3), and applies formal state transitions:
  - PRESERVE (VALID) -> Boost confidence, advance temporal anchor
  - DOWNGRADE (PARTIALLY_VALID) -> Decay confidence, attach advisory
  - INVALIDATE (STALE) -> Invalidate status, purge from active working set
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple, Union
import os
import subprocess
import time

from .schema import RoleMemoryRecord, RoleEnum, MemoryStatus, TemporalAnchor
from src.claim_validity.types import MemoryClaim, ClaimType, ClaimEvaluationResult
from src.evidence_escalation.pipeline import EvidenceEscalationPipeline
from src.evidence_escalation.types import CostBudget, PipelineConfig


@dataclass
class LifecycleUpdateResult:
    """Result summary of a lifecycle evaluation and transition."""
    memory_id: str
    decision: str  # VALID, STALE, PARTIALLY_VALID, UNCERTAIN
    previous_status: MemoryStatus
    new_status: MemoryStatus
    previous_confidence: float
    new_confidence: float
    escalation_tier: str
    action_count: int
    execution_wall_time_sec: float
    reasons: List[str] = field(default_factory=list)
    raw_result: Optional[Dict[str, Any]] = None


class RoleMemLifecycleEngine:
    """
    Dynamic Lifecycle State Transition Engine for RoleMem.
    Interfaces memory units with the evidence escalation ladder under strict budget bounds.
    """

    def __init__(
        self,
        confidence_boost: float = 0.05,
        confidence_decay: float = 0.80,
        uncertain_decay: float = 0.90,
        default_budget: Optional[CostBudget] = None
    ):
        self.confidence_boost = confidence_boost
        self.confidence_decay = confidence_decay
        self.uncertain_decay = uncertain_decay
        self.default_budget = default_budget or CostBudget(max_total_actions=50)
        self.pipeline = EvidenceEscalationPipeline()

    def _resolve_repo_root(self, repository_name: str) -> Optional[str]:
        """Resolve local path for bare cache or worktree of repository."""
        if not repository_name:
            return None
        repo_clean = repository_name.replace("/", "_")
        # Check formal bare repo directory
        bare_cand = os.path.join("/tmp/formal_bare_repos", repo_clean)
        if os.path.isdir(bare_cand):
            return bare_cand
        # Check standard cache
        repo_simple = repository_name.split("/")[-1]
        cache_cand = os.path.join("/code/repo_cache", repo_simple)
        if os.path.isdir(cache_cand):
            return cache_cand
        return None

    def _extract_git_file_source(self, repo_root: str, commit_sha: str, file_path: str) -> str:
        """Extract source content of a file at a specific commit from git."""
        if not repo_root or not commit_sha or not file_path:
            return ""
        try:
            res = subprocess.run(
                ["git", "show", f"{commit_sha}:{file_path}"],
                cwd=repo_root,
                capture_output=True,
                text=True,
                timeout=5
            )
            if res.returncode == 0:
                return res.stdout
        except Exception:
            pass
        return ""

    def evaluate_record(
        self,
        record: RoleMemoryRecord,
        target_commit: str = "",
        repository_root: Optional[str] = None,
        base_commit: Optional[str] = None,
        target_timestamp: str = "",
        target_ref: str = "",
        budget: Optional[CostBudget] = None
    ) -> LifecycleUpdateResult:
        """
        Evaluate single memory record against target codebase state and apply state update.
        """
        start_time = time.time()
        prev_status = record.status
        prev_conf = record.confidence

        repo_name = record.claim.repository_name
        repo_root = repository_root or self._resolve_repo_root(repo_name)
        b_commit = base_commit or record.timestamp.commit_sha
        t_commit = target_commit

        file_path = record.evidence.evidence_path
        structured = record.claim.structured_claim
        subject = structured.get("symbol") or structured.get("module", "")

        # Extract file source at base and target commits if possible
        base_source = self._extract_git_file_source(repo_root, b_commit, file_path) if repo_root else ""
        target_source = self._extract_git_file_source(repo_root, t_commit, file_path) if repo_root else ""

        # Map claim type
        raw_ctype = record.claim.claim_type or "SYMBOL_EXISTS"
        try:
            ctype = ClaimType(raw_ctype)
        except Exception:
            ctype = ClaimType.SYMBOL_EXISTS

        # Construct MemoryClaim
        mem_claim = MemoryClaim(
            claim_id=record.memory_id,
            raw_statement=record.claim.raw_statement,
            claim_type=ctype,
            subject=subject,
            predicate=record.claim.claim_type,
            object=str(structured.get("expected_default") or structured.get("contract_specification") or ""),
            qualifiers=structured,
            repository=repo_name,
            file_path=file_path,
            symbol=subject,
            evidence_refs=[record.evidence.evidence_path] if record.evidence.evidence_path else [],
            confidence=record.confidence,
            source_case_id=record.memory_id,
            claim_parse_status="PARSED"
        )

        cost_budget = budget or self.default_budget

        # Execute escalation pipeline
        eval_result, trace, cost_tracker = self.pipeline.evaluate_claim(
            claim_or_statement=mem_claim,
            base_source=base_source,
            target_source=target_source,
            symbol_qualified_name=subject,
            file_path=file_path,
            repository=repo_name,
            repository_root=repo_root,
            base_commit=b_commit,
            target_commit=t_commit,
            available_budget=cost_budget
        )

        decision = eval_result.decision
        action_count = sum(cost_tracker.action_counts.values()) if hasattr(cost_tracker, "action_counts") else 0
        wall_time = time.time() - start_time

        # Determine escalation tier
        if action_count == 0:
            tier = "TIER_0_STATIC_AST"
        elif action_count <= 5:
            tier = "TIER_1_FILE_SEARCH"
        elif action_count <= 10:
            tier = "TIER_2_MANIFEST_PARSING"
        else:
            tier = "TIER_3_TEST_EXECUTION"

        # Apply state transition dynamics
        new_status = prev_status
        new_conf = prev_conf
        transition_note = ""

        if decision == "VALID":
            new_status = MemoryStatus.PRESERVED
            new_conf = min(1.0, round(prev_conf + self.confidence_boost, 4))
            record.status = new_status
            record.confidence = new_conf
            if target_commit:
                record.timestamp = TemporalAnchor(
                    commit_sha=target_commit,
                    timestamp_iso8601=target_timestamp or record.timestamp.timestamp_iso8601,
                    release_ref=target_ref or record.timestamp.release_ref
                )
            transition_note = f"Preserved at commit {target_commit[:8]} (confidence: {prev_conf} -> {new_conf})"

        elif decision == "PARTIALLY_VALID":
            new_status = MemoryStatus.DOWNGRADED
            new_conf = max(0.1, round(prev_conf * self.confidence_decay, 4))
            record.status = new_status
            record.confidence = new_conf
            transition_note = f"Downgraded at commit {target_commit[:8]} (confidence: {prev_conf} -> {new_conf}). Non-breaking migration detected."
            record.advisory_notes.append(transition_note)

        elif decision == "STALE":
            new_status = MemoryStatus.INVALIDATED
            new_conf = 0.0
            record.status = new_status
            record.confidence = new_conf
            transition_note = f"Invalidated at commit {target_commit[:8]}. Breaking modification detected: {eval_result.reasons}"
            record.advisory_notes.append(transition_note)

        else:  # UNCERTAIN
            new_conf = max(0.2, round(prev_conf * self.uncertain_decay, 4))
            record.confidence = new_conf
            transition_note = f"Uncertain at commit {target_commit[:8]} (confidence: {prev_conf} -> {new_conf}). Insufficient evidence."
            record.advisory_notes.append(transition_note)

        # Audit action history
        record.action_history.append({
            "action": "LIFECYCLE_EVALUATION",
            "target_commit": target_commit,
            "decision": decision,
            "tier": tier,
            "action_count": action_count,
            "note": transition_note,
            "timestamp": time.time()
        })

        return LifecycleUpdateResult(
            memory_id=record.memory_id,
            decision=decision,
            previous_status=prev_status,
            new_status=new_status,
            previous_confidence=prev_conf,
            new_confidence=new_conf,
            escalation_tier=tier,
            action_count=action_count,
            execution_wall_time_sec=round(wall_time, 4),
            reasons=eval_result.reasons,
            raw_result=eval_result.to_dict() if hasattr(eval_result, "to_dict") else {}
        )

    def batch_evaluate(
        self,
        records: List[RoleMemoryRecord],
        target_commit: str = "",
        repository_root: Optional[str] = None,
        base_commit: Optional[str] = None
    ) -> List[LifecycleUpdateResult]:
        """Evaluate a batch of memory records sequentially."""
        return [
            self.evaluate_record(
                record=r,
                target_commit=target_commit,
                repository_root=repository_root,
                base_commit=base_commit
            )
            for r in records
        ]
