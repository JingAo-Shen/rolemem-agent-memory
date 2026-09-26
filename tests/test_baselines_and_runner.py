"""
tests/test_baselines_and_runner.py

Unit and integration tests for Phase S7 baseline models and benchmark runner:
- Baseline-1 (Majority)
- Baseline-2 (Static AST)
- Baseline-3 (Naive RAG)
- Metrics calculation (Accuracy, Macro-F1, Strict Track A, Compatible Track B, FIR, SER)
- BenchmarkRunner end-to-end execution
"""

import pytest
import os
import json
import tempfile

from src.baselines.majority import MajorityBaselinePredictor
from src.baselines.static_ast import StaticASTBaselinePredictor
from src.baselines.naive_rag import NaiveRAGBaselinePredictor
from src.evaluation.metrics import evaluate_predictions, compute_per_class_metrics, compute_confusion_matrix
from src.benchmark_runner import BenchmarkRunner


def test_majority_baseline():
    """Verify Majority predictor always returns VALID."""
    pred = MajorityBaselinePredictor()
    res = pred.predict({"case_id": "TEST-01"})
    assert res["predicted_label"] == "VALID"
    assert res["action_count"] == 0
    assert res["escalation_tier"] == "TIER_0_STATIC_AST"


def test_static_ast_baseline():
    """Verify Static AST baseline behavior."""
    pred = StaticASTBaselinePredictor()
    res = pred.predict(
        {"case_id": "TEST-02", "structured_claim": {"symbol": "non_existent_func_xyz"}, "repository_name": "test/repo"},
        {"target_commit": "123", "base_evidence_path": "fake.py"}
    )
    assert res["predicted_label"] == "STALE"
    assert res["action_count"] == 1


def test_naive_rag_baseline():
    """Verify Naive RAG baseline token overlap logic."""
    pred = NaiveRAGBaselinePredictor()
    res = pred.predict(
        {"case_id": "TEST-03", "raw_statement": "some random statement", "structured_claim": {}, "repository_name": "test/repo"},
        {"target_commit": "123", "base_evidence_path": "fake.py"}
    )
    assert res["predicted_label"] == "STALE"
    assert res["action_count"] == 2


def test_metrics_evaluation():
    """Verify evaluation metric calculations with known gold/pred pairs."""
    gold = [
        {"case_id": "C1", "gold_label": "VALID"},
        {"case_id": "C2", "gold_label": "STALE"},
        {"case_id": "C3", "gold_label": "PARTIALLY_VALID"},
        {"case_id": "C4", "gold_label": "VALID"}
    ]
    preds = [
        {"case_id": "C1", "predicted_label": "VALID", "action_count": 0, "execution_wall_time_sec": 0.01},
        {"case_id": "C2", "predicted_label": "STALE", "action_count": 1, "execution_wall_time_sec": 0.02},
        {"case_id": "C3", "predicted_label": "PARTIALLY_VALID", "action_count": 2, "execution_wall_time_sec": 0.03},
        {"case_id": "C4", "predicted_label": "STALE", "action_count": 0, "execution_wall_time_sec": 0.01}
    ]
    metrics = evaluate_predictions(preds, gold)
    assert metrics["total_evaluated"] == 4
    assert metrics["primary_3class"]["accuracy"] == 0.75
    assert metrics["selective_risk_metrics"]["false_invalid_rate_FIR"] == 0.5  # 1 false stale out of 2 valid
    assert metrics["selective_risk_metrics"]["stale_escape_rate_SER"] == 0.0


def test_benchmark_runner_sanity():
    """Verify benchmark runner runs across models on limited set without error."""
    with tempfile.TemporaryDirectory() as tmpdir:
        runner = BenchmarkRunner(output_dir=tmpdir)
        metrics = runner.execute_all(methods=["majority", "static_ast"], limit=3, track="strict")
        assert "majority" in metrics
        assert "static_ast" in metrics
        assert os.path.exists(os.path.join(tmpdir, "metrics.json"))
        assert os.path.exists(os.path.join(tmpdir, "predictions_majority.jsonl"))
        assert os.path.exists(os.path.join(tmpdir, "retrieval_trace.json"))
