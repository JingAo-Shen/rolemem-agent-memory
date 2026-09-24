"""
src/evidence_escalation/cost.py

Cost Accounting and Tracking for Protocol V2.2-V1.1 Evidence Escalation:
- Tracks fine-grained computational actions per claim and across evaluation batches.
- Measures repository files scanned, tests inspected, executions run, execution time ms, and total actions.
- Provides BudgetGuard for pre-action verification and budget exhaustion enforcement.
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional, Tuple
from .types import EvidenceActionType, CostBudget


@dataclass
class CostTracker:
    repository_files_scanned: int = 0
    tests_inspected: int = 0
    executions_run: int = 0
    execution_time_ms: float = 0.0
    total_actions: int = 0
    action_counts: Dict[str, int] = field(default_factory=dict)

    def add_file_scan(self, count: int = 1):
        self.repository_files_scanned += count

    def add_test_inspection(self, count: int = 1):
        self.tests_inspected += count

    def add_execution(self, time_ms: float):
        self.executions_run += 1
        self.execution_time_ms += max(0.0, time_ms)

    def add_action(self, action_type: EvidenceActionType):
        self.total_actions += 1
        act_name = action_type.value if isinstance(action_type, EvidenceActionType) else str(action_type)
        self.action_counts[act_name] = self.action_counts.get(act_name, 0) + 1

    def is_budget_exceeded(self, budget: CostBudget) -> Tuple[bool, str]:
        if self.repository_files_scanned >= budget.max_files_scanned:
            return True, f"Budget exceeded: max_files_scanned ({budget.max_files_scanned})"
        if self.tests_inspected >= budget.max_tests_inspected:
            return True, f"Budget exceeded: max_tests_inspected ({budget.max_tests_inspected})"
        if self.executions_run >= budget.max_executions_run:
            return True, f"Budget exceeded: max_executions_run ({budget.max_executions_run})"
        if self.total_actions >= budget.max_total_actions:
            return True, f"Budget exceeded: max_total_actions ({budget.max_total_actions})"
        return False, ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "repository_files_scanned": self.repository_files_scanned,
            "tests_inspected": self.tests_inspected,
            "executions_run": self.executions_run,
            "execution_time_ms": round(self.execution_time_ms, 2),
            "total_actions": self.total_actions,
            "action_counts": dict(self.action_counts)
        }

    def copy(self) -> CostTracker:
        return CostTracker(
            repository_files_scanned=self.repository_files_scanned,
            tests_inspected=self.tests_inspected,
            executions_run=self.executions_run,
            execution_time_ms=self.execution_time_ms,
            total_actions=self.total_actions,
            action_counts=dict(self.action_counts)
        )


class BudgetGuard:
    """Enforces pre-action budget constraints and resource reservations across all evidence acquisition stages."""

    @staticmethod
    def can_perform_action(
        tracker: CostTracker,
        budget: CostBudget,
        action_type: EvidenceActionType,
        files: int = 0,
        tests: int = 0,
        executions: int = 0,
        actions: int = 1
    ) -> Tuple[bool, str]:
        if tracker.total_actions + actions > budget.max_total_actions:
            return False, f"Total actions limit reached ({budget.max_total_actions})"

        if action_type == EvidenceActionType.TARGETED_EXECUTION or executions > 0:
            exec_to_add = max(1, executions) if action_type == EvidenceActionType.TARGETED_EXECUTION else executions
            if tracker.executions_run + exec_to_add > budget.max_executions_run:
                return False, f"Max executions reached ({budget.max_executions_run})"

        if action_type in (EvidenceActionType.TEST_DISCOVERY, EvidenceActionType.TEST_INSPECTION) or tests > 0:
            tests_to_add = max(1, tests) if action_type == EvidenceActionType.TEST_INSPECTION else tests
            if tracker.tests_inspected + tests_to_add > budget.max_tests_inspected:
                return False, f"Max tests inspected reached ({budget.max_tests_inspected})"

        if action_type == EvidenceActionType.REPOSITORY_SEARCH or files > 0:
            files_to_add = max(1, files) if action_type == EvidenceActionType.REPOSITORY_SEARCH else files
            if tracker.repository_files_scanned + files_to_add > budget.max_files_scanned:
                return False, f"Max files scanned reached ({budget.max_files_scanned})"

        return True, ""

    @staticmethod
    def reserve(
        tracker: CostTracker,
        budget: CostBudget,
        files: int = 0,
        tests: int = 0,
        executions: int = 0,
        actions: int = 1
    ) -> Tuple[bool, str]:
        if tracker.total_actions + actions > budget.max_total_actions:
            return False, f"Total actions limit reached ({budget.max_total_actions})"
        if tracker.repository_files_scanned + files > budget.max_files_scanned:
            return False, f"Max files scanned reached ({budget.max_files_scanned})"
        if tracker.tests_inspected + tests > budget.max_tests_inspected:
            return False, f"Max tests inspected reached ({budget.max_tests_inspected})"
        if tracker.executions_run + executions > budget.max_executions_run:
            return False, f"Max executions reached ({budget.max_executions_run})"
        return True, ""
