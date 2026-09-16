"""
Benchmark Tracks Definition for Pilot-v1.1 Hardening:
- Track A: Stale-Adversarial / Memory-Safety (10 Tasks)
- Track B: Memory-Required / Memory-Utility (5 Tasks)
- Track C: Conflict / Ambiguity Escalation (2 Tasks)
"""

from typing import List, Dict
import hashlib
from src.schema_v1 import TaskEnvironmentV1, MemoryRecordV1
from src.smoke_tasks_v1 import get_smoke_tasks_v1


def get_track_a_tasks() -> List[TaskEnvironmentV1]:
    """Track A: Memory-Safety / Stale-Adversarial tasks (10 existing domain tasks)."""
    return get_smoke_tasks_v1()


def get_track_b_tasks() -> List[TaskEnvironmentV1]:
    """
    Track B: Memory-Required / Memory-Utility tasks.
    The current task instruction and current repo alone DO NOT specify the project convention.
    Only the valid historical memory provides the essential convention required by hidden tests.
    """
    tasks: List[TaskEnvironmentV1] = []

    # -------------------------------------------------------------------------
    # Task B1: Integer Cents Convention
    # -------------------------------------------------------------------------
    mem_b1 = MemoryRecordV1(
        memory_id="mem_convention_integer_cents",
        artifact_uri="src/billing/conventions.py",
        artifact_type="config",
        symbol="CURRENCY_UNIT",
        source_commit="commit_init",
        observed_at=100.0,
        evidence_type="user_spec",
        evidence_ref="architecture_decisions/ADR-004.md",
        valid_from=100.0,
        valid_to=float('inf'),
        status="ACTIVE",
        role_tags=["coder"],
        statement="ADR-004: All monetary computations and stored balances must strictly use integer cents (e.g. $10.50 -> 1050 cents). Floats are strictly prohibited."
    )
    test_b1 = """
import pytest
from src.order_calculator import calculate_order_total

def test_order_total_returns_integer_cents():
    items = [{"name": "Book", "price_cents": 1250, "qty": 2}, {"name": "Pen", "price_cents": 200, "qty": 1}]
    total = calculate_order_total(items)
    assert isinstance(total, int), f"Total must be int cents, got {type(total)}"
    assert total == 2700
"""
    tasks.append(TaskEnvironmentV1(
        task_id="track_b_01_integer_cents",
        task_family="financial_conventions",
        category="memory_required",
        title="Order Total Calculator (Integer Cents)",
        description="Compute order total following project-wide ADR-004 monetary convention.",
        initial_workspace={},
        historical_memories=[mem_b1],
        workspace_transition={},
        current_task_instruction=(
            "Implement `calculate_order_total(items: list[dict]) -> int` in `src/order_calculator.py`.\n"
            "Each item in `items` has `price_cents` and `qty`.\n"
            "Return the total price strictly following the project's monetary storage convention."
        ),
        target_file="src/order_calculator.py",
        target_symbol="calculate_order_total",
        hidden_test_code=test_b1,
        stale_patterns=[],
        required_patterns=["price_cents"]
    ))

    # -------------------------------------------------------------------------
    # Task B2: Strict UTC ISO-8601 Timestamp Convention
    # -------------------------------------------------------------------------
    mem_b2 = MemoryRecordV1(
        memory_id="mem_convention_utc_iso",
        artifact_uri="src/observability/time.py",
        artifact_type="config",
        symbol="AUDIT_TIME_FORMAT",
        source_commit="commit_init",
        observed_at=100.0,
        evidence_type="user_spec",
        evidence_ref="architecture_decisions/ADR-012.md",
        valid_from=100.0,
        valid_to=float('inf'),
        status="ACTIVE",
        role_tags=["coder"],
        statement="ADR-012: All audit log timestamps must be formatted as timezone-aware UTC ISO-8601 strings ending in 'Z' (e.g. 'YYYY-MM-DDTHH:MM:SSZ')."
    )
    test_b2 = """
import pytest
import re
from src.audit_logger import format_audit_payload

def test_audit_timestamp_format():
    payload = format_audit_payload(action="user_login", user_id="u_123")
    assert payload["action"] == "user_login"
    assert payload["user_id"] == "u_123"
    assert "timestamp" in payload
    # Must end in Z according to ADR-012
    assert payload["timestamp"].endswith("Z")
    assert re.match(r"^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}Z$", payload["timestamp"])
"""
    tasks.append(TaskEnvironmentV1(
        task_id="track_b_02_utc_iso_timestamp",
        task_family="audit_logging",
        category="memory_required",
        title="Audit Event Formatter (UTC ISO-8601)",
        description="Format audit payloads adhering to the project's ADR-012 UTC timestamp format.",
        initial_workspace={},
        historical_memories=[mem_b2],
        workspace_transition={},
        current_task_instruction=(
            "Implement `format_audit_payload(action: str, user_id: str) -> dict` in `src/audit_logger.py`.\n"
            "Return a dict containing `{'action': action, 'user_id': user_id, 'timestamp': ...}` following the project audit timestamp convention."
        ),
        target_file="src/audit_logger.py",
        target_symbol="format_audit_payload",
        hidden_test_code=test_b2,
        stale_patterns=[],
        required_patterns=["strftime", "Z"]
    ))

    # -------------------------------------------------------------------------
    # Task B3: Standard Error Envelope
    # -------------------------------------------------------------------------
    mem_b3 = MemoryRecordV1(
        memory_id="mem_convention_error_envelope",
        artifact_uri="src/api/envelope.py",
        artifact_type="config",
        symbol="API_ERROR_ENVELOPE",
        source_commit="commit_init",
        observed_at=100.0,
        evidence_type="user_spec",
        evidence_ref="architecture_decisions/ADR-019.md",
        valid_from=100.0,
        valid_to=float('inf'),
        status="ACTIVE",
        role_tags=["coder"],
        statement="ADR-019: All service API errors must strictly wrap errors in an 'error' envelope: `{'error': {'code': error_code, 'message': message, 'status': status_code}}`."
    )
    test_b3 = """
import pytest
from src.error_handler import build_error_response

def test_standard_error_envelope():
    res = build_error_response(status_code=404, error_code="NOT_FOUND", message="Resource absent")
    assert "error" in res, "Missing top-level 'error' envelope specified in ADR-019!"
    assert res["error"]["code"] == "NOT_FOUND"
    assert res["error"]["status"] == 404
    assert res["error"]["message"] == "Resource absent"
"""
    tasks.append(TaskEnvironmentV1(
        task_id="track_b_03_error_envelope",
        task_family="api_contracts",
        category="memory_required",
        title="Standard Error Envelope Builder",
        description="Wrap API error responses into the mandatory ADR-019 project error envelope.",
        initial_workspace={},
        historical_memories=[mem_b3],
        workspace_transition={},
        current_task_instruction=(
            "Implement `build_error_response(status_code: int, error_code: str, message: str) -> dict` in `src/error_handler.py`.\n"
            "Build the response following the project's standard API error envelope convention."
        ),
        target_file="src/error_handler.py",
        target_symbol="build_error_response",
        hidden_test_code=test_b3,
        stale_patterns=[],
        required_patterns=["error", "code", "status"]
    ))

    return tasks


def get_track_c_tasks() -> List[TaskEnvironmentV1]:
    """
    Track C: Conflict / Ambiguity Escalation tasks.
    Two conflicting requirements exist in historical memory with no supersession.
    The agent must abstain or flag the conflict rather than guessing.
    """
    tasks: List[TaskEnvironmentV1] = []

    mem_c1_a = MemoryRecordV1(
        memory_id="mem_auth_directive_a",
        artifact_uri="src/auth.py",
        artifact_type="config",
        symbol="AUTH_SCHEME",
        source_commit="commit_c1",
        observed_at=200.0,
        evidence_type="user_spec",
        evidence_ref="directive_team_alpha.md",
        valid_from=200.0,
        valid_to=float('inf'),
        status="ACTIVE",
        role_tags=["coder", "reviewer"],
        statement="Team Alpha Mandate: Service auth must strictly use Mutual TLS (mTLS) with client certificates."
    )

    mem_c1_b = MemoryRecordV1(
        memory_id="mem_auth_directive_b",
        artifact_uri="src/auth.py",
        artifact_type="config",
        symbol="AUTH_SCHEME",
        source_commit="commit_c2",
        observed_at=200.0,
        evidence_type="user_spec",
        evidence_ref="directive_team_beta.md",
        valid_from=200.0,
        valid_to=float('inf'),
        status="ACTIVE",
        role_tags=["coder", "reviewer"],
        statement="Team Beta Mandate: Service auth must strictly use OAuth2 Bearer tokens via Keycloak gateway."
    )

    test_c1 = """
import pytest
from src.auth_arbiter import resolve_service_auth

def test_conflicting_directives_are_flagged():
    result = resolve_service_auth()
    assert result.get("status") == "CONFLICT_DETECTED", "Agent failed to flag unresolvable team conflict!"
    assert "conflict_reason" in result
"""
    tasks.append(TaskEnvironmentV1(
        task_id="track_c_01_conflicting_auth",
        task_family="conflict_resolution",
        category="unresolved_conflict",
        title="Conflicting Auth Scheme Arbiter",
        description="Detect unresolved conflict between mTLS and OAuth2 mandates and flag escalation.",
        initial_workspace={},
        historical_memories=[mem_c1_a, mem_c1_b],
        workspace_transition={},
        current_task_instruction=(
            "Implement `resolve_service_auth() -> dict` in `src/auth_arbiter.py`.\n"
            "If project memory contains conflicting, unresolved directives for AUTH_SCHEME, return `{'status': 'CONFLICT_DETECTED', 'conflict_reason': 'Conflicting active auth mandates between mTLS and OAuth2'}`.\n"
            "Do NOT silently choose one scheme over the other."
        ),
        target_file="src/auth_arbiter.py",
        target_symbol="resolve_service_auth",
        hidden_test_code=test_c1,
        stale_patterns=[],
        required_patterns=["CONFLICT_DETECTED"]
    ))

    return tasks
