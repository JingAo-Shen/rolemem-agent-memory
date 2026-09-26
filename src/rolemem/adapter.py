"""
src/rolemem/adapter.py

RoleMem Evaluation Adapter and Agent Integration Layer:
Interfaces benchmark cases (formal_inputs.jsonl) with the RoleMem Lifecycle Engine
and provides high-level memory querying and context-formatting interfaces for autonomous agents.
"""

from __future__ import annotations
from typing import Dict, Any, List, Optional, Union
import json
import os
import time

from .schema import (
    RoleMemoryRecord,
    ClaimPayload,
    EvidencePayload,
    TemporalAnchor,
    RoleEnum,
    MemoryStatus
)
from .store import RoleMemStore
from .retriever import RoleAwareRetriever
from .lifecycle import RoleMemLifecycleEngine, LifecycleUpdateResult
from src.evidence_escalation.types import CostBudget


class RoleMemEvaluationAdapter:
    """
    Evaluation adapter linking formal benchmark inputs (formal_inputs.jsonl)
    to the RoleMem reasoning and lifecycle engine.
    """

    def __init__(
        self,
        case_map_path: Optional[str] = None,
        lifecycle_engine: Optional[RoleMemLifecycleEngine] = None
    ):
        self.lifecycle_engine = lifecycle_engine or RoleMemLifecycleEngine()
        self.case_map: Dict[str, Dict[str, Any]] = {}
        if case_map_path and os.path.exists(case_map_path):
            with open(case_map_path, "r", encoding="utf-8") as f:
                self.case_map = json.load(f)

    def load_case_map(self, case_map_path: str) -> None:
        """Load private or formal case metadata map."""
        if os.path.exists(case_map_path):
            with open(case_map_path, "r", encoding="utf-8") as f:
                self.case_map = json.load(f)

    def evaluate_case(
        self,
        case_input: Dict[str, Any],
        target_commit_override: Optional[str] = None,
        base_commit_override: Optional[str] = None,
        evidence_path_override: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Evaluate a single benchmark input case and return formal prediction record.
        """
        start_time = time.time()
        case_id = case_input.get("case_id", "UNKNOWN")
        structured_claim = case_input.get("structured_claim", {})
        raw_statement = case_input.get("raw_statement", "")
        claim_type = case_input.get("claim_type", "SYMBOL_EXISTS")
        repo_name = case_input.get("repository_name", "")

        # Look up case metadata from case_map if present
        meta = self.case_map.get(case_id, {})
        base_commit = base_commit_override or meta.get("base_commit", "")
        target_commit = target_commit_override or meta.get("target_commit", "")
        evidence_path = evidence_path_override or meta.get("base_evidence_path", "")
        evidence_snippet = meta.get("base_evidence_snippet", "")

        # Infer role
        role = RoleEnum.from_claim_type(claim_type)

        # Build ephemeral RoleMemoryRecord
        record = RoleMemoryRecord(
            memory_id=case_id,
            claim=ClaimPayload(
                structured_claim=structured_claim,
                raw_statement=raw_statement,
                claim_type=claim_type,
                repository_name=repo_name
            ),
            evidence=EvidencePayload(
                evidence_path=evidence_path,
                evidence_lineno=1,
                evidence_snippet=evidence_snippet,
                extraction_channel="AST_ANALYSIS"
            ),
            role=role,
            confidence=1.0,
            timestamp=TemporalAnchor(commit_sha=base_commit)
        )

        # Run lifecycle evaluation
        result = self.lifecycle_engine.evaluate_record(
            record=record,
            target_commit=target_commit,
            base_commit=base_commit
        )

        wall_time = time.time() - start_time

        # Map decision to formal prediction schema
        predicted_label = result.decision
        if predicted_label == "UNCERTAIN":
            # In fail-safe evaluation, uncertain cases are flagged or treated conservatively
            predicted_label = "UNCERTAIN"

        return {
            "case_id": case_id,
            "predicted_label": predicted_label,
            "confidence": result.new_confidence if predicted_label != "STALE" else 0.0,
            "escalation_tier": result.escalation_tier,
            "action_count": result.action_count,
            "execution_wall_time_sec": round(wall_time, 4)
        }

    def run_benchmark(
        self,
        inputs_file: str,
        output_predictions_file: str,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Run batch evaluation across formal inputs and output predictions JSONL.
        """
        predictions: List[Dict[str, Any]] = []
        with open(inputs_file, "r", encoding="utf-8") as f:
            for idx, line in enumerate(f):
                line = line.strip()
                if not line:
                    continue
                if limit and idx >= limit:
                    break
                case_data = json.loads(line)
                pred = self.evaluate_case(case_data)
                predictions.append(pred)

        os.makedirs(os.path.dirname(os.path.abspath(output_predictions_file)), exist_ok=True)
        with open(output_predictions_file, "w", encoding="utf-8") as f:
            for p in predictions:
                f.write(json.dumps(p) + "\n")

        return predictions


class RoleMemAgentInterface:
    """
    High-level programmatic agent interface for integrating RoleMem
    into autonomous coding agents and interactive reasoning loops.
    """

    def __init__(self, store: Optional[RoleMemStore] = None):
        self.store = store or RoleMemStore()
        self.retriever = RoleAwareRetriever(self.store)
        self.lifecycle_engine = RoleMemLifecycleEngine()

    def add_memory(
        self,
        memory_id: str,
        structured_claim: Dict[str, Any],
        raw_statement: str,
        claim_type: str,
        evidence_path: str,
        evidence_snippet: str = "",
        repository_name: str = "",
        commit_sha: str = "",
        confidence: float = 1.0
    ) -> RoleMemoryRecord:
        """Register a newly observed memory into the agent store."""
        role = RoleEnum.from_claim_type(claim_type)
        record = RoleMemoryRecord(
            memory_id=memory_id,
            claim=ClaimPayload(
                structured_claim=structured_claim,
                raw_statement=raw_statement,
                claim_type=claim_type,
                repository_name=repository_name
            ),
            evidence=EvidencePayload(
                evidence_path=evidence_path,
                evidence_snippet=evidence_snippet
            ),
            role=role,
            confidence=confidence,
            timestamp=TemporalAnchor(commit_sha=commit_sha)
        )
        self.store.add_record(record)
        return record

    def query_memories(
        self,
        query: str,
        target_role: Optional[RoleEnum] = None,
        repository: Optional[str] = None,
        top_k: int = 5
    ) -> List[RoleMemoryRecord]:
        """Query relevant active memories using role-aware hybrid retrieval."""
        results = self.retriever.retrieve(
            query=query,
            target_role=target_role,
            repository=repository,
            top_k=top_k,
            active_only=True
        )
        return [rec for rec, _ in results]

    def format_context_prompt(self, query: str, target_role: Optional[RoleEnum] = None, top_k: int = 3) -> str:
        """Format retrieved memories into a structured context prompt section for LLMs."""
        memories = self.query_memories(query, target_role=target_role, top_k=top_k)
        if not memories:
            return ""

        lines = ["### [RoleMem Verified Codebase Knowledge]"]
        for idx, m in enumerate(memories, 1):
            lines.append(f"{idx}. [{m.role.value}] {m.claim.raw_statement} (Confidence: {m.confidence:.2f})")
            if m.evidence.evidence_path:
                lines.append(f"   Provenance: `{m.evidence.evidence_path}`")
        return "\n".join(lines)

    def synchronize_repository_state(self, target_commit: str, repository_name: str) -> List[LifecycleUpdateResult]:
        """
        Trigger proactive lifecycle updates on all active memories for a repository upon commit change.
        """
        active_records = self.store.filter_by_repository(repository_name, active_only=True)
        results = []
        for rec in active_records:
            res = self.lifecycle_engine.evaluate_record(rec, target_commit=target_commit)
            results.append(res)
        return results
