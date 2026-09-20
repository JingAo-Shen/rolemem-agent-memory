"""
tests/test_transition_semantics_v4_1.py
Unit tests for Semantic Audit V4.1 schema helper and fail-closed logic.
"""

import pytest
from scripts.audit_transition_semantics_v4_1 import read_causal_matrix, evaluate_claim_entailment


def test_read_causal_matrix_valid():
    causal_data = {
        "matrix": {
            "stale_on_base": True,
            "stale_on_target": False,
            "valid_on_base": True,
            "valid_on_target": True
        }
    }
    ok, parsed, err = read_causal_matrix(causal_data)
    assert ok is True
    assert parsed["stale_on_base"] is True
    assert parsed["stale_on_target"] is False
    assert parsed["valid_on_base"] is True
    assert parsed["valid_on_target"] is True
    assert err == "OK"


def test_read_causal_matrix_missing_field():
    causal_data = {
        "matrix": {
            "stale_on_base": True,
            "stale_on_target": False,
            "valid_on_base": True
            # missing valid_on_target
        }
    }
    ok, parsed, err = read_causal_matrix(causal_data)
    assert ok is False
    assert "missing field valid_on_target" in err


def test_read_causal_matrix_non_bool():
    causal_data = {
        "matrix": {
            "stale_on_base": "true", # string instead of bool
            "stale_on_target": False,
            "valid_on_base": True,
            "valid_on_target": True
        }
    }
    ok, parsed, err = read_causal_matrix(causal_data)
    assert ok is False
    assert "field stale_on_base is not bool" in err


def test_evaluate_claim_entailment():
    candidate = "Use get_io_stream(name) instead of get_binary_stream"
    evidence = "def get_io_stream(name: str): return sys.stdout.buffer"
    res = evaluate_claim_entailment(candidate, evidence, "get_io_stream", ["get_binary_stream"])
    assert res == "ENTAILED"

    empty_res = evaluate_claim_entailment("", evidence, "get_io_stream", [])
    assert empty_res == "NOT_ENTAILED"
