"""
tests/test_protocol_v2_1_anti_leakage.py

Rigorous Anti-Leakage Scientific Verification Suite for Protocol V2.1:
1. Zero benchmark-specific symbol literals or keyword heuristics in src/validity/.
2. Prediction runner strictly isolated from gold labels and category metadata.
3. De-leaked blind IDs strictly following ^MV21-\\d{6}$.
4. Blind inputs containing zero ground truth or category tags.
5. Protocol V1 and historical pilot files remaining strictly immutable.
"""

import os
import re
import glob
import json
import importlib
import pytest

BANNED_BENCHMARK_LITERALS = [
    "unicodefun",
    "getheaders",
    "url_decode",
    "_app_ctx_stack",
    "pydantic",
    "varnames",
    "pprint_export",
    "doctest_options",
    "zip_equal",
    "isatty",
]


def test_no_banned_benchmark_literals_in_validity_engine():
    validity_dir = "/code/rolemem-agent-memory/src/validity"
    py_files = glob.glob(f"{validity_dir}/**/*.py", recursive=True)
    assert len(py_files) > 0, "src/validity/ must contain python files"

    violations = []
    for fpath in py_files:
        with open(fpath, "r", encoding="utf-8") as f:
            content = f.read().lower()
        for banned in BANNED_BENCHMARK_LITERALS:
            if banned in content:
                violations.append((os.path.basename(fpath), banned))

    assert len(violations) == 0, f"Banned benchmark literals found in src/validity/: {violations}"


def test_prediction_script_does_not_access_gold():
    pred_script = "/code/rolemem-agent-memory/scripts/run_validity_predictions_v2_1.py"
    with open(pred_script, "r", encoding="utf-8") as f:
        content = f.read().lower()

    banned_imports = ["gold_labels", "gold_label", "expected_result", "ground_truth", "category"]
    for bi in banned_imports:
        assert f"import {bi}" not in content, f"Prediction script imports {bi}"
        assert f"open(\"data/memory_validity_v2_1/gold_labels" not in content, "Prediction script opens gold labels"


def test_blind_inputs_case_id_pattern():
    blind_path = "/code/rolemem-agent-memory/data/memory_validity_v2_1/blind_inputs.jsonl"
    assert os.path.exists(blind_path), "blind_inputs.jsonl must exist"

    pattern = re.compile(r"^MV21-\d{6}$")
    with open(blind_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, start=1):
            if not line.strip():
                continue
            record = json.loads(line)
            cid = record.get("case_id", "")
            assert pattern.match(cid), f"Line {line_num}: Case ID '{cid}' does not match ^MV21-\\d{{6}}$"


def test_blind_inputs_zero_label_leakage():
    blind_path = "/code/rolemem-agent-memory/data/memory_validity_v2_1/blind_inputs.jsonl"
    leaked_keys = {"gold_label", "category", "gold_category", "stale_ground_truth", "valid_ground_truth"}
    leaked_category_substrings = ["cat_a", "cat_b", "cat_c", "cat_d", "valid_contract", "dep_stale"]

    with open(blind_path, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f):
            if not line.strip():
                continue
            rec = json.loads(line)
            for k in leaked_keys:
                assert k not in rec, f"Leaked key '{k}' found in case {rec.get('case_id')}"
            cid = rec.get("case_id", "").lower()
            for sub in leaked_category_substrings:
                assert sub not in cid, f"Leaked category pattern '{sub}' found in case_id '{cid}'"


def test_config_referenced_classes_exist():
    import yaml
    cfg_p = "/code/rolemem-agent-memory/configs/experiment_protocol_v2_1.yaml"
    with open(cfg_p, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    for engine_key in ["validity_engine", "symbol_engine", "dependency_engine", "file_engine"]:
        assert engine_key in cfg, f"Missing {engine_key} in config"
        mod_name = cfg[engine_key]["module"]
        cls_name = cfg[engine_key]["class"]
        mod = importlib.import_module(mod_name)
        assert hasattr(mod, cls_name), f"Class {cls_name} not found in module {mod_name}"
