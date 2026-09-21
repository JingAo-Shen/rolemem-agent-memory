"""
src/evidence_escalation/pipeline.py

Evidence Escalation Pipeline for Protocol V2.2-V1:
- Coordinates static validation and selective escalation gate.
- Enforces core invariant: ONLY claims with static_decision == 'UNCERTAIN' enter escalation.
- Decided claims (VALID/STALE) exit immediately with 0 escalation actions and 0 cost.
- Produces full execution provenance, trace logging, and cost metrics.
"""

from __future__ import annotations
import os
from typing import Dict, Any, List, Optional, Tuple, Union

from src.claim_validity.types import (
    MemoryClaim,
    ClaimEvaluationResult
)
from src.claim_validity.engine import ClaimAwareValidityEngine
from .types import (
    EvidenceActionType,
    CostBudget,
    AcquiredEvidence,
    EvidenceAcquisitionRequest,
    EscalationTrace
)
from .cost import CostTracker
from .trace import EscalationTracer
from .planner import DeterministicEscalationPlanner


class EvidenceEscalationPipeline:
    """Unified pipeline for static validity reasoning with selective evidence escalation."""

    def __init__(self):
        self.static_engine = ClaimAwareValidityEngine()
        self.planner = DeterministicEscalationPlanner()

    def evaluate_claim(
        self,
        claim_or_statement: Union[MemoryClaim, str],
        base_source: str = "",
        target_source: str = "",
        diff_hunk: str = "",
        symbol_qualified_name: str = "",
        file_path: str = "",
        repository: str = "",
        repository_root: Optional[str] = None,
        base_commit: Optional[str] = None,
        target_commit: Optional[str] = None,
        available_budget: Optional[CostBudget] = None,
        trace_dir: Optional[str] = None
    ) -> Tuple[ClaimEvaluationResult, EscalationTrace, CostTracker]:
        """
        Evaluates a claim: runs static validation first, and escalates only if static decision is UNCERTAIN.
        """
        # 1. Static Validation
        static_result = self.static_engine.evaluate(
            claim_or_statement=claim_or_statement,
            base_source=base_source,
            target_source=target_source,
            diff_hunk=diff_hunk,
            symbol_qualified_name=symbol_qualified_name,
            file_path=file_path,
            repository=repository,
            repository_root=repository_root,
            base_commit=base_commit,
            target_commit=target_commit
        )

        cid = static_result.claim_id
        budget = available_budget or CostBudget()
        cost_tracker = CostTracker()
        trace = EscalationTracer.start_trace(cid, static_result.decision)

        # 2. Selective Escalation Gate
        if static_result.decision in ("VALID", "STALE"):
            # Decided cases bypass escalation entirely
            EscalationTracer.finish_trace(
                trace=trace,
                final_decision=static_result.decision,
                total_cost=cost_tracker.to_dict(),
                stop_reason="STATIC_DECIDED_NO_ESCALATION",
                acquired_evidences=[]
            )
            if trace_dir:
                EscalationTracer.save_trace(trace, trace_dir)
            return static_result, trace, cost_tracker

        # 3. Escalation for UNCERTAIN claims
        claim: MemoryClaim
        if isinstance(claim_or_statement, MemoryClaim):
            claim = claim_or_statement
        else:
            claim = self.static_engine.extractor.extract(
                raw_statement=claim_or_statement,
                repository=repository,
                file_path=file_path,
                symbol=symbol_qualified_name
            )

        if not repository_root and repository:
            repo_clean = repository.split("/")[-1]
            cand = os.path.join("/code/repo_cache", repo_clean)
            if os.path.isdir(cand):
                repository_root = cand

        request = EvidenceAcquisitionRequest(
            claim=claim,
            repository_root=repository_root or "",
            static_result=static_result,
            available_budget=budget,
            base_commit=base_commit or "",
            target_commit=target_commit or ""
        )

        final_result, acquired_evidences = self.planner.execute_plan(
            request=request,
            cost_tracker=cost_tracker,
            trace=trace
        )

        # Determine stop reason
        if final_result.decision != "UNCERTAIN":
            stop_reason = f"RESOLVED_TO_{final_result.decision}"
        else:
            stop_reason = "REMAINED_UNCERTAIN_AFTER_ESCALATION"

        EscalationTracer.finish_trace(
            trace=trace,
            final_decision=final_result.decision,
            total_cost=cost_tracker.to_dict(),
            stop_reason=stop_reason,
            acquired_evidences=[e.to_dict() for e in acquired_evidences]
        )

        if trace_dir:
            EscalationTracer.save_trace(trace, trace_dir)

        return final_result, trace, cost_tracker
