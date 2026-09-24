"""
tests/test_budget_guard.py

Unit tests for BudgetGuard and CostBudget presets (Protocol V2.2-V1.1):
- Budget limit enforcement.
- Action-specific limits (executions, files, tests).
- Preset configurations (B10, B25, B50, B100).
"""

import pytest
from src.evidence_escalation.types import CostBudget, EvidenceActionType
from src.evidence_escalation.cost import CostTracker, BudgetGuard


def test_budget_presets():
    b10 = CostBudget.from_preset("B10")
    assert b10.max_files_scanned == 20
    assert b10.max_tests_inspected == 10
    assert b10.max_executions_run == 1
    assert b10.max_total_actions == 3

    b25 = CostBudget.from_preset("B25")
    assert b25.max_files_scanned == 50
    assert b25.max_tests_inspected == 25
    assert b25.max_executions_run == 2

    b50 = CostBudget.from_preset("B50")
    assert b50.max_files_scanned == 100
    assert b50.max_tests_inspected == 50
    assert b50.max_executions_run == 3

    b100 = CostBudget.from_preset("B100")
    assert b100.max_files_scanned == 300
    assert b100.max_tests_inspected == 100
    assert b100.max_executions_run == 5


def test_budget_guard_limits():
    budget = CostBudget(max_files_scanned=2, max_tests_inspected=2, max_executions_run=1, max_total_actions=2)
    tracker = CostTracker()

    can_act, reason = BudgetGuard.can_perform_action(tracker, budget, EvidenceActionType.REPOSITORY_SEARCH)
    assert can_act is True

    # Scan 2 files
    tracker.repository_files_scanned += 2
    tracker.total_actions += 1

    can_act, reason = BudgetGuard.can_perform_action(tracker, budget, EvidenceActionType.REPOSITORY_SEARCH)
    assert can_act is False
    assert "files scanned reached" in reason.lower()

    # Execution check
    can_exec, exec_reason = BudgetGuard.can_perform_action(tracker, budget, EvidenceActionType.TARGETED_EXECUTION)
    assert can_exec is True

    tracker.executions_run += 1
    tracker.total_actions += 1

    can_exec2, exec_reason2 = BudgetGuard.can_perform_action(tracker, budget, EvidenceActionType.TARGETED_EXECUTION)
    assert can_exec2 is False
    assert "reached" in exec_reason2.lower() or "limit" in exec_reason2.lower()


def test_budget_guard_reservation():
    budget = CostBudget(max_files_scanned=10, max_tests_inspected=15, max_executions_run=2, max_total_actions=5)
    tracker = CostTracker()

    # Can reserve within limits
    can_res, reason = BudgetGuard.reserve(tracker, budget, files=5, tests=10, executions=1, actions=2)
    assert can_res is True
    assert reason == ""

    # Exceeding files reservation
    can_res_f, reason_f = BudgetGuard.reserve(tracker, budget, files=15)
    assert can_res_f is False
    assert "files scanned" in reason_f.lower()

    # Exceeding tests reservation
    can_res_t, reason_t = BudgetGuard.reserve(tracker, budget, tests=20)
    assert can_res_t is False
    assert "tests inspected" in reason_t.lower()

    # Exceeding executions reservation
    can_res_e, reason_e = BudgetGuard.reserve(tracker, budget, executions=3)
    assert can_res_e is False
    assert "executions" in reason_e.lower()

    # Exceeding actions reservation
    can_res_a, reason_a = BudgetGuard.reserve(tracker, budget, actions=6)
    assert can_res_a is False
    assert "total actions" in reason_a.lower()


def test_pipeline_budget_limit_files():
    from src.claim_validity.types import MemoryClaim, ClaimType
    from src.evidence_escalation.pipeline import EvidenceEscalationPipeline

    pipeline = EvidenceEscalationPipeline()
    claim = MemoryClaim(
        claim_id="CLM-000008",
        claim_type=ClaimType.SYMBOL_EXISTS,
        subject="HTMLParser.unescape",
        predicate="exists",
        object="",
        raw_statement="HTMLParser.unescape exists.",
        file_path="src/utils.py",
        repository="psf/requests"
    )

    budget = CostBudget(max_files_scanned=1, max_tests_inspected=1, max_executions_run=0, max_total_actions=1)
    res, trace, cost_tracker = pipeline.evaluate_claim(
        claim_or_statement=claim,
        repository_root="/code/repo_cache/requests",
        base_commit="commit1",
        target_commit="commit2",
        available_budget=budget
    )

    # Budget strictly respected
    assert cost_tracker.repository_files_scanned <= 1
    assert cost_tracker.total_actions <= 1


def test_pipeline_budget_limit_tests():
    from src.claim_validity.types import MemoryClaim, ClaimType
    from src.evidence_escalation.pipeline import EvidenceEscalationPipeline

    pipeline = EvidenceEscalationPipeline()
    claim = MemoryClaim(
        claim_id="CLM-000041",
        claim_type=ClaimType.BEHAVIORAL_CONTRACT,
        subject="Text",
        predicate="converts_to",
        object="str",
        raw_statement="Text object converts to string representation containing its plain text via str().",
        file_path="rich/text.py",
        repository="Textualize/rich"
    )

    budget = CostBudget(max_files_scanned=50, max_tests_inspected=3, max_executions_run=0, max_total_actions=5)
    res, trace, cost_tracker = pipeline.evaluate_claim(
        claim_or_statement=claim,
        repository_root="/code/repo_cache/rich",
        base_commit="commit1",
        target_commit="commit2",
        available_budget=budget
    )

    assert cost_tracker.tests_inspected <= 3
    assert cost_tracker.executions_run == 0


def test_pipeline_budget_limit_executions():
    from src.claim_validity.types import MemoryClaim, ClaimType
    from src.evidence_escalation.pipeline import EvidenceEscalationPipeline

    pipeline = EvidenceEscalationPipeline()
    claim = MemoryClaim(
        claim_id="CLM-000041",
        claim_type=ClaimType.BEHAVIORAL_CONTRACT,
        subject="Text",
        predicate="converts_to",
        object="str",
        raw_statement="Text object converts to string representation containing its plain text via str().",
        file_path="rich/text.py",
        repository="Textualize/rich"
    )

    budget = CostBudget(max_files_scanned=50, max_tests_inspected=50, max_executions_run=0, max_total_actions=5)
    res, trace, cost_tracker = pipeline.evaluate_claim(
        claim_or_statement=claim,
        repository_root="/code/repo_cache/rich",
        base_commit="commit1",
        target_commit="commit2",
        available_budget=budget
    )

    assert cost_tracker.executions_run == 0


def test_per_claim_budget_invariants():
    """
    Budget Invariant Test:
    Iterate across all 11 escalation claims on presets B10, B25, B50, B100.
    Assert for each single claim that:
    - files_scanned <= preset.max_files_scanned
    - tests_inspected <= preset.max_tests_inspected
    - executions_run <= preset.max_executions_run
    - total_actions <= preset.max_total_actions
    """
    from scripts.evaluate_evidence_escalation_v1 import load_blind_data
    from src.evidence_escalation.pipeline import EvidenceEscalationPipeline
    from src.evidence_escalation.types import CostBudget, PipelineConfig

    prepared_cases = load_blind_data()
    pipeline = EvidenceEscalationPipeline()

    escalation_cases = []
    for case in prepared_cases:
        res, trace, cost = pipeline.evaluate_claim(
            claim_or_statement=case["claim"],
            base_source=case["b_src"],
            target_source=case["t_src"],
            diff_hunk=case["diff"],
            symbol_qualified_name=case["sym"],
            file_path=case["fpath"],
            repository=case["repo"],
            repository_root=case["repo_root"],
            base_commit=case["b_commit"],
            target_commit=case["t_commit"],
            config=PipelineConfig(repo_search=False, dependency_inspection=False, test_discovery=False, targeted_execution=False)
        )
        if trace.static_decision == "UNCERTAIN":
            escalation_cases.append(case)

    assert len(escalation_cases) == 11, f"Expected 11 escalation cases, got {len(escalation_cases)}"

    presets = ["B10", "B25", "B50", "B100"]
    for preset_name in presets:
        budget = CostBudget.from_preset(preset_name)
        for case in escalation_cases:
            res, trace, cost = pipeline.evaluate_claim(
                claim_or_statement=case["claim"],
                base_source=case["b_src"],
                target_source=case["t_src"],
                diff_hunk=case["diff"],
                symbol_qualified_name=case["sym"],
                file_path=case["fpath"],
                repository=case["repo"],
                repository_root=case["repo_root"],
                base_commit=case["b_commit"],
                target_commit=case["t_commit"],
                available_budget=budget
            )
            assert cost.repository_files_scanned <= budget.max_files_scanned, (
                f"Claim {case['cid']} scanned {cost.repository_files_scanned} files > {budget.max_files_scanned} for preset {preset_name}"
            )
            assert cost.tests_inspected <= budget.max_tests_inspected, (
                f"Claim {case['cid']} inspected {cost.tests_inspected} tests > {budget.max_tests_inspected} for preset {preset_name}"
            )
            assert cost.executions_run <= budget.max_executions_run, (
                f"Claim {case['cid']} executed {cost.executions_run} tests > {budget.max_executions_run} for preset {preset_name}"
            )
            assert cost.total_actions <= budget.max_total_actions, (
                f"Claim {case['cid']} performed {cost.total_actions} actions > {budget.max_total_actions} for preset {preset_name}"
            )



