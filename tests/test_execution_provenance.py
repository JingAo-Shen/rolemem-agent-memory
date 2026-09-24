"""
tests/test_execution_provenance.py

Unit tests for execution provenance and source origin auditing (Protocol V2.2-V1.1):
- Source origin verification (VERIFIED_TARGET_WORKTREE vs SOURCE_ORIGIN_UNVERIFIED).
- Evidence hashes (test_function_sha256, stdout_sha256, command_sha256).
- Audit fields consistency.
"""

import os
import json
import pytest
from src.evidence_escalation.types import (
    SourceOriginStatus,
    DecisionEvidenceStatus,
    AcquiredEvidence,
    BindingStrength,
    EvidenceActionType
)
from src.evidence_escalation.executor import TargetedWorktreeExecutor


def test_evidence_provenance_model():
    ev = AcquiredEvidence(
        evidence_id="EV-TEST-1234",
        claim_id="CLM-000041",
        action_type=EvidenceActionType.TARGETED_EXECUTION,
        source_type="NATIVE_TEST_EXECUTION",
        repository="rich",
        commit="9a99acc97d26d7832200a271ed8e95dd59df10c7",
        file_path="tests/test_text.py",
        content_hash="hash123",
        binding_strength=BindingStrength.STRONG,
        supports_or_contradicts="SUPPORTS",
        confidence=0.95,
        test_file_sha256="sha_file_123",
        test_function_sha256="sha_fn_123",
        stdout_sha256="sha_out_123",
        stderr_sha256="sha_err_123",
        command_sha256="sha_cmd_123",
        source_origin_status=SourceOriginStatus.VERIFIED_TARGET_WORKTREE.value,
        dependency_environment_status="CURRENT_ENVIRONMENT_NOT_HISTORICALLY_RESTORED"
    )

    d = ev.to_dict()
    assert d["evidence_id"] == "EV-TEST-1234"
    assert d["test_function_sha256"] == "sha_fn_123"
    assert d["source_origin_status"] == "VERIFIED_TARGET_WORKTREE"
    assert d["dependency_environment_status"] == "CURRENT_ENVIRONMENT_NOT_HISTORICALLY_RESTORED"

    # Deserialization test
    ev_restored = AcquiredEvidence.from_dict(d)
    assert ev_restored.evidence_id == ev.evidence_id
    assert ev_restored.test_function_sha256 == "sha_fn_123"
    assert ev_restored.source_origin_status == "VERIFIED_TARGET_WORKTREE"


def test_audit_json_integrity():
    audit_path = "/code/rolemem-agent-memory/data/evidence_escalation_v1/evidence_resolution_audit.json"
    assert os.path.isfile(audit_path), f"Audit file not found at {audit_path}"

    with open(audit_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert "audit_statistics" in data
    assert "audit_entries" in data

    stats = data["audit_statistics"]
    assert stats["total_claims_audited"] == 55
    assert stats["escalated_claims_count"] == 11
    assert stats["newly_decided_count"] == 5
    assert stats["verified_evidence_decisions_count"] == 5
    assert stats["verified_test_witness_decisions_count"] == 3
    assert stats["verified_structural_decisions_count"] == 2
    assert stats["verified_evidence_decision_rate"] == 1.0

    entries = data["audit_entries"]
    assert len(entries) == 55

    # Check CLM-000041 specifically
    clm41 = next((e for e in entries if e["claim_id"] == "CLM-000041"), None)
    assert clm41 is not None
    assert clm41["selected_test_file"] == "tests/test_text.py"
    assert clm41["selected_test_name"] == "test_str"
    assert clm41["witness_binding_strength"] == "STRONG"
    assert clm41["source_origin_status"] == "VERIFIED_TARGET_WORKTREE"
    assert clm41["decision_evidence_status"] == "VERIFIED_TEST_WITNESS"
    assert clm41["dataflow_binding"] is True
    assert clm41["operation_coverage"] == 1.0

