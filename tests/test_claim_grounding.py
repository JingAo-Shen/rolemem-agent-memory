"""
tests/test_claim_grounding.py

Unit tests for ClaimGrounder AST binding.
"""

import pytest
from src.claim_validity.grounding import ClaimGrounder
from src.claim_validity.types import ClaimType, GroundingStatus, MemoryClaim


@pytest.fixture
def grounder():
    return ClaimGrounder()


def test_grounding_exact_function(grounder):
    src = "def calculate_total(a, b):\n    return a + b\n"
    claim = MemoryClaim(
        claim_id="CLM-01",
        raw_statement="Function calculate_total exists",
        claim_type=ClaimType.SYMBOL_EXISTS,
        subject="calculate_total",
        predicate="exists_in",
        object="test.py"
    )
    res = grounder.ground(claim, src)
    assert res.grounding_status == GroundingStatus.EXACT
    assert res.target_node_name == "calculate_total"


def test_grounding_exact_class_method(grounder):
    src = "class User:\n    def get_id(self):\n        return 1\n"
    claim = MemoryClaim(
        claim_id="CLM-02",
        raw_statement="Method get_id exists in User",
        claim_type=ClaimType.SYMBOL_EXISTS,
        subject="User.get_id",
        predicate="exists_in",
        object="test.py"
    )
    res = grounder.ground(claim, src)
    assert res.grounding_status == GroundingStatus.EXACT


def test_grounding_aliased_import(grounder):
    src = "from os.path import exists as path_exists\n"
    claim = MemoryClaim(
        claim_id="CLM-03",
        raw_statement="Symbol exists is imported",
        claim_type=ClaimType.IMPORT_PATH_VALID,
        subject="path_exists",
        predicate="imported_from",
        object="os.path"
    )
    res = grounder.ground(claim, src)
    assert res.grounding_status == GroundingStatus.ALIASED


def test_grounding_unresolved(grounder):
    src = "def other_func():\n    pass\n"
    claim = MemoryClaim(
        claim_id="CLM-04",
        raw_statement="Symbol missing_symbol exists",
        claim_type=ClaimType.SYMBOL_EXISTS,
        subject="missing_symbol",
        predicate="exists_in",
        object="test.py"
    )
    res = grounder.ground(claim, src)
    assert res.grounding_status == GroundingStatus.UNRESOLVED
