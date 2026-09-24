"""
tests/test_evidence_taxonomy.py

Unit tests for evidence taxonomy disaggregation (Protocol V2.2-V1.2):
- Structural evidence taxonomy (STRUCTURAL_AST_EVIDENCE, VERIFIED_STRUCTURAL_EVIDENCE, NOT_APPLICABLE source origin, VERIFIED_TARGET_COMMIT snapshot).
- Test witness evidence taxonomy (EXECUTABLE_TEST_WITNESS, VERIFIED_TEST_WITNESS, VERIFIED_TARGET_WORKTREE).
- Dependency evidence taxonomy (DEPENDENCY_EVIDENCE, INCONCLUSIVE).
- Audit JSON taxonomy compliance.
"""

import json
import os
import pytest
from src.evidence_escalation.types import (
    EvidenceKind,
    DecisionEvidenceStatus,
    SourceOriginStatus,
    RepositorySnapshotStatus,
    AcquiredEvidence,
    BindingStrength,
    EvidenceActionType,
)


def test_taxonomy_enums():
    """Verify taxonomy enums have distinct values and disaggregated types."""
    assert EvidenceKind.EXECUTABLE_TEST_WITNESS.value == "EXECUTABLE_TEST_WITNESS"
    assert EvidenceKind.STRUCTURAL_AST_EVIDENCE.value == "STRUCTURAL_AST_EVIDENCE"
    assert EvidenceKind.DEPENDENCY_EVIDENCE.value == "DEPENDENCY_EVIDENCE"
    assert EvidenceKind.GIT_HISTORY_EVIDENCE.value == "GIT_HISTORY_EVIDENCE"

    assert DecisionEvidenceStatus.VERIFIED_TEST_WITNESS.value == "VERIFIED_TEST_WITNESS"
    assert DecisionEvidenceStatus.VERIFIED_STRUCTURAL_EVIDENCE.value == "VERIFIED_STRUCTURAL_EVIDENCE"
    assert DecisionEvidenceStatus.VERIFIED_DEPENDENCY_EVIDENCE.value == "VERIFIED_DEPENDENCY_EVIDENCE"
    assert DecisionEvidenceStatus.WEAK_TEST_WITNESS.value == "WEAK_TEST_WITNESS"
    assert DecisionEvidenceStatus.UNVERIFIED_SOURCE.value == "UNVERIFIED_SOURCE"
    assert DecisionEvidenceStatus.INCONCLUSIVE.value == "INCONCLUSIVE"

    assert SourceOriginStatus.NOT_APPLICABLE.value == "NOT_APPLICABLE"
    assert SourceOriginStatus.VERIFIED_TARGET_WORKTREE.value == "VERIFIED_TARGET_WORKTREE"
    assert SourceOriginStatus.SOURCE_ORIGIN_UNVERIFIED.value == "SOURCE_ORIGIN_UNVERIFIED"

    assert RepositorySnapshotStatus.VERIFIED_TARGET_COMMIT.value == "VERIFIED_TARGET_COMMIT"
    assert RepositorySnapshotStatus.SNAPSHOT_UNVERIFIED.value == "SNAPSHOT_UNVERIFIED"
    assert RepositorySnapshotStatus.NOT_APPLICABLE.value == "NOT_APPLICABLE"


def test_structural_evidence_model():
    """Structural AST evidence must have NOT_APPLICABLE for source_origin_status and VERIFIED_TARGET_COMMIT."""
    ev = AcquiredEvidence(
        evidence_id="EV-STRUCT-001",
        claim_id="CLM-000049",
        action_type=EvidenceActionType.REPOSITORY_SEARCH,
        source_type="AST_SYMBOL_RESOLUTION",
        repository="werkzeug",
        commit="target_commit_sha",
        file_path="src/werkzeug/sansio/response.py",
        content_hash="sha256_hash",
        binding_strength=BindingStrength.STRONG,
        supports_or_contradicts="CONTRADICTS",
        confidence=1.0,
        evidence_kind=EvidenceKind.STRUCTURAL_AST_EVIDENCE,
        source_origin_status=SourceOriginStatus.NOT_APPLICABLE.value,
        repository_snapshot_status=RepositorySnapshotStatus.VERIFIED_TARGET_COMMIT.value,
        base_symbol_presence=True,
        target_symbol_presence=False,
    )

    d = ev.to_dict()
    assert d["evidence_kind"] == "STRUCTURAL_AST_EVIDENCE"
    assert d["source_origin_status"] == "NOT_APPLICABLE"
    assert d["repository_snapshot_status"] == "VERIFIED_TARGET_COMMIT"
    assert d["base_symbol_presence"] is True
    assert d["target_symbol_presence"] is False

    restored = AcquiredEvidence.from_dict(d)
    assert restored.evidence_kind == EvidenceKind.STRUCTURAL_AST_EVIDENCE
    assert restored.source_origin_status == "NOT_APPLICABLE"
    assert restored.repository_snapshot_status == "VERIFIED_TARGET_COMMIT"


def test_test_witness_evidence_model():
    """Executable test witness must have VERIFIED_TARGET_WORKTREE for source_origin_status and VERIFIED_TARGET_COMMIT."""
    ev = AcquiredEvidence(
        evidence_id="EV-TEST-001",
        claim_id="CLM-000041",
        action_type=EvidenceActionType.TARGETED_EXECUTION,
        source_type="NATIVE_TEST_EXECUTION",
        repository="rich",
        commit="target_commit_sha",
        file_path="tests/test_text.py",
        content_hash="sha256_hash",
        binding_strength=BindingStrength.STRONG,
        supports_or_contradicts="SUPPORTS",
        confidence=0.95,
        evidence_kind=EvidenceKind.EXECUTABLE_TEST_WITNESS,
        source_origin_status=SourceOriginStatus.VERIFIED_TARGET_WORKTREE.value,
        repository_snapshot_status=RepositorySnapshotStatus.VERIFIED_TARGET_COMMIT.value,
        test_file_sha256="sha_file",
        test_function_sha256="sha_fn",
        requirement_count=3,
        requirements_satisfied=3,
        requirement_coverage=1.0,
    )

    d = ev.to_dict()
    assert d["evidence_kind"] == "EXECUTABLE_TEST_WITNESS"
    assert d["source_origin_status"] == "VERIFIED_TARGET_WORKTREE"
    assert d["repository_snapshot_status"] == "VERIFIED_TARGET_COMMIT"
    assert d["requirement_count"] == 3
    assert d["requirements_satisfied"] == 3
    assert d["requirement_coverage"] == 1.0


def test_audit_json_disaggregated_taxonomy():
    """Verify evidence_resolution_audit.json uses disaggregated taxonomy."""
    audit_path = "/code/rolemem-agent-memory/data/evidence_escalation_v1/evidence_resolution_audit.json"
    assert os.path.isfile(audit_path), f"Audit file not found at {audit_path}"

    with open(audit_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    stats = data["audit_statistics"]
    assert stats["verified_evidence_decisions_count"] == 5
    assert stats["verified_test_witness_decisions_count"] == 3
    assert stats["verified_structural_decisions_count"] == 2
    assert stats["verified_dependency_decisions_count"] == 0
    assert stats["all_newly_decided_with_test_count"] == 3
    assert stats["verified_evidence_decision_rate"] == 1.0
    assert stats["verified_test_witness_rate"] == 1.0

    entries = {e["claim_id"]: e for e in data["audit_entries"]}

    # CLM-37, 40, 41 must be VERIFIED_TEST_WITNESS with VERIFIED_TARGET_WORKTREE
    for cid in ["CLM-000037", "CLM-000040", "CLM-000041"]:
        entry = entries[cid]
        assert entry["decision_evidence_status"] == "VERIFIED_TEST_WITNESS"
        assert entry["evidence_kind"] == "EXECUTABLE_TEST_WITNESS"
        assert entry["source_origin_status"] == "VERIFIED_TARGET_WORKTREE"
        assert entry["repository_snapshot_status"] == "VERIFIED_TARGET_COMMIT"

    # CLM-49, 50 must be VERIFIED_STRUCTURAL_EVIDENCE with NOT_APPLICABLE for source origin
    for cid in ["CLM-000049", "CLM-000050"]:
        entry = entries[cid]
        assert entry["decision_evidence_status"] == "VERIFIED_STRUCTURAL_EVIDENCE"
        assert entry["evidence_kind"] == "STRUCTURAL_AST_EVIDENCE"
        assert entry["source_origin_status"] == "NOT_APPLICABLE"
        assert entry["repository_snapshot_status"] == "VERIFIED_TARGET_COMMIT"

    # CLM-44 must be INCONCLUSIVE because it had WEAK witness strength
    clm44 = entries["CLM-000044"]
    assert clm44["decision_evidence_status"] == "INCONCLUSIVE"
    assert clm44["witness_binding_strength"] == "WEAK"
    assert clm44["final_decision"] == "UNCERTAIN"
    assert clm44["static_decision"] == "UNCERTAIN"

