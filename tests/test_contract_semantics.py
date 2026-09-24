"""
tests/test_contract_semantics.py

Unit tests for Behavioral Contract Semantics Module (Protocol V2.2-V1.2):
- Requirement extraction across all categories of behavioral contracts.
- OPERATION, ATTRIBUTE_STATE, CONSTRUCTOR_ARGUMENT, DEFAULT_VALUE, RETURN_RELATION, SEQUENCE.
"""

import pytest
from src.claim_validity.types import MemoryClaim, ClaimType
from src.evidence_escalation.contract_semantics import (
    BehavioralRequirementType,
    BehavioralRequirement,
    ContractSemanticsExtractor
)


def test_clm37_semantics_extraction():
    claim = MemoryClaim(
        claim_id="CLM-000037",
        claim_type=ClaimType.BEHAVIORAL_CONTRACT,
        subject="HelpFormatter",
        predicate="satisfies_contract",
        object=", text buffered with write_text() can be retrieved via getvalue().",
        raw_statement="When HelpFormatter is initialized, text buffered with write_text() can be retrieved via getvalue()."
    )
    reqs = ContractSemanticsExtractor.extract_requirements(claim)
    req_types = [r.req_type for r in reqs]
    req_targets = [r.target_name for r in reqs]

    assert BehavioralRequirementType.OPERATION in req_types
    assert BehavioralRequirementType.SEQUENCE in req_types
    assert "write_text" in req_targets
    assert "getvalue" in req_targets
    assert "write_text -> getvalue" in req_targets


def test_clm40_semantics_extraction():
    claim = MemoryClaim(
        claim_id="CLM-000040",
        claim_type=ClaimType.BEHAVIORAL_CONTRACT,
        subject="Console",
        predicate="satisfies_contract",
        object="with record=True, text printed via print() is captured and retrievable through export_text().",
        raw_statement="When Console is initialized with record=True, text printed via print() is captured and retrievable through export_text()."
    )
    reqs = ContractSemanticsExtractor.extract_requirements(claim)
    req_types = [r.req_type for r in reqs]
    req_targets = [r.target_name for r in reqs]

    assert BehavioralRequirementType.CONSTRUCTOR_ARGUMENT in req_types
    assert "record" in req_targets
    assert BehavioralRequirementType.OPERATION in req_types
    assert "print" in req_targets
    assert "export_text" in req_targets
    assert BehavioralRequirementType.SEQUENCE in req_types
    assert "print -> export_text" in req_targets


def test_clm41_semantics_extraction():
    claim = MemoryClaim(
        claim_id="CLM-000041",
        claim_type=ClaimType.BEHAVIORAL_CONTRACT,
        subject="Text",
        predicate="satisfies_contract",
        object="with a string returns the plain string content when converted via str().",
        raw_statement="Text instance initialized with a string returns the plain string content when converted via str()."
    )
    reqs = ContractSemanticsExtractor.extract_requirements(claim)
    req_types = [r.req_type for r in reqs]
    req_targets = [r.target_name for r in reqs]

    assert BehavioralRequirementType.OPERATION in req_types
    assert "str" in req_targets
    assert BehavioralRequirementType.RETURN_RELATION in req_types


def test_clm42_semantics_extraction():
    claim = MemoryClaim(
        claim_id="CLM-000042",
        claim_type=ClaimType.BEHAVIORAL_CONTRACT,
        subject="FastAPI",
        predicate="satisfies_contract",
        object="with default title attribute set to 'FastAPI'.",
        raw_statement="FastAPI application instance initializes with default title attribute set to 'FastAPI'."
    )
    reqs = ContractSemanticsExtractor.extract_requirements(claim)
    req_types = [r.req_type for r in reqs]

    assert BehavioralRequirementType.ATTRIBUTE_STATE in req_types
    assert BehavioralRequirementType.DEFAULT_VALUE in req_types

    title_req = next(r for r in reqs if r.target_name == "title")
    assert title_req.expected_value == "FastAPI"


def test_clm43_semantics_extraction():
    claim = MemoryClaim(
        claim_id="CLM-000043",
        claim_type=ClaimType.BEHAVIORAL_CONTRACT,
        subject="Starlette",
        predicate="satisfies_contract",
        object="with default debug mode set to False.",
        raw_statement="Starlette application instance initializes with default debug mode set to False."
    )
    reqs = ContractSemanticsExtractor.extract_requirements(claim)
    req_types = [r.req_type for r in reqs]

    assert BehavioralRequirementType.ATTRIBUTE_STATE in req_types
    assert BehavioralRequirementType.DEFAULT_VALUE in req_types

    debug_req = next(r for r in reqs if r.target_name == "debug")
    assert debug_req.expected_value == "False"


def test_clm44_semantics_extraction():
    claim = MemoryClaim(
        claim_id="CLM-000044",
        claim_type=ClaimType.BEHAVIORAL_CONTRACT,
        subject="PoolManager",
        predicate="satisfies_contract",
        object="with default connection pool configuration without arguments.",
        raw_statement="PoolManager class can be instantiated with default connection pool configuration without arguments."
    )
    reqs = ContractSemanticsExtractor.extract_requirements(claim)
    req_types = [r.req_type for r in reqs]

    assert BehavioralRequirementType.CONSTRUCTOR_ARGUMENT in req_types
    assert BehavioralRequirementType.DEFAULT_VALUE in req_types
    assert any(r.target_name == "constructor" and r.expected_value == "0_args" for r in reqs)
    assert any(r.target_name == "default_configuration" for r in reqs)
