import pytest
from src.historical_claim_factuality_v2 import HistoricalClaimFactualityAuditorV2


def test_factuality_auditor_temporal_isolation():
    auditor = HistoricalClaimFactualityAuditorV2(use_llm=False)
    # Valid historical statement
    stmt = "Use get_binary_stream to read binary data from stdin."
    base_src = "def get_binary_stream(name: str):\n    return open(name, \"rb\")\n"
    is_isolated, leaks = auditor.evaluate_temporal_isolation(
        statement=stmt,
        base_content=base_src,
        target_commit="051725fa7e0c69effc9107066d8791c5b99242c3"
    )
    assert is_isolated is True
    assert len(leaks) == 0

    # Leakage of future phrase
    leaky_stmt = "get_binary_stream will be removed in later version."
    is_isolated_bad, leaks_bad = auditor.evaluate_temporal_isolation(
        statement=leaky_stmt,
        base_content=base_src,
        target_commit="051725fa7e0c69effc9107066d8791c5b99242c3"
    )
    assert is_isolated_bad is False
    assert len(leaks_bad) > 0


def test_factuality_auditor_structural_grounding():
    auditor = HistoricalClaimFactualityAuditorV2(use_llm=False)
    base_src = "def get_binary_stream(name: str):\n    return open(name, \"rb\")\n"
    is_grounded, found = auditor.evaluate_structural_grounding(
        statement="Use get_binary_stream for binary IO",
        symbols=["get_binary_stream"],
        base_content=base_src
    )
    assert is_grounded is True

    is_grounded_missing, _ = auditor.evaluate_structural_grounding(
        statement="Use non_existent_func for binary IO",
        symbols=["non_existent_func"],
        base_content=base_src
    )
    assert is_grounded_missing is False
