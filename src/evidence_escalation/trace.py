"""
src/evidence_escalation/trace.py

Escalation Trace Logging for Protocol V2.2-V1 Evidence Escalation:
- Records detailed step-by-step trace of action dispatch, targets, outcomes, costs, and decisions.
- Exports traces to data/evidence_escalation_v1/traces/{claim_id}.json.
"""

from __future__ import annotations
import os
import json
from typing import Dict, Any, List, Optional
from .types import (
    EvidenceActionType,
    BindingStrength,
    EscalationTraceStep,
    EscalationTrace,
    AcquiredEvidence
)


class EscalationTracer:
    """Manages escalation traces for claims undergoing evidence acquisition."""

    @staticmethod
    def start_trace(claim_id: str, static_decision: str) -> EscalationTrace:
        return EscalationTrace(
            claim_id=claim_id,
            static_decision=static_decision,
            steps=[],
            final_decision=static_decision,
            total_actions=0,
            total_cost={},
            stop_reason="IN_PROGRESS",
            acquired_evidences=[]
        )

    @staticmethod
    def record_step(
        trace: EscalationTrace,
        action_type: EvidenceActionType,
        target: str,
        outcome: str,
        evidence_id: Optional[str] = None,
        binding_strength: Optional[BindingStrength] = None,
        cost_increment: Optional[Dict[str, Any]] = None,
        detail: str = ""
    ) -> EscalationTraceStep:
        step = EscalationTraceStep(
            step_number=len(trace.steps) + 1,
            action_type=action_type,
            target=target,
            outcome=outcome,
            evidence_id=evidence_id,
            binding_strength=binding_strength,
            cost_increment=cost_increment or {},
            detail=detail
        )
        trace.steps.append(step)
        trace.total_actions += 1
        return step

    @staticmethod
    def finish_trace(
        trace: EscalationTrace,
        final_decision: str,
        total_cost: Dict[str, Any],
        stop_reason: str,
        acquired_evidences: Optional[List[Dict[str, Any]]] = None
    ) -> EscalationTrace:
        trace.final_decision = final_decision
        trace.total_cost = total_cost
        trace.stop_reason = stop_reason
        if acquired_evidences is not None:
            trace.acquired_evidences = acquired_evidences
        return trace

    @staticmethod
    def save_trace(trace: EscalationTrace, output_dir: str) -> str:
        os.makedirs(output_dir, exist_ok=True)
        file_path = os.path.join(output_dir, f"{trace.claim_id}.json")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(trace.to_dict(), f, indent=2)
        return file_path
