"""
tests/test_protocol_v2_1_report_consistency.py

Verifies Single Source of Truth consistency across Protocol V2.1-R2 reports and JSON artifacts.
"""

import os
import json
import pytest

DATA_DIR = "/code/rolemem-agent-memory/data/memory_validity_v2_1"
EVAL_RESULTS_PATH = os.path.join(DATA_DIR, "evaluation_results.json")
BENCHMARK_STATS_PATH = os.path.join(DATA_DIR, "benchmark_stats.json")
MANIFEST_SUMMARY_PATH = "/code/rolemem-agent-memory/data/benchmark_v2_1/manifest_summary.json"

REPORT_SYMBOL_VALIDITY = "/code/rolemem-agent-memory/reports/symbol-validity-protocol-v2.1.md"
REPORT_READINESS = "/code/rolemem-agent-memory/reports/protocol-v2.1-readiness.md"
REPORT_CURATION = "/code/rolemem-agent-memory/reports/benchmark-curation-v2.1.md"
REPORT_HUMAN = "/code/rolemem-agent-memory/reports/human-annotation-status-v2.1.md"


def test_symbol_validity_report_consistency():
    assert os.path.exists(EVAL_RESULTS_PATH)
    assert os.path.exists(REPORT_SYMBOL_VALIDITY)

    with open(EVAL_RESULTS_PATH, "r", encoding="utf-8") as f:
        eval_data = json.load(f)

    with open(REPORT_SYMBOL_VALIDITY, "r", encoding="utf-8") as f:
        rep_content = f.read()

    total_cases = eval_data["benchmark_summary"]["total_cases"]
    valid_cases = eval_data["benchmark_summary"]["valid_cases"]
    stale_cases = eval_data["benchmark_summary"]["stale_cases"]

    assert f"Total Empirical Cases**: {total_cases}" in rep_content
    assert f"Valid Cases (True Negative for Stale)**: {valid_cases}" in rep_content
    assert f"Stale Cases (True Positive for Stale)**: {stale_cases}" in rep_content

    mechs = eval_data["mechanisms"]
    for mname, mdata in mechs.items():
        assert mname in rep_content


def test_readiness_report_consistency():
    assert os.path.exists(MANIFEST_SUMMARY_PATH)
    assert os.path.exists(REPORT_READINESS)

    with open(MANIFEST_SUMMARY_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    with open(REPORT_READINESS, "r", encoding="utf-8") as f:
        rep_content = f.read()

    assert "PROTOCOL_VERSION = 2.1-r3" in rep_content
    assert "ALGORITHM_FREEZE = NO" in rep_content
    assert "BENCHMARK_FREEZE = NO" in rep_content
    assert "HUMAN_VALIDATION = PENDING" in rep_content
    assert "FORMAL_AGENT_RESULTS = NO" in rep_content
    assert "FORMAL_PAPER_RESULTS = NO" in rep_content

    assert f"Total Evaluated Transitions**: {manifest['total_evaluated_transitions']}" in rep_content
    assert f"Core Benchmark Transitions**: {manifest['core_benchmark_count']}" in rep_content
    assert f"Control Benchmark Transitions**: {manifest['control_benchmark_count']}" in rep_content
    assert f"Rebuild Candidates**: {manifest['rebuild_candidate_count']}" in rep_content
    assert f"Excluded Transitions**: {manifest['excluded_count']}" in rep_content


def test_curation_report_consistency():
    assert os.path.exists(MANIFEST_SUMMARY_PATH)
    assert os.path.exists(REPORT_CURATION)

    with open(MANIFEST_SUMMARY_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    with open(REPORT_CURATION, "r", encoding="utf-8") as f:
        rep_content = f.read()

    assert "Protocol V2.1-R3" in rep_content
    assert f"Total Evaluated Transitions**: {manifest['total_evaluated_transitions']}" in rep_content
    assert f"Core Benchmark Candidates**: {manifest['core_benchmark_count']}" in rep_content
    assert f"Control Benchmark Candidates**: {manifest['control_benchmark_count']}" in rep_content


def test_human_annotation_report_pending():
    assert os.path.exists(REPORT_HUMAN)
    with open(REPORT_HUMAN, "r", encoding="utf-8") as f:
        rep_content = f.read()

    assert "PENDING" in rep_content
    assert "human_annotation_package_v2_1.jsonl" in rep_content
    assert "human_annotation_template_annotator_a.csv" in rep_content
    assert "human_annotation_template_annotator_b.csv" in rep_content
