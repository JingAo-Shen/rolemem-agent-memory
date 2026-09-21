"""
src/evidence_escalation/planner.py

Deterministic Escalation Planner for Protocol V2.2-V1 Evidence Escalation:
- Coordinates action dispatch based strictly on claim taxonomy, grounding status, and structural heuristics.
- Implements budget checks, early stopping upon conclusive evidence, and full trace recording.
- Operates 100% deterministically without category or case ID conditioning.
"""

from __future__ import annotations
import os
from typing import Dict, Any, List, Optional, Tuple

from src.claim_validity.types import (
    ClaimType,
    GroundingStatus,
    MemoryClaim,
    ClaimEvaluationResult
)
from .types import (
    EvidenceActionType,
    BindingStrength,
    AcquiredEvidence,
    TestCandidate,
    EvidenceAcquisitionRequest,
    EscalationTrace
)
from .cost import CostTracker
from .trace import EscalationTracer
from .repository_search import RepositorySearchEngine
from .test_discovery import NativeTestDiscoveryEngine
from .test_binding import ClaimTestBinder
from .executor import TargetedWorktreeExecutor
from .binding import EscalatedEvidenceAggregator


class DeterministicEscalationPlanner:
    """Plans and executes deterministic evidence acquisition workflows for uncertain claims."""

    def __init__(self):
        self.search_engine = RepositorySearchEngine()
        self.discovery_engine = NativeTestDiscoveryEngine()
        self.test_binder = ClaimTestBinder()
        self.executor = TargetedWorktreeExecutor()
        self.aggregator = EscalatedEvidenceAggregator()

    def execute_plan(
        self,
        request: EvidenceAcquisitionRequest,
        cost_tracker: Optional[CostTracker] = None,
        trace: Optional[EscalationTrace] = None
    ) -> Tuple[ClaimEvaluationResult, List[AcquiredEvidence]]:
        """
        Executes escalation plan for a single uncertain claim.
        Returns synthesized ClaimEvaluationResult and list of AcquiredEvidence.
        """
        claim = request.claim
        cid = claim.claim_id
        static_result = request.static_result
        budget = request.available_budget
        tracker = cost_tracker or CostTracker()

        repo_root = request.repository_root
        if not repo_root and claim.repository:
            cand = os.path.join("/code/repo_cache", claim.repository.split("/")[-1])
            if os.path.isdir(cand):
                repo_root = cand

        repo_name = claim.repository or (os.path.basename(repo_root) if repo_root else "")
        target_commit = request.target_commit
        base_commit = request.base_commit

        acquired_evidences: List[AcquiredEvidence] = []

        # If repo_root or target_commit is missing, cannot escalate
        if not repo_root or not target_commit:
            if trace:
                EscalationTracer.record_step(
                    trace,
                    EvidenceActionType.REPOSITORY_SEARCH,
                    target="repository_root",
                    outcome="UNAVAILABLE",
                    detail="Repository root or target commit missing; cannot escalate."
                )
            return static_result, acquired_evidences

        # -------------------------------------------------------------
        # Branch 1: BEHAVIORAL_CONTRACT
        # -------------------------------------------------------------
        if claim.claim_type == ClaimType.BEHAVIORAL_CONTRACT:
            # Step 1: Discover native tests
            op_tokens = self.test_binder.extract_operation_tokens(claim)
            candidates = self.discovery_engine.discover_tests_for_claim(
                repo_root=repo_root,
                repository_name=repo_name,
                target_commit=target_commit,
                subject=claim.subject,
                object_tokens=op_tokens,
                cost_tracker=tracker,
                budget=budget
            )

            # Step 2: Bind candidates
            ranked_candidates = self.test_binder.bind_and_rank_candidates(
                claim=claim,
                candidates=candidates
            )

            strong_candidates = [c for c in ranked_candidates if c.binding_strength == BindingStrength.STRONG]

            if trace:
                EscalationTracer.record_step(
                    trace,
                    EvidenceActionType.TEST_DISCOVERY,
                    target=f"{claim.subject} op_tokens={op_tokens}",
                    outcome=f"Discovered {len(candidates)} candidates ({len(strong_candidates)} strong)",
                    binding_strength=strong_candidates[0].binding_strength if strong_candidates else (ranked_candidates[0].binding_strength if ranked_candidates else None),
                    detail=f"Top candidate: {ranked_candidates[0].test_file}:{ranked_candidates[0].test_name}" if ranked_candidates else "No candidates found"
                )

            # Step 3: Targeted execution of top strong candidate
            if strong_candidates:
                top_candidate = strong_candidates[0]
                exec_ev = self.executor.run_test_candidate(
                    claim_id=cid,
                    repo_root=repo_root,
                    repository_name=repo_name,
                    candidate=top_candidate,
                    cost_tracker=tracker,
                    budget=budget
                )
                acquired_evidences.append(exec_ev)

                if trace:
                    EscalationTracer.record_step(
                        trace,
                        EvidenceActionType.TARGETED_EXECUTION,
                        target=f"{top_candidate.test_file}::{top_candidate.test_name}",
                        outcome=exec_ev.supports_or_contradicts,
                        evidence_id=exec_ev.evidence_id,
                        binding_strength=exec_ev.binding_strength,
                        cost_increment=exec_ev.cost,
                        detail=exec_ev.detail
                    )

        # -------------------------------------------------------------
        # Branch 2: DEPENDENCY_CONTRACT
        # -------------------------------------------------------------
        elif claim.claim_type == ClaimType.DEPENDENCY_CONTRACT:
            dep_obj = claim.object
            # Step 1: Inspect dependency usage in AST and diff
            dep_evs = self.search_engine.search_dependency_usage(
                claim_id=cid,
                repo_root=repo_root,
                repository_name=repo_name,
                base_commit=base_commit,
                target_commit=target_commit,
                file_path=claim.file_path,
                subject_symbol=claim.subject,
                dependency_symbol=dep_obj,
                cost_tracker=tracker
            )
            acquired_evidences.extend(dep_evs)

            if trace:
                for ev in dep_evs:
                    EscalationTracer.record_step(
                        trace,
                        EvidenceActionType.DEPENDENCY_INSPECTION,
                        target=f"{claim.subject} -> {dep_obj}",
                        outcome=ev.supports_or_contradicts,
                        evidence_id=ev.evidence_id,
                        binding_strength=ev.binding_strength,
                        detail=ev.detail
                    )

            # If static dependency inspection proved contradiction or support, early stop
            has_strong = any(e.binding_strength == BindingStrength.STRONG for e in dep_evs)
            if not has_strong:
                # Step 2: Native test discovery for dependency
                candidates = self.discovery_engine.discover_tests_for_claim(
                    repo_root=repo_root,
                    repository_name=repo_name,
                    target_commit=target_commit,
                    subject=claim.subject,
                    dependency_symbol=dep_obj,
                    cost_tracker=tracker,
                    budget=budget
                )
                ranked = self.test_binder.bind_and_rank_candidates(claim, candidates, dependency_symbol=dep_obj)
                strong_candidates = [c for c in ranked if c.binding_strength == BindingStrength.STRONG]

                if trace:
                    EscalationTracer.record_step(
                        trace,
                        EvidenceActionType.TEST_DISCOVERY,
                        target=f"dependency {claim.subject} & {dep_obj}",
                        outcome=f"Discovered {len(candidates)} candidates ({len(strong_candidates)} strong)",
                        detail=f"Top candidate: {ranked[0].test_file}:{ranked[0].test_name}" if ranked else "No candidates"
                    )

                if strong_candidates:
                    exec_ev = self.executor.run_test_candidate(
                        claim_id=cid,
                        repo_root=repo_root,
                        repository_name=repo_name,
                        candidate=strong_candidates[0],
                        cost_tracker=tracker,
                        budget=budget
                    )
                    acquired_evidences.append(exec_ev)

                    if trace:
                        EscalationTracer.record_step(
                            trace,
                            EvidenceActionType.TARGETED_EXECUTION,
                            target=f"{strong_candidates[0].test_file}::{strong_candidates[0].test_name}",
                            outcome=exec_ev.supports_or_contradicts,
                            evidence_id=exec_ev.evidence_id,
                            binding_strength=exec_ev.binding_strength,
                            cost_increment=exec_ev.cost,
                            detail=exec_ev.detail
                        )

        # -------------------------------------------------------------
        # Branch 3: SYMBOL_EXISTS (Qualified / Unresolved)
        # -------------------------------------------------------------
        elif claim.claim_type == ClaimType.SYMBOL_EXISTS:
            # Check if symbol is a qualified name (e.g. parent.child)
            sym = claim.subject
            if "." in sym:
                parts = sym.split(".")
                parent_sym = parts[0]
                child_sym = parts[-1]
                search_evs = self.search_engine.search_qualified_symbol_or_attribute(
                    claim_id=cid,
                    repo_root=repo_root,
                    repository_name=repo_name,
                    base_commit=base_commit,
                    target_commit=target_commit,
                    file_path=claim.file_path,
                    parent_symbol=parent_sym,
                    child_symbol=child_sym,
                    cost_tracker=tracker
                )
                acquired_evidences.extend(search_evs)

                if trace:
                    for ev in search_evs:
                        EscalationTracer.record_step(
                            trace,
                            EvidenceActionType.REPOSITORY_SEARCH,
                            target=f"{parent_sym}.{child_sym}",
                            outcome=ev.supports_or_contradicts,
                            evidence_id=ev.evidence_id,
                            binding_strength=ev.binding_strength,
                            detail=ev.detail
                        )
            else:
                # Search general repository
                pass

        # -------------------------------------------------------------
        # Branch 4: General Attributes / Signatures / Imports
        # -------------------------------------------------------------
        else:
            # Repository search across file and git diff
            sym = claim.subject
            if "." in sym:
                parts = sym.split(".")
                parent_sym = parts[0]
                child_sym = parts[-1]
                search_evs = self.search_engine.search_qualified_symbol_or_attribute(
                    claim_id=cid,
                    repo_root=repo_root,
                    repository_name=repo_name,
                    base_commit=base_commit,
                    target_commit=target_commit,
                    file_path=claim.file_path,
                    parent_symbol=parent_sym,
                    child_symbol=child_sym,
                    cost_tracker=tracker
                )
                acquired_evidences.extend(search_evs)

        # Synthesize final decision using aggregator
        final_result = self.aggregator.aggregate(static_result, acquired_evidences)
        return final_result, acquired_evidences
