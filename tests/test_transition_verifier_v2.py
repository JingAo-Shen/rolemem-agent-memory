"""
Unit and Integration Tests for TransitionVerifierV2 and Fixtures V2 (Pilot-v1.2b).
Validates:
- AST symbol inspection accuracy
- Local Git cat-file commit verification
- Causality verification
- Fixtures V2 integrity and controls
"""

import os
import json
import pytest

from src.transition_verifier_v2 import TransitionVerifierV2, inspect_symbol_in_code_ast


def test_ast_symbol_inspection_detects_warnings_and_docstrings():
    clean_code = """
def my_func(x):
    return x * 2
"""
    res_clean = inspect_symbol_in_code_ast(clean_code, "my_func")
    assert res_clean["found"] is True
    assert res_clean["deprecated"] is False

    dep_doc_code = """
def my_func(x):
    '''This function is deprecated. Use modern_func instead.'''
    return x * 2
"""
    res_doc = inspect_symbol_in_code_ast(dep_doc_code, "my_func")
    assert res_doc["found"] is True
    assert res_doc["deprecated"] is True

    dep_warn_code = """
import warnings

def my_func(x):
    warnings.warn('my_func is deprecated', DeprecationWarning, stacklevel=2)
    return x * 2
"""
    res_warn = inspect_symbol_in_code_ast(dep_warn_code, "my_func")
    assert res_warn["found"] is True
    assert res_warn["deprecated"] is True


def test_ast_symbol_inspection_detects_getattr_deprecation():
    getattr_code = """
import warnings

def __getattr__(name):
    if name == "legacy_property":
        warnings.warn("'legacy_property' is deprecated", DeprecationWarning, stacklevel=2)
        return 42
    raise AttributeError(name)
"""
    res = inspect_symbol_in_code_ast(getattr_code, "legacy_property")
    assert res["found"] is True
    assert res["deprecated"] is True


def test_transition_verifier_v2_accepts_verified_local_candidate():
    verifier = TransitionVerifierV2()
    # Werkzeug 01 cached_property is cached in /code/repo_cache/werkzeug
    candidate = {
        "transition_id": "trans_gold_werkzeug_01_cached_property",
        "repo_name": "pallets/werkzeug",
        "base_commit": "25ca9cd92956e48a38f7a32c837e0f8a54c8ae31",
        "history_commit": "25ca9cd92956e48a38f7a32c837e0f8a54c8ae31",
        "transition_commit": "004b446eac19db2ff351a923fd594d4f23d67e90",
        "target_commit": "f50fbf5659875821c19ae21b237b4290b12e1e2d",
        "changed_files": ["src/werkzeug/utils.py"],
        "changed_symbols": ["werkzeug.utils.invalidate_cached_property"],
        "pr_url": "https://github.com/pallets/werkzeug/pull/2084",
        "issue_url": "https://github.com/pallets/werkzeug/issues/2084"
    }

    report = verifier.verify_candidate_v2(candidate)
    assert report["commit_verification"] == "PASS"
    assert report["causality_status"] == "CAUSALITY_PASS"
    assert report["overall_status"] == "ACCEPT"


def test_gold_transitions_v2_file_integrity():
    gold_v2_path = "data/gold/gold_transitions_v2.jsonl"
    assert os.path.exists(gold_v2_path), "gold_transitions_v2.jsonl must exist"

    with open(gold_v2_path, "r", encoding="utf-8") as f:
        records = [json.loads(line) for line in f if line.strip()]

    assert len(records) == 8, f"Expected exactly 8 accepted Gold V2 transitions, got {len(records)}"

    for r in records:
        assert r["benchmark_status"] == "PROVISIONAL_GOLD_V2"
        f_dir = r.get("fixture_path")
        assert f_dir and os.path.isdir(f_dir), f"Fixture dir {f_dir} missing for {r['transition_id']}"
        assert os.path.exists(os.path.join(f_dir, "metadata.json"))
        assert os.path.exists(os.path.join(f_dir, "environment.json"))
        assert os.path.isdir(os.path.join(f_dir, "after"))
        assert os.path.exists(os.path.join(f_dir, "hidden_tests", "test_evaluation.py"))
