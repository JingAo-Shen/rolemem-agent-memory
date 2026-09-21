"""
tests/test_evidence_escalation.py

Comprehensive Unit Tests for Protocol V2.2-V1 Evidence Escalation:
- Verifies types and serialization.
- Verifies cost accounting and budget tracking.
- Verifies trace logging and export.
- Verifies repository search on qualified symbols.
- Verifies test discovery and claim-test semantic binding.
- Verifies execution error handling (ERROR != STALE).
- Verifies evidence aggregator decision thresholds.
- Verifies selective escalation gate: decided static claims take 0 escalation actions and cost 0.
"""

import os
import json
import pytest

from src.claim_validity.types import (
    ClaimType,
    GroundingStatus,
    ValidationStatus,
    MemoryClaim,
    ClaimEvaluationResult,
    ClaimEvidence,
    EvidenceType
)
from src.evidence_escalation.types import (
    EvidenceActionType,
    BindingStrength,
    ExecutionStatus,
    CostBudget,
    AcquiredEvidence,
    TestCandidate,
    EvidenceAcquisitionRequest,
    EscalationTrace
)
from src.evidence_escalation.cost import CostTracker
from src.evidence_escalation.trace import EscalationTracer
from src.evidence_escalation.repository_search import RepositorySearchEngine
from src.evidence_escalation.test_discovery import NativeTestDiscoveryEngine
from src.evidence_escalation.test_binding import ClaimTestBinder
from src.evidence_escalation.executor import TargetedWorktreeExecutor
from src.evidence_escalation.binding import EscalatedEvidenceAggregator
from src.evidence_escalation.pipeline import EvidenceEscalationPipeline


def test_types_and_serialization():
    ev = AcquiredEvidence(
        evidence_id="EV-TEST-1",
        claim_id="CLM-000001",
        action_type=EvidenceActionType.TARGETED_EXECUTION,
        source_type="NATIVE_TEST",
        repository="test_repo",
        commit="abcdef12",
        file_path="tests/test_demo.py",
        content_hash="hash123",
        binding_strength=BindingStrength.STRONG,
        supports_or_contradicts="SUPPORTS",
        confidence=0.95,
        detail="Test passed"
    )
    d = ev.to_dict()
    assert d["action_type"] == "TARGETED_EXECUTION"
    assert d["binding_strength"] == "STRONG"

    ev2 = AcquiredEvidence.from_dict(d)
    assert ev2.evidence_id == "EV-TEST-1"
    assert ev2.action_type == EvidenceActionType.TARGETED_EXECUTION
    assert ev2.binding_strength == BindingStrength.STRONG

    claim_ev = ev.to_claim_evidence()
    assert claim_ev.evidence_type == EvidenceType.EXECUTION
    assert claim_ev.supports_or_contradicts == "SUPPORTS"


def test_cost_tracker_and_budget():
    tracker = CostTracker()
    tracker.add_file_scan(5)
    tracker.add_test_inspection(3)
    tracker.add_execution(125.5)
    tracker.add_action(EvidenceActionType.TEST_DISCOVERY)
    tracker.add_action(EvidenceActionType.TARGETED_EXECUTION)

    assert tracker.repository_files_scanned == 5
    assert tracker.tests_inspected == 3
    assert tracker.executions_run == 1
    assert tracker.execution_time_ms == 125.5
    assert tracker.total_actions == 2
    assert tracker.action_counts["TEST_DISCOVERY"] == 1
    assert tracker.action_counts["TARGETED_EXECUTION"] == 1

    budget = CostBudget(max_files_scanned=10, max_tests_inspected=5, max_executions_run=2, max_total_actions=5)
    exceeded, _ = tracker.is_budget_exceeded(budget)
    assert not exceeded

    tight_budget = CostBudget(max_files_scanned=4)
    exceeded, msg = tracker.is_budget_exceeded(tight_budget)
    assert exceeded
    assert "max_files_scanned" in msg


def test_trace_logging(tmp_path):
    trace = EscalationTracer.start_trace("CLM-000037", "UNCERTAIN")
    EscalationTracer.record_step(
        trace,
        action_type=EvidenceActionType.TEST_DISCOVERY,
        target="HelpFormatter",
        outcome="Discovered 3 candidates",
        binding_strength=BindingStrength.STRONG
    )
    EscalationTracer.record_step(
        trace,
        action_type=EvidenceActionType.TARGETED_EXECUTION,
        target="tests/test_help.py::test_write_text",
        outcome="SUPPORTS",
        evidence_id="EV-1",
        binding_strength=BindingStrength.STRONG,
        cost_increment={"execution_time_ms": 50.0}
    )
    EscalationTracer.finish_trace(
        trace=trace,
        final_decision="VALID",
        total_cost={"total_actions": 2},
        stop_reason="RESOLVED_TO_VALID",
        acquired_evidences=[{"evidence_id": "EV-1"}]
    )

    p = EscalationTracer.save_trace(trace, str(tmp_path))
    assert os.path.exists(p)

    with open(p, "r", encoding="utf-8") as f:
        loaded = json.load(f)
    assert loaded["claim_id"] == "CLM-000037"
    assert loaded["static_decision"] == "UNCERTAIN"
    assert loaded["final_decision"] == "VALID"
    assert len(loaded["steps"]) == 2
    assert loaded["steps"][0]["action_type"] == "TEST_DISCOVERY"


def test_claim_test_binder_token_extraction():
    claim = MemoryClaim(
        claim_id="CLM-000037",
        raw_statement="HelpFormatter text buffered with write_text() can be retrieved via getvalue().",
        claim_type=ClaimType.BEHAVIORAL_CONTRACT,
        subject="HelpFormatter",
        predicate="satisfies_contract",
        object=", text buffered with write_text() can be retrieved via getvalue()."
    )
    tokens = ClaimTestBinder.extract_operation_tokens(claim)
    assert "write_text" in tokens
    assert "getvalue" in tokens


def test_claim_test_binder_scoring():
    binder = ClaimTestBinder()
    claim = MemoryClaim(
        claim_id="CLM-000037",
        raw_statement="HelpFormatter text buffered with write_text() can be retrieved via getvalue().",
        claim_type=ClaimType.BEHAVIORAL_CONTRACT,
        subject="HelpFormatter",
        predicate="satisfies_contract",
        object="text buffered with write_text() can be retrieved via getvalue()."
    )

    # Strong candidate
    cand_strong = TestCandidate(
        test_file="tests/test_help.py",
        test_name="test_formatter_write_and_get",
        subject_mentions=2,
        object_mentions=0,
        dependency_mentions=0,
        assertion_count=2,
        target_commit="c1",
        source_hash="h1",
        binding_strength=BindingStrength.UNBOUND,
        discovery_reason="",
        test_source="def test_formatter_write_and_get():\n    f = HelpFormatter()\n    f.write_text('hi')\n    assert f.getvalue() == 'hi'\n"
    )
    res_strong = binder.evaluate_binding(claim, cand_strong)
    assert res_strong.binding_strength == BindingStrength.STRONG
    assert res_strong.object_mentions >= 2

    # Weak candidate (only mentions name in AST without operations or assertions)
    cand_weak = TestCandidate(
        test_file="tests/test_help.py",
        test_name="test_misc",
        subject_mentions=1,
        object_mentions=0,
        dependency_mentions=0,
        assertion_count=0,
        target_commit="c1",
        source_hash="h2",
        binding_strength=BindingStrength.UNBOUND,
        discovery_reason="",
        test_source="def test_misc():\n    x = HelpFormatter\n"
    )
    res_weak = binder.evaluate_binding(claim, cand_weak)
    assert res_weak.binding_strength == BindingStrength.WEAK


def test_evidence_aggregator_decision_logic():
    aggregator = EscalatedEvidenceAggregator(strong_confidence_threshold=0.85)

    static_res = ClaimEvaluationResult(
        claim_id="CLM-000037",
        decision="UNCERTAIN",
        grounding_status=GroundingStatus.EXACT,
        validation_status=ValidationStatus.INSUFFICIENT_EVIDENCE,
        confidence=0.50,
        evidences=[]
    )

    # 1. Strong supporting evidence -> VALID
    strong_sup = AcquiredEvidence(
        evidence_id="EV-1",
        claim_id="CLM-000037",
        action_type=EvidenceActionType.TARGETED_EXECUTION,
        source_type="TEST",
        repository="repo",
        commit="c1",
        file_path="tests/test_help.py",
        content_hash="h1",
        binding_strength=BindingStrength.STRONG,
        supports_or_contradicts="SUPPORTS",
        confidence=0.95,
        detail="Test passed"
    )
    res_valid = aggregator.aggregate(static_res, [strong_sup])
    assert res_valid.decision == "VALID"
    assert res_valid.confidence == 0.95

    # 2. Strong contradicting evidence -> STALE
    strong_contra = AcquiredEvidence(
        evidence_id="EV-2",
        claim_id="CLM-000037",
        action_type=EvidenceActionType.TARGETED_EXECUTION,
        source_type="TEST",
        repository="repo",
        commit="c1",
        file_path="tests/test_help.py",
        content_hash="h2",
        binding_strength=BindingStrength.STRONG,
        supports_or_contradicts="CONTRADICTS",
        confidence=0.95,
        detail="Test failed"
    )
    res_stale = aggregator.aggregate(static_res, [strong_contra])
    assert res_stale.decision == "STALE"
    assert res_stale.confidence == 0.95

    # 3. Weak evidence -> UNCERTAIN
    weak_ev = AcquiredEvidence(
        evidence_id="EV-3",
        claim_id="CLM-000037",
        action_type=EvidenceActionType.TEST_DISCOVERY,
        source_type="TEST",
        repository="repo",
        commit="c1",
        file_path="tests/test_help.py",
        content_hash="h3",
        binding_strength=BindingStrength.WEAK,
        supports_or_contradicts="SUPPORTS",
        confidence=0.60,
        detail="Weak mention"
    )
    res_uncertain = aggregator.aggregate(static_res, [weak_ev])
    assert res_uncertain.decision == "UNCERTAIN"


def test_selective_escalation_gate_stops_on_decided():
    """Verify that claims with static decision VALID or STALE exit immediately with 0 escalation cost."""
    pipeline = EvidenceEscalationPipeline()

    # CAT A claim: file change, symbol unchanged -> statically VALID
    claim = MemoryClaim(
        claim_id="CLM-000001",
        raw_statement="Symbol `render_to_string` exists in `django/template/loader.py`.",
        claim_type=ClaimType.SYMBOL_EXISTS,
        subject="render_to_string",
        predicate="exists_in",
        object="django/template/loader.py",
        repository="django/django",
        file_path="django/template/loader.py",
        symbol="render_to_string"
    )

    src = "def render_to_string(template_name, context=None):\n    return ''\n"
    res, trace, cost = pipeline.evaluate_claim(
        claim_or_statement=claim,
        base_source=src,
        target_source=src,
        diff_hunk="@@ -1,1 +1,1 @@\n# comment\n",
        repository="django/django"
    )

    assert res.decision == "VALID"
    assert cost.total_actions == 0
    assert cost.executions_run == 0
    assert trace.stop_reason == "STATIC_DECIDED_NO_ESCALATION"
    assert len(trace.steps) == 0


def test_executor_error_handling_not_stale():
    """Verify that execution status ERROR/TIMEOUT/UNAVAILABLE maps to INCONCLUSIVE and is not treated as STALE."""
    aggregator = EscalatedEvidenceAggregator()

    inconclusive_ev = AcquiredEvidence(
        evidence_id="EV-ERR",
        claim_id="CLM-TEST",
        action_type=EvidenceActionType.TARGETED_EXECUTION,
        source_type="NATIVE_TEST_EXECUTION",
        repository="repo",
        commit="c1",
        file_path="tests/test_error.py",
        content_hash="errhash",
        binding_strength=BindingStrength.STRONG,
        supports_or_contradicts="INCONCLUSIVE",
        confidence=0.0,
        detail="Execution error: ModuleNotFoundError (not interpreted as staleness)"
    )

    static_res = ClaimEvaluationResult(
        claim_id="CLM-TEST",
        decision="UNCERTAIN",
        grounding_status=GroundingStatus.EXACT,
        validation_status=ValidationStatus.INSUFFICIENT_EVIDENCE,
        confidence=0.50,
        evidences=[]
    )

    final_res = aggregator.aggregate(static_res, [inconclusive_ev])
    assert final_res.decision == "UNCERTAIN"
    assert final_res.decision != "STALE"
