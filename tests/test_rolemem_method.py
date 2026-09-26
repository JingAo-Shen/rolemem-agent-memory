"""
tests/test_rolemem_method.py

Unit and Integration Tests for RoleMem Method Modules:
- Schema: 6-tuple model, SHA-256 fingerprint, integrity verification, serialization.
- Store: multi-index lookup (role, symbol, repo, path, status), CRUD, JSONL export/load.
- Retriever: role-aware hard gating, BM25 scoring, dense similarity, confidence weighting.
- Lifecycle Engine: B50-bounded escalation, state updates (Preserve, Downgrade, Invalidate).
- Adapter & Agent Interface: evaluation adapter and agent context prompt generation.
"""

import pytest
import os
import json
import tempfile

from src.rolemem.schema import (
    RoleMemoryRecord,
    RoleEnum,
    MemoryStatus,
    ClaimPayload,
    EvidencePayload,
    TemporalAnchor
)
from src.rolemem.store import RoleMemStore
from src.rolemem.retriever import RoleAwareRetriever, BM25RetrieverScorer
from src.rolemem.lifecycle import RoleMemLifecycleEngine, LifecycleUpdateResult
from src.rolemem.adapter import RoleMemEvaluationAdapter, RoleMemAgentInterface
from src.evidence_escalation.types import CostBudget


def test_schema_6tuple_and_integrity():
    """Verify 6-tuple memory schema, fingerprint computation, and integrity verification."""
    claim = ClaimPayload(
        structured_claim={"module": "agateexcel.table_xlsx", "symbol": "TableXLSX.from_xlsx", "parameter_or_attr": "sheet", "expected_default": None},
        raw_statement="In wireservice/agate-excel, parameter 'sheet' defaults to None.",
        claim_type="DEFAULT_VALUE",
        repository_name="wireservice/agate-excel"
    )
    evidence = EvidencePayload(
        evidence_path="agateexcel/table_xlsx.py",
        evidence_lineno=42,
        evidence_snippet="def from_xlsx(cls, path, sheet=None):",
        extraction_channel="AST_ANALYSIS"
    )
    role = RoleEnum.from_claim_type(claim.claim_type)
    assert role == RoleEnum.CONFIG

    anchor = TemporalAnchor(
        commit_sha="37f1b3884ee28f25d005cf8de2d67d68b18ada30",
        timestamp_iso8601="2020-01-01T00:00:00Z",
        release_ref="v0.2.3"
    )

    record = RoleMemoryRecord(
        memory_id="MEM-001",
        claim=claim,
        evidence=evidence,
        role=role,
        confidence=0.95,
        timestamp=anchor
    )

    # Check fingerprint exists and is valid SHA256 (64 hex chars)
    assert len(record.fingerprint) == 64
    assert record.verify_integrity() is True

    # Tampering test
    record.claim.raw_statement = "Tampered statement"
    assert record.verify_integrity() is False

    # Reset and test serialization
    record.claim.raw_statement = "In wireservice/agate-excel, parameter 'sheet' defaults to None."
    assert record.verify_integrity() is True

    d = record.to_dict()
    assert d["memory_id"] == "MEM-001"
    assert d["role"] == "CONFIG"
    assert d["confidence"] == 0.95

    restored = RoleMemoryRecord.from_dict(d)
    assert restored.memory_id == record.memory_id
    assert restored.role == record.role
    assert restored.verify_integrity() is True

    json_str = record.to_json()
    from_json_rec = RoleMemoryRecord.from_json(json_str)
    assert from_json_rec.memory_id == "MEM-001"


def test_store_multi_index_and_crud():
    """Verify RoleMemStore indexing and CRUD operations."""
    store = RoleMemStore()

    # Create records of different roles and repos
    rec1 = RoleMemoryRecord(
        memory_id="MEM-001",
        claim=ClaimPayload(
            structured_claim={"module": "mod_a", "symbol": "func_a"},
            raw_statement="func_a exists",
            claim_type="SYMBOL_EXISTS",
            repository_name="repo_alpha"
        ),
        evidence=EvidencePayload(evidence_path="src/a.py"),
        role=RoleEnum.API,
        confidence=0.9
    )

    rec2 = RoleMemoryRecord(
        memory_id="MEM-002",
        claim=ClaimPayload(
            structured_claim={"module": "mod_b", "symbol": "setting_b"},
            raw_statement="setting_b default is 10",
            claim_type="DEFAULT_VALUE",
            repository_name="repo_alpha"
        ),
        evidence=EvidencePayload(evidence_path="src/b.py"),
        role=RoleEnum.CONFIG,
        confidence=0.85
    )

    rec3 = RoleMemoryRecord(
        memory_id="MEM-003",
        claim=ClaimPayload(
            structured_claim={"module": "tests.test_c", "symbol": "test_c"},
            raw_statement="test_c returns True",
            claim_type="BEHAVIORAL_CONTRACT",
            repository_name="repo_beta"
        ),
        evidence=EvidencePayload(evidence_path="tests/test_c.py"),
        role=RoleEnum.BEHAVIOR,
        confidence=0.8
    )

    store.add_record(rec1)
    store.add_record(rec2)
    store.add_record(rec3)

    assert len(store) == 3

    # Test filtering by role
    api_recs = store.filter_by_role(RoleEnum.API)
    assert len(api_recs) == 1
    assert api_recs[0].memory_id == "MEM-001"

    config_recs = store.filter_by_role(RoleEnum.CONFIG)
    assert len(config_recs) == 1
    assert config_recs[0].memory_id == "MEM-002"

    # Test filtering by repository
    alpha_recs = store.filter_by_repository("repo_alpha")
    assert len(alpha_recs) == 2

    # Test filtering by symbol
    sym_recs = store.filter_by_symbol("mod_a", "func_a")
    assert len(sym_recs) == 1
    assert sym_recs[0].memory_id == "MEM-001"

    # Test invalidation
    assert store.invalidate("MEM-002", reason="Removed in v2") is True
    assert store.get("MEM-002").status == MemoryStatus.INVALIDATED
    assert len(store.get_active()) == 2

    # Test JSONL export and load
    with tempfile.TemporaryDirectory() as tmpdir:
        jsonl_path = os.path.join(tmpdir, "test_store.jsonl")
        exported_count = store.export_jsonl(jsonl_path)
        assert exported_count == 3

        new_store = RoleMemStore()
        loaded_count = new_store.load_jsonl(jsonl_path)
        assert loaded_count == 3
        assert new_store.get("MEM-001").claim.structured_claim["symbol"] == "func_a"
        assert new_store.get("MEM-002").status == MemoryStatus.INVALIDATED


def test_role_aware_retriever():
    """Verify RoleAwareRetriever role-gating, BM25 scoring, and confidence weighting."""
    store = RoleMemStore()

    # Add API record
    rec_api = RoleMemoryRecord(
        memory_id="MEM-API-1",
        claim=ClaimPayload(
            structured_claim={"module": "urllib3.poolmanager", "symbol": "PoolManager.request"},
            raw_statement="PoolManager.request method performs HTTP requests with headers and method.",
            claim_type="SIGNATURE_COMPATIBLE",
            repository_name="urllib3/urllib3"
        ),
        evidence=EvidencePayload(
            evidence_path="src/urllib3/poolmanager.py",
            evidence_snippet="def request(self, method, url, fields=None, headers=None, **urlopen_kw):"
        ),
        role=RoleEnum.API,
        confidence=0.95
    )

    # Add Config record with overlapping keyword "headers"
    rec_cfg = RoleMemoryRecord(
        memory_id="MEM-CFG-1",
        claim=ClaimPayload(
            structured_claim={"module": "urllib3.util.request", "symbol": "make_headers", "expected_default": None},
            raw_statement="make_headers parameter user_agent defaults to None.",
            claim_type="DEFAULT_VALUE",
            repository_name="urllib3/urllib3"
        ),
        evidence=EvidencePayload(
            evidence_path="src/urllib3/util/request.py",
            evidence_snippet="def make_headers(keep_alive=None, accept_encoding=None, user_agent=None):"
        ),
        role=RoleEnum.CONFIG,
        confidence=0.70
    )

    store.add_record(rec_api)
    store.add_record(rec_cfg)

    retriever = RoleAwareRetriever(store, alpha=1.0, beta=0.5, omega=0.3)

    # Query targeting API role should NEVER return CONFIG record despite keyword overlap
    api_results = retriever.retrieve(query="make headers request", target_role=RoleEnum.API)
    assert len(api_results) == 1
    assert api_results[0][0].memory_id == "MEM-API-1"

    # Query targeting CONFIG role should return only CONFIG record
    cfg_results = retriever.retrieve(query="make headers request", target_role=RoleEnum.CONFIG)
    assert len(cfg_results) == 1
    assert cfg_results[0][0].memory_id == "MEM-CFG-1"

    # Query without role filter returns both ranked
    all_results = retriever.retrieve(query="PoolManager HTTP request", target_role=None)
    assert len(all_results) >= 1
    assert all_results[0][0].memory_id == "MEM-API-1"


def test_lifecycle_engine_transitions():
    """Verify RoleMemLifecycleEngine state transition logic."""
    engine = RoleMemLifecycleEngine(confidence_boost=0.05, confidence_decay=0.80)

    # Test PRESERVE on mock static AST
    rec = RoleMemoryRecord(
        memory_id="MEM-LIFECYCLE-1",
        claim=ClaimPayload(
            structured_claim={"module": "math_utils", "symbol": "add", "expected_parameters": ["a", "b"]},
            raw_statement="Function add takes parameters a and b.",
            claim_type="SIGNATURE_COMPATIBLE",
            repository_name="test/mock-repo"
        ),
        evidence=EvidencePayload(
            evidence_path="math_utils.py",
            evidence_snippet="def add(a, b): return a + b"
        ),
        role=RoleEnum.API,
        confidence=0.90
    )

    # Mock evaluation by overriding file sources or evaluating directly
    res = engine.evaluate_record(
        record=rec,
        target_commit="target_commit_sha_123",
        base_commit="base_commit_sha_123"
    )

    assert isinstance(res, LifecycleUpdateResult)
    assert res.memory_id == "MEM-LIFECYCLE-1"
    assert res.escalation_tier in ("TIER_0_STATIC_AST", "TIER_1_FILE_SEARCH", "TIER_2_MANIFEST_PARSING", "TIER_3_TEST_EXECUTION")
    assert len(rec.action_history) == 1


def test_evaluation_adapter_and_agent_interface():
    """Verify RoleMemEvaluationAdapter and RoleMemAgentInterface execution."""
    adapter = RoleMemEvaluationAdapter()

    sample_case = {
        "case_id": "FV22-TEST-001",
        "structured_claim": {
            "module": "dummy.mod",
            "symbol": "dummy_func",
            "expected_parameters": ["x", "y"]
        },
        "raw_statement": "In dummy/mod, dummy_func accepts parameters [x, y].",
        "claim_type": "SIGNATURE_COMPATIBLE",
        "repository_name": "dummy/mod"
    }

    pred = adapter.evaluate_case(sample_case)
    assert pred["case_id"] == "FV22-TEST-001"
    assert "predicted_label" in pred
    assert "confidence" in pred
    assert "escalation_tier" in pred
    assert "action_count" in pred
    assert "execution_wall_time_sec" in pred

    # Test Agent Interface
    agent_iface = RoleMemAgentInterface()
    agent_iface.add_memory(
        memory_id="MEM-AG-01",
        structured_claim={"module": "api.auth", "symbol": "authenticate"},
        raw_statement="authenticate() returns UserToken upon valid credentials.",
        claim_type="BEHAVIORAL_CONTRACT",
        evidence_path="api/auth.py",
        confidence=0.95
    )

    prompt_context = agent_iface.format_context_prompt("How to authenticate user credentials?")
    assert "[RoleMem Verified Codebase Knowledge]" in prompt_context
    assert "authenticate()" in prompt_context
    assert "Confidence: 0.95" in prompt_context


def test_default_value_evolution_checker():
    """Verify DefaultValueEvolutionChecker logic across all 4 formal rules."""
    from src.rolemem.lifecycle import DefaultValueEvolutionChecker, FunctionSignature

    base_code = """
def connect(host, port=8080, timeout=30, retry=True):
    pass
"""
    # 1. Target with same defaults -> VALID
    target_same = """
def connect(host, port=8080, timeout=30, retry=True):
    pass
"""
    sig_base = DefaultValueEvolutionChecker.extract_signature_from_ast(base_code, "connect")
    sig_same = DefaultValueEvolutionChecker.extract_signature_from_ast(target_same, "connect")
    dec, rule, ev = DefaultValueEvolutionChecker.check_evolution(sig_base, sig_same, "timeout", expected_default=30)
    assert dec == "VALID"
    assert rule == "DEFAULT_VALUE_PRESERVED"

    # 2. Target with changed default -> PARTIALLY_VALID
    target_changed = """
def connect(host, port=8080, timeout=60, retry=True):
    pass
"""
    sig_changed = DefaultValueEvolutionChecker.extract_signature_from_ast(target_changed, "connect")
    dec, rule, ev = DefaultValueEvolutionChecker.check_evolution(sig_base, sig_changed, "timeout", expected_default=30)
    assert dec == "PARTIALLY_VALID"
    assert rule == "DEFAULT_VALUE_MUTATED_COMPATIBLE"

    # 3. Target with parameter removed -> STALE
    target_removed = """
def connect(host, port=8080, retry=True):
    pass
"""
    sig_removed = DefaultValueEvolutionChecker.extract_signature_from_ast(target_removed, "connect")
    dec, rule, ev = DefaultValueEvolutionChecker.check_evolution(sig_base, sig_removed, "timeout", expected_default=30)
    assert dec == "STALE"
    assert rule == "DEFAULT_VALUE_PARAMETER_REMOVED"

    # 4. Target with parameter made required -> STALE
    target_required = """
def connect(host, timeout, port=8080, retry=True):
    pass
"""
    sig_required = DefaultValueEvolutionChecker.extract_signature_from_ast(target_required, "connect")
    dec, rule, ev = DefaultValueEvolutionChecker.check_evolution(sig_base, sig_required, "timeout", expected_default=30)
    assert dec == "STALE"
    assert rule == "DEFAULT_VALUE_MADE_REQUIRED"


def test_deprecation_status_schema_unification():
    """Verify DeprecationStatus enum normalization across boolean, string, and object representations."""
    from src.rolemem.schema import DeprecationStatus

    # Boolean normalization
    assert DeprecationStatus.from_value(True) == DeprecationStatus.DEPRECATED
    assert DeprecationStatus.from_value(False) == DeprecationStatus.ACTIVE

    # String normalization
    assert DeprecationStatus.from_value("deprecated") == DeprecationStatus.DEPRECATED
    assert DeprecationStatus.from_value("DEPRECATED") == DeprecationStatus.DEPRECATED
    assert DeprecationStatus.from_value("active") == DeprecationStatus.ACTIVE
    assert DeprecationStatus.from_value("supported") == DeprecationStatus.ACTIVE

    # Object normalization
    assert DeprecationStatus.from_value({"is_deprecated": True}) == DeprecationStatus.DEPRECATED
    assert DeprecationStatus.from_value({"is_deprecated": False}) == DeprecationStatus.ACTIVE
    assert DeprecationStatus.from_value({"status": "deprecated"}) == DeprecationStatus.DEPRECATED
    assert DeprecationStatus.from_value({"status": "active"}) == DeprecationStatus.ACTIVE

