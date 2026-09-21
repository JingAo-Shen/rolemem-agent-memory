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
