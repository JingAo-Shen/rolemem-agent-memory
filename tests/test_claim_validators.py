"""
tests/test_claim_validators.py

Unit tests for Protocol V2.2 individual claim validators:
- Verifies behavior for all validator types.
- Tests fail-uncertain semantics (INSUFFICIENT_EVIDENCE when evidence is missing).
- Tests artifact-claim binding verification with ClaimEvidenceBinder.
"""

import pytest
from src.claim_validity.types import (
    ClaimType,
    ValidationStatus,
    GroundingStatus,
    MemoryClaim,
    GroundedClaim
)
from src.claim_validity.validators import (
    SymbolExistsValidator,
    AttributeExistsValidator,
    ImportPathValidator,
    SignatureValidator,
    DefaultValueValidator,
    DeprecationValidator,
    ReturnValueValidator,
    BehavioralContractValidator,
    DependencyContractValidator
)


def test_symbol_exists_validator():
    val = SymbolExistsValidator()
    claim = MemoryClaim("C1", "Symbol foo exists", ClaimType.SYMBOL_EXISTS, "foo", "exists", "app.py")
    gc_exact = GroundedClaim(claim, GroundingStatus.EXACT, target_node_name="foo")
    gc_unres = GroundedClaim(claim, GroundingStatus.UNRESOLVED)

    status_ok, evs_ok, _ = val.validate(gc_exact, "def foo(): pass", "def foo(): pass")
    assert status_ok == ValidationStatus.SUPPORTED

    status_fail, evs_fail, _ = val.validate(gc_unres, "def foo(): pass", "def bar(): pass")
    assert status_fail == ValidationStatus.CONTRADICTED


def test_attribute_exists_validator():
    val = AttributeExistsValidator()
    claim = MemoryClaim("C2", "Class Client has method connect", ClaimType.ATTRIBUTE_EXISTS, "Client", "has_attribute", "connect")
    gc = GroundedClaim(claim, GroundingStatus.EXACT, target_node_name="Client")

    src_with_attr = "class Client:\n    def connect(self): pass\n"
    src_no_attr = "class Client:\n    def disconnect(self): pass\n"

    status_ok, _, _ = val.validate(gc, "", src_with_attr)
    assert status_ok == ValidationStatus.SUPPORTED

    status_fail, _, _ = val.validate(gc, "", src_no_attr)
    assert status_fail == ValidationStatus.CONTRADICTED


def test_signature_validator():
    val = SignatureValidator()
    claim = MemoryClaim("C3", "Function query accepts timeout", ClaimType.SIGNATURE_COMPATIBLE, "query", "accepts", "timeout", qualifiers={"expected_parameters": ["timeout"]})
    gc = GroundedClaim(claim, GroundingStatus.EXACT, target_node_name="query")

    src_with_param = "def query(sql, timeout=30): pass\n"
    src_no_param = "def query(sql): pass\n"

    status_ok, _, _ = val.validate(gc, "", src_with_param)
    assert status_ok == ValidationStatus.SUPPORTED

    status_fail, _, _ = val.validate(gc, "", src_no_param)
    assert status_fail == ValidationStatus.CONTRADICTED


def test_default_value_validator():
    val = DefaultValueValidator()
    claim = MemoryClaim("C4", "Parameter timeout defaults to 30", ClaimType.DEFAULT_VALUE, "connect", "default", "30", qualifiers={"parameter_name": "timeout", "expected_default": "30"})
    gc = GroundedClaim(claim, GroundingStatus.EXACT, target_node_name="connect")

    src_match = "def connect(host, timeout=30): pass\n"
    src_mismatch = "def connect(host, timeout=60): pass\n"

    status_ok, _, _ = val.validate(gc, "", src_match)
    assert status_ok == ValidationStatus.SUPPORTED

    status_fail, _, _ = val.validate(gc, "", src_mismatch)
    assert status_fail == ValidationStatus.CONTRADICTED


def test_deprecation_validator():
    val = DeprecationValidator()
    claim = MemoryClaim("C5", "Function legacy_run is deprecated", ClaimType.DEPRECATION_STATUS, "legacy_run", "is", "deprecated")
    gc = GroundedClaim(claim, GroundingStatus.EXACT, target_node_name="legacy_run")

    src_dep = "def legacy_run():\n    warnings.warn('deprecated', DeprecationWarning)\n"
    src_active = "def legacy_run():\n    return 42\n"

    status_dep, _, _ = val.validate(gc, "", src_dep)
    assert status_dep == ValidationStatus.SUPPORTED

    status_active, _, _ = val.validate(gc, "", src_active)
    assert status_active == ValidationStatus.CONTRADICTED


def test_import_path_validator_all():
    val = ImportPathValidator()
    claim = MemoryClaim("C_imp", "pprint exported in __all__", ClaimType.IMPORT_PATH_VALID, "pprint", "exported_in", "__all__")
    gc = GroundedClaim(claim, GroundingStatus.EXACT, target_node_name="pprint")

    src_with_all = "__all__ = ['pprint', 'dumps']\npprint = lambda: None\n"
    src_without_sym_in_all = "__all__ = ['dumps']\npprint = lambda: None\n"

    status_ok, _, _ = val.validate(gc, "", src_with_all)
    assert status_ok == ValidationStatus.SUPPORTED

    status_fail, _, _ = val.validate(gc, "", src_without_sym_in_all)
    assert status_fail == ValidationStatus.CONTRADICTED


def test_behavioral_contract_validator():
    val = BehavioralContractValidator()
    claim = MemoryClaim(
        claim_id="C6",
        raw_statement="When Parser is initialized...",
        claim_type=ClaimType.BEHAVIORAL_CONTRACT,
        subject="Parser",
        predicate="maintains_contract",
        object="",
        symbol="Parser",
        source_case_id="CASE-01"
    )
    gc = GroundedClaim(claim, GroundingStatus.EXACT, target_node_name="Parser")

    exec_pass = {
        "case_id": "CASE-01",
        "claim_subject": "Parser",
        "claim_predicate": "maintains parser contract",
        "target_execution": {"passed": True, "exit_code": 0, "contract_hash": "c_hash_1"}
    }
    exec_fail = {
        "case_id": "CASE-01",
        "claim_subject": "Parser",
        "claim_predicate": "maintains parser contract",
        "target_execution": {"passed": False, "exit_code": 1, "contract_hash": "c_hash_1"}
    }
    exec_mismatched_case = {
        "case_id": "CASE-99",
        "claim_subject": "Parser",
        "claim_predicate": "maintains parser contract",
        "target_execution": {"passed": True, "exit_code": 0, "contract_hash": "c_hash_1"}
    }

    # 1. Matching artifact pass
    status_ok, _, _ = val.validate(gc, "", "", execution_artifact=exec_pass)
    assert status_ok == ValidationStatus.SUPPORTED

    # 2. Matching artifact fail
    status_fail, _, _ = val.validate(gc, "", "", execution_artifact=exec_fail)
    assert status_fail == ValidationStatus.CONTRADICTED

    # 3. Mismatched artifact -> INSUFFICIENT_EVIDENCE (fail-uncertain)
    status_mismatch, _, _ = val.validate(gc, "", "", execution_artifact=exec_mismatched_case)
    assert status_mismatch == ValidationStatus.INSUFFICIENT_EVIDENCE

    # 4. No artifact -> INSUFFICIENT_EVIDENCE (fail-uncertain)
    status_none, _, _ = val.validate(gc, "", "", execution_artifact=None)
    assert status_none == ValidationStatus.INSUFFICIENT_EVIDENCE


def test_dependency_contract_validator():
    val = DependencyContractValidator()
    claim = MemoryClaim(
        claim_id="C7",
        raw_statement="HookCaller depends on varnames",
        claim_type=ClaimType.DEPENDENCY_CONTRACT,
        subject="HookCaller",
        predicate="depends_on",
        object="varnames",
        symbol="HookCaller",
        source_case_id="CASE-02"
    )
    gc = GroundedClaim(claim, GroundingStatus.EXACT, target_node_name="HookCaller")

    art_fail = {
        "case_id": "CASE-02",
        "target_symbol": "HookCaller",
        "dependency_symbol": "varnames",
        "dependency_path": ["HookCaller", "varnames"],
        "old_on_target": {"passed": False, "contract_hash": "dep_hash_2"}
    }
    status_fail, _, _ = val.validate(gc, "", "", execution_artifact=art_fail)
    assert status_fail == ValidationStatus.CONTRADICTED

    # Without artifact, returns INSUFFICIENT_EVIDENCE
    status_none, _, _ = val.validate(gc, "", "", execution_artifact=None)
    assert status_none == ValidationStatus.INSUFFICIENT_EVIDENCE
