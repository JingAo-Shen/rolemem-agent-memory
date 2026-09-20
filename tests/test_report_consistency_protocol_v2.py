"""
tests/test_report_consistency_protocol_v2.py

Rigorously verifies Single Source of Truth consistency for Protocol V2:
- Blind inputs data integrity and zero label leakage
- Evaluation results correctness across 126 grounded test cases
- Benchmark V2 manifest integrity (15 Core, 4 Control, 3 Rebuild, 8 Excluded)
- Exact concordance between JSON artifacts and generated markdown reports
- Protocol V2 experiment configuration validity
"""

import os
import re
import json
import yaml
import pytest


def test_blind_inputs_data_integrity():
    blind_path = "/code/rolemem-agent-memory/data/memory_validity_v2/blind_inputs.jsonl"
    assert os.path.exists(blind_path), "blind_inputs.jsonl must exist"

    with open(blind_path, "r", encoding="utf-8") as f:
        records = [json.loads(line) for line in f if line.strip()]

    assert len(records) == 126, f"Expected 126 blind inputs, got {len(records)}"

    leaked_keys = {"gold_label", "category", "gold_category", "stale_ground_truth", "valid_ground_truth"}
    for idx, r in enumerate(records):
        assert "case_id" in r
        assert "repository" in r
        assert "base_commit" in r
        assert "target_commit" in r
        assert "file_path" in r
        assert "symbol_qualified_name" in r
        assert "base_source_excerpt" in r
        assert "diff_hunk" in r
        assert "memory_statement" in r

        # Check for zero mock data
        assert len(r["base_commit"]) == 40, f"base_commit must be 40-char SHA: {r['base_commit']}"
        assert len(r["target_commit"]) == 40, f"target_commit must be 40-char SHA: {r['target_commit']}"
        assert "mock" not in r["base_commit"].lower()
        assert "dummy" not in r["base_commit"].lower()
        assert "head~" not in r["base_commit"].lower()

        # Check for zero label leakage
        for lk in leaked_keys:
            assert lk not in r, f"Leaked key {lk} found in blind input case {r['case_id']}"


def test_gold_labels_structure():
    gold_path = "/code/rolemem-agent-memory/data/memory_validity_v2/gold_labels.jsonl"
    assert os.path.exists(gold_path), "gold_labels.jsonl must exist"

    with open(gold_path, "r", encoding="utf-8") as f:
        records = [json.loads(line) for line in f if line.strip()]

    assert len(records) == 126, f"Expected 126 gold labels, got {len(records)}"

    valid_cats = {
        "CAT_A_FILE_CHG_SYM_SAME_VALID",
        "CAT_B_SYM_CHG_MEMORY_VALID",
        "CAT_C_SYM_SAME_MEMORY_STALE",
        "CAT_D_SYM_CHG_OR_REM_STALE"
    }

    for r in records:
        assert r["gold_label"] in ("VALID", "STALE")
        assert r["category"] in valid_cats


def test_evaluation_results_and_report_concordance():
    eval_path = "/code/rolemem-agent-memory/data/memory_validity_v2/evaluation_results.json"
    assert os.path.exists(eval_path), "evaluation_results.json must exist"

    with open(eval_path, "r", encoding="utf-8") as f:
        eval_data = json.load(f)

    bench = eval_data["benchmark_summary"]
    assert bench["total_cases"] == 126
    assert bench["valid_cases"] == 65
    assert bench["stale_cases"] == 61
    assert bench["valid_cases"] + bench["stale_cases"] == 126

    report_path = "/code/rolemem-agent-memory/reports/symbol-validity-protocol-v2.md"
    assert os.path.exists(report_path), "symbol-validity-protocol-v2.md must exist"

    with open(report_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "**Total Empirical Cases**: 126" in content
    assert "**Valid Cases (True Negative for Stale)**: 65" in content
    assert "**Stale Cases (True Positive for Stale)**: 61" in content

    # Check that each mechanism metrics appear accurately in report
    for mname, mdata in eval_data["mechanisms"].items():
        acc_str = f"{mdata['Accuracy_Overall']*100:.1f}%"
        assert acc_str in content, f"Accuracy {acc_str} for {mname} not in report"


def test_benchmark_v2_manifests_integrity():
    manifest_summary_path = "/code/rolemem-agent-memory/data/benchmark_v2/manifest_summary.json"
    assert os.path.exists(manifest_summary_path), "manifest_summary.json must exist"

    with open(manifest_summary_path, "r", encoding="utf-8") as f:
        summary = json.load(f)

    assert summary["core_benchmark_count"] == 15
    assert summary["control_benchmark_count"] == 4
    assert summary["rebuild_candidate_count"] == 3
    assert summary["excluded_count"] == 8
    assert summary["total_evaluated_transitions"] == 30
    assert summary["distinct_repositories_core"] == 14

    # Check individual jsonl files
    core_file = "/code/rolemem-agent-memory/data/benchmark_v2/track_a_core.jsonl"
    with open(core_file, "r", encoding="utf-8") as f:
        core_records = [json.loads(line) for line in f if line.strip()]
    assert len(core_records) == 15

    for cr in core_records:
        assert len(cr["base_commit"]) == 40
        assert len(cr["target_commit"]) == 40
        assert cr["benchmark_role"] == "CORE"


def test_author_audit_report_concordance():
    audit_jsonl = "/code/rolemem-agent-memory/data/memory_validity_v2/author_audit.jsonl"
    assert os.path.exists(audit_jsonl), "author_audit.jsonl must exist"

    with open(audit_jsonl, "r", encoding="utf-8") as f:
        audit_records = [json.loads(line) for line in f if line.strip()]

    assert len(audit_records) == 30

    report_path = "/code/rolemem-agent-memory/reports/human-annotation-author-audit.md"
    assert os.path.exists(report_path), "human-annotation-author-audit.md must exist"

    with open(report_path, "r", encoding="utf-8") as f:
        content = f.read()

    agreed = sum(1 for r in audit_records if r.get("audit_label") == r.get("gold_label"))
    assert f"**Sample Size**: {len(audit_records)}" in content
    assert f"**Concordance with Gold Ground Truth**: {agreed}/{len(audit_records)}" in content
    assert "AUTHOR_AUDIT" in content


def test_experiment_config_protocol_v2():
    config_path = "/code/rolemem-agent-memory/configs/experiment_protocol_v2.yaml"
    assert os.path.exists(config_path), "experiment_protocol_v2.yaml must exist"

    with open(config_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    assert cfg["protocol_version"] == "2.0.0"
    assert cfg["token_budget"]["total_context_limit"] == 2048

    breakdown = cfg["token_budget"]["breakdown"]
    total_alloc = sum(breakdown.values())
    assert total_alloc <= 2048

    conditions = cfg["conditions"]
    expected_conditions = ["B0", "B1", "B3", "B4", "F", "A2", "A3"]
    for c in expected_conditions:
        assert c in conditions, f"Condition {c} must be defined in config"
