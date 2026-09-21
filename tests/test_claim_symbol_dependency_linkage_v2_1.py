"""
tests/test_claim_symbol_dependency_linkage_v2_1.py

Verifies rigorous semantic and causal linkage across:
- Memory claim, target symbol, dependency, and execution evidence.
- Protocol V2.1-R3 requirements for Cat B, Cat C, and Cat D2.
"""

import os
import json
import pytest
from src.validity.dependency_graph import DependencyGraphVerifier

DATA_DIR = "/code/rolemem-agent-memory/data/memory_validity_v2_1"
GOLD_PATH = os.path.join(DATA_DIR, "gold_labels.jsonl")
BLIND_PATH = os.path.join(DATA_DIR, "blind_inputs.jsonl")
CONTRACTS_DIR = os.path.join(DATA_DIR, "contracts")
COUNTERFACTUALS_DIR = os.path.join(DATA_DIR, "counterfactuals")
BEHAVIOR_BREAKS_DIR = os.path.join(DATA_DIR, "behavior_breaks")


def load_gold_records():
    with open(GOLD_PATH, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def test_cat_b_claim_contract_linkage():
    records = load_gold_records()
    cat_b = [r for r in records if r["category"] == "CAT_B_SYM_CHG_MEMORY_VALID"]
    assert len(cat_b) >= 8, f"Expected at least 8 Cat B cases, got {len(cat_b)}"

    for r in cat_b:
        cid = r["case_id"]
        cpath = os.path.join(CONTRACTS_DIR, f"{cid}.json")
        assert os.path.exists(cpath), f"Contract artifact {cpath} missing"

        with open(cpath, "r", encoding="utf-8") as f:
            cdata = json.load(f)

        assert cdata.get("claim_contract_linked") is True, f"Case {cid} claim_contract_linked is not True"
        assert len(cdata.get("contract_assertions", [])) > 0, f"Case {cid} missing contract_assertions"
        assert cdata["base_execution"]["passed"] is True, f"Case {cid} base execution did not pass"
        assert cdata["target_execution"]["passed"] is True, f"Case {cid} target execution did not pass"
        assert cdata.get("machine_verified") is True


def test_cat_c_dependency_linkage():
    records = load_gold_records()
    cat_c = [r for r in records if r["category"] == "CAT_C_SYM_SAME_MEMORY_STALE"]
    assert len(cat_c) >= 1, "Cat C must contain at least 1 verified case"

    for r in cat_c:
        cid = r["case_id"]
        cfpath = os.path.join(COUNTERFACTUALS_DIR, f"{cid}.json")
        assert os.path.exists(cfpath), f"Counterfactual artifact {cfpath} missing"

        with open(cfpath, "r", encoding="utf-8") as f:
            cfdata = json.load(f)

        assert cfdata.get("linkage_verified") is True, f"Case {cid} linkage_verified is False"
        assert len(cfdata.get("dependency_path", [])) >= 2, f"Case {cid} dependency_path invalid"
        assert cfdata.get("symbol_digest_equal") is True
        assert cfdata["old_on_base"]["passed"] is True, f"Case {cid} old_on_base failed"
        assert cfdata["old_on_target"]["passed"] is False, f"Case {cid} old_on_target passed (should break)"
        assert cfdata["new_on_target"]["passed"] is True, f"Case {cid} new_on_target failed"
        assert cfdata.get("machine_verified") is True


def test_cat_d2_behavior_breaks():
    records = load_gold_records()
    cat_d2 = [r for r in records if r["category"] == "CAT_D2_SYM_CHG_BEHAVIOR_STALE"]
    assert len(cat_d2) >= 8, f"Expected at least 8 Cat D2 cases, got {len(cat_d2)}"

    for r in cat_d2:
        cid = r["case_id"]
        bbpath = os.path.join(BEHAVIOR_BREAKS_DIR, f"{cid}.json")
        assert os.path.exists(bbpath), f"Behavior break artifact {bbpath} missing"

        with open(bbpath, "r", encoding="utf-8") as f:
            bbdata = json.load(f)

        assert bbdata.get("break_verified") is True
        assert bbdata["base_execution"]["passed"] is True, f"Case {cid} base execution did not pass"
        assert bbdata["target_execution"]["passed"] is False, f"Case {cid} target execution passed (should break)"


def test_dependency_graph_verifier_unit():
    pluggy_src = """
class HookSpec:
    def __init__(self, hook):
        self.varnames = varnames(hook)
"""
    dep_src = """
def varnames(func):
    return func.__code__.co_varnames
"""
    verifier = DependencyGraphVerifier()
    res = verifier.verify_linkage(pluggy_src, "HookSpec", "varnames")
    assert res.linkage_verified is True
    assert res.path == ["HookSpec", "varnames"]
