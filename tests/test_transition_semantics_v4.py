import pytest
import os
import json
from scripts.audit_transition_semantics_v4 import audit_transition_v4, extract_symbol_excerpt


def test_extract_symbol_excerpt_finds_actual_lines():
    code = "import sys\ndef helper():\n    pass\n\ndef target_func(a, b):\n    return a + b\n"
    excerpt, term, lineno = extract_symbol_excerpt(code, "target_func", [])
    assert "def target_func" in excerpt
    assert term == "target_func"
    assert lineno == 5


def test_semantic_audit_fails_on_missing_evidence(tmp_path):
    fake_spec = tmp_path / "fake_spec.json"
    fake_spec.write_text(json.dumps({
        "transition_id": "trans_fake_nonexistent",
        "repo_name": "fake/repo",
        "primary_file": "fake.py",
        "symbol": "fake_sym",
        "base_commit": "1111",
        "target_commit": "2222"
    }))
    res = audit_transition_v4(str(fake_spec))
    assert res["semantic_pass"] is False
    assert res["verdict"] in ["EVIDENCE_MISSING", "REPO_NOT_FOUND"]


def test_semantic_audit_no_keyword_only_bypass():
    res = extract_symbol_excerpt("x = 1\ny = 2", "absent_symbol", [])
    assert res[0] == ""
    assert res[1] == ""
    assert res[2] == 0
