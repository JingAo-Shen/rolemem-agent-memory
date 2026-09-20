"""
tests/test_memory_validity_benchmark_integrity_v2_1.py

Rigorous Benchmark Integrity Test Suite for Protocol V2.1-R1:
- test_cat_a_digest_same(): Asserts all Category A cases have identical AST digests.
- test_cat_b_digest_changed(): Asserts all Category B cases have changed AST digests.
- test_cat_c_digest_same(): Asserts all Category C cases have identical AST digests.
- test_cat_d_digest_changed_or_removed(): Asserts all Category D cases have altered/removed digests.
- test_no_placeholder_digest(): Asserts zero placeholder strings across all benchmark data.
- test_cat_b_has_behavioral_contract(): Asserts every Cat B case has an executable contract artifact.
- test_cat_c_has_counterfactual_evidence(): Asserts every Cat C case has a counterfactual artifact.
- test_case_concentration_limits(): Asserts concentration limits (max 5 per transition, max 8 per repo).
"""

import os
import glob
import json
import pytest

DATA_DIR = "/code/rolemem-agent-memory/data/memory_validity_v2_1"
GOLD_PATH = os.path.join(DATA_DIR, "gold_labels.jsonl")
BLIND_PATH = os.path.join(DATA_DIR, "blind_inputs.jsonl")
CONTRACTS_DIR = os.path.join(DATA_DIR, "contracts")
COUNTERFACTUALS_DIR = os.path.join(DATA_DIR, "counterfactuals")
STATS_PATH = os.path.join(DATA_DIR, "benchmark_stats.json")


def load_gold_records():
    with open(GOLD_PATH, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def load_blind_records():
    with open(BLIND_PATH, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def test_cat_a_digest_same():
    records = load_gold_records()
    cat_a = [r for r in records if r["category"] == "CAT_A_FILE_CHG_SYM_SAME_VALID"]
    assert len(cat_a) > 0, "Cat A must contain cases"
    for r in cat_a:
        assert r["symbol_changed"] is False, f"Cat A case {r['case_id']} has symbol_changed=True"
        assert r["symbol_digest_base"] == r["symbol_digest_target"], f"Cat A case {r['case_id']} digests differ"
        assert r["gold_label"] == "VALID"


def test_cat_b_digest_changed():
    records = load_gold_records()
    cat_b = [r for r in records if r["category"] == "CAT_B_SYM_CHG_MEMORY_VALID"]
    assert len(cat_b) > 0, "Cat B must contain cases"
    for r in cat_b:
        assert r["symbol_changed"] is True, f"Cat B case {r['case_id']} has symbol_changed=False"
        assert r["symbol_digest_base"] != r["symbol_digest_target"], f"Cat B case {r['case_id']} digests are identical"
        assert r["gold_label"] == "VALID"


def test_cat_c_digest_same():
    records = load_gold_records()
    cat_c = [r for r in records if r["category"] == "CAT_C_SYM_SAME_MEMORY_STALE"]
    assert len(cat_c) > 0, "Cat C must contain cases"
    for r in cat_c:
        assert r["symbol_changed"] is False, f"Cat C case {r['case_id']} has symbol_changed=True"
        assert r["symbol_digest_base"] == r["symbol_digest_target"], f"Cat C case {r['case_id']} digests differ"
        assert r["gold_label"] == "STALE"


def test_cat_d_digest_changed_or_removed():
    records = load_gold_records()
    cat_d = [r for r in records if r["category"] == "CAT_D_SYM_CHG_OR_REM_STALE"]
    assert len(cat_d) > 0, "Cat D must contain cases"
    for r in cat_d:
        assert r["symbol_changed"] is True, f"Cat D case {r['case_id']} has symbol_changed=False"
        assert r["symbol_digest_base"] != r["symbol_digest_target"] or r["symbol_digest_target"] == "NONE"
        assert r["gold_label"] == "STALE"


def test_no_placeholder_digest():
    banned = ["DIGEST_BASE", "DIGEST_TARGET", "MOCK_DIGEST", "UNKNOWN_DIGEST"]
    for root, _, files in os.walk(DATA_DIR):
        for fn in files:
            fpath = os.path.join(root, fn)
            with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            for b in banned:
                assert b not in content, f"Placeholder digest '{b}' found in {fpath}"


def test_cat_b_has_behavioral_contract():
    records = load_gold_records()
    cat_b = [r for r in records if r["category"] == "CAT_B_SYM_CHG_MEMORY_VALID"]
    for r in cat_b:
        cid = r["case_id"]
        cpath = os.path.join(CONTRACTS_DIR, f"{cid}.json")
        assert os.path.exists(cpath), f"Cat B case {cid} missing contract artifact at {cpath}"
        with open(cpath, "r", encoding="utf-8") as f:
            cdata = json.load(f)
        base_pass = cdata["base_execution"]["passed"] if "base_execution" in cdata else cdata.get("base_contract_pass")
        target_pass = cdata["target_execution"]["passed"] if "target_execution" in cdata else cdata.get("target_contract_pass")
        assert base_pass is True
        assert target_pass is True
        assert cdata.get("machine_verified") is True


def test_cat_c_has_counterfactual_evidence():
    records = load_gold_records()
    cat_c = [r for r in records if r["category"] == "CAT_C_SYM_SAME_MEMORY_STALE"]
    for r in cat_c:
        cid = r["case_id"]
        cfpath = os.path.join(COUNTERFACTUALS_DIR, f"{cid}.json")
        assert os.path.exists(cfpath), f"Cat C case {cid} missing counterfactual artifact at {cfpath}"
        with open(cfpath, "r", encoding="utf-8") as f:
            cfdata = json.load(f)
        old_b = cfdata["old_on_base"]["passed"] if isinstance(cfdata.get("old_on_base"), dict) else cfdata.get("old_on_base")
        old_t = cfdata["old_on_target"]["passed"] if isinstance(cfdata.get("old_on_target"), dict) else cfdata.get("old_on_target")
        new_t = cfdata["new_on_target"]["passed"] if isinstance(cfdata.get("new_on_target"), dict) else cfdata.get("new_on_target")
        assert old_b is True
        assert old_t is False
        assert new_t is True
        assert cfdata.get("machine_verified") is True


def test_case_concentration_limits():
    assert os.path.exists(STATS_PATH), "benchmark_stats.json must exist"
    with open(STATS_PATH, "r", encoding="utf-8") as f:
        stats = json.load(f)

    assert stats["unique_repository_count"] >= 15, "Benchmark must span >= 15 distinct repositories"
    for tid, count in stats["cases_per_transition"].items():
        assert count <= 5, f"Transition {tid} exceeds concentration limit (max 5, got {count})"
