r"""
src/evaluation/metrics.py

Evaluation Metrics Calculation for RoleMem Temporal Consistency Benchmark:
Implements Accuracy, Macro-F1, Per-Class F1, Confusion Matrix, Track A (Strict),
Track B (Compatible), and Selective Risk / Coverage (FIR, SER).
Conforms strictly to data/formal_v2_2/evaluation_protocol.json specification.
"""

from __future__ import annotations
from typing import Dict, Any, List, Optional, Tuple, Set
from collections import defaultdict


def compute_per_class_metrics(
    y_true: List[str],
    y_pred: List[str],
    classes: List[str]
) -> Dict[str, Dict[str, float]]:
    """Compute precision, recall, and F1 for each class."""
    metrics = {}
    for c in classes:
        tp = sum(1 for yt, yp in zip(y_true, y_pred) if yt == c and yp == c)
        fp = sum(1 for yt, yp in zip(y_true, y_pred) if yt != c and yp == c)
        fn = sum(1 for yt, yp in zip(y_true, y_pred) if yt == c and yp != c)

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

        metrics[c] = {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "support": sum(1 for yt in y_true if yt == c)
        }
    return metrics


def compute_confusion_matrix(
    y_true: List[str],
    y_pred: List[str],
    classes: List[str]
) -> Dict[str, Dict[str, int]]:
    """Generate NxN confusion matrix: matrix[gold_label][predicted_label]."""
    matrix: Dict[str, Dict[str, int]] = {c: {p: 0 for p in classes} for c in classes}
    for yt, yp in zip(y_true, y_pred):
        if yt in matrix and yp in matrix[yt]:
            matrix[yt][yp] += 1
    return matrix


def evaluate_predictions(
    predictions: List[Dict[str, Any]],
    gold_annotations: List[Dict[str, Any]],
    track: str = "all"
) -> Dict[str, Any]:
    """
    Evaluate list of prediction records against list of gold annotation records.
    Computes 3-class primary metrics, Track A (Strict), Track B (Compatible), and Selective Risk metrics.
    """
    gold_map = {g["case_id"]: g["gold_label"] for g in gold_annotations}
    pred_map = {p["case_id"]: p["predicted_label"] for p in predictions}

    common_ids = [cid for cid in pred_map if cid in gold_map]
    total_evaluated = len(common_ids)
    if total_evaluated == 0:
        return {"error": "Zero matching cases between predictions and gold annotations."}

    y_true = [gold_map[cid] for cid in common_ids]
    y_pred = [pred_map[cid] for cid in common_ids]

    classes_3 = ["VALID", "STALE", "PARTIALLY_VALID"]

    # 1. 3-Class Primary Metrics
    correct = sum(1 for yt, yp in zip(y_true, y_pred) if yt == yp)
    accuracy = correct / total_evaluated

    per_class_3 = compute_per_class_metrics(y_true, y_pred, classes_3)
    present_classes = [c for c in classes_3 if per_class_3[c]["support"] > 0]
    macro_f1 = sum(per_class_3[c]["f1"] for c in present_classes) / max(1, len(present_classes))
    confusion_3 = compute_confusion_matrix(y_true, y_pred, classes_3)

    # 2. Track A: Strict (PARTIALLY_VALID -> STALE)
    y_true_strict = ["STALE" if yt == "PARTIALLY_VALID" else yt for yt in y_true]
    y_pred_strict = ["STALE" if yp == "PARTIALLY_VALID" else yp for yp in y_pred]
    correct_strict = sum(1 for yt, yp in zip(y_true_strict, y_pred_strict) if yt == yp)
    accuracy_strict = correct_strict / total_evaluated
    per_class_strict = compute_per_class_metrics(y_true_strict, y_pred_strict, ["VALID", "STALE"])
    macro_f1_strict = (per_class_strict["VALID"]["f1"] + per_class_strict["STALE"]["f1"]) / 2.0

    # 3. Track B: Compatible (PARTIALLY_VALID -> VALID)
    y_true_compat = ["VALID" if yt == "PARTIALLY_VALID" else yt for yt in y_true]
    y_pred_compat = ["VALID" if yp == "PARTIALLY_VALID" else yp for yp in y_pred]
    correct_compat = sum(1 for yt, yp in zip(y_true_compat, y_pred_compat) if yt == yp)
    accuracy_compat = correct_compat / total_evaluated
    per_class_compat = compute_per_class_metrics(y_true_compat, y_pred_compat, ["VALID", "STALE"])
    macro_f1_compat = (per_class_compat["VALID"]["f1"] + per_class_compat["STALE"]["f1"]) / 2.0

    # 4. Selective Classification & Risk Metrics
    # False Invalid Rate (FIR) = False STALE / Total Actual VALID
    total_actual_valid = sum(1 for yt in y_true if yt == "VALID")
    false_stale = sum(1 for yt, yp in zip(y_true, y_pred) if yt == "VALID" and yp == "STALE")
    fir = false_stale / total_actual_valid if total_actual_valid > 0 else 0.0

    # Stale Escape Rate (SER) = False VALID / Total Actual STALE
    total_actual_stale = sum(1 for yt in y_true if yt == "STALE")
    false_valid = sum(1 for yt, yp in zip(y_true, y_pred) if yt == "STALE" and yp == "VALID")
    ser = false_valid / total_actual_stale if total_actual_stale > 0 else 0.0

    # Decided & Coverage
    decided_count = sum(1 for yp in y_pred if yp in ("VALID", "STALE", "PARTIALLY_VALID"))
    coverage = decided_count / total_evaluated
    selective_risk = (total_evaluated - correct) / max(1, decided_count)

    # Average tool action cost and execution time
    avg_actions = sum(p.get("action_count", 0) for p in predictions) / total_evaluated
    avg_wall_time = sum(p.get("execution_wall_time_sec", 0.0) for p in predictions) / total_evaluated

    return {
        "total_evaluated": total_evaluated,
        "primary_3class": {
            "accuracy": round(accuracy, 4),
            "macro_f1": round(macro_f1, 4),
            "per_class": per_class_3,
            "confusion_matrix": confusion_3
        },
        "track_a_strict": {
            "accuracy": round(accuracy_strict, 4),
            "macro_f1": round(macro_f1_strict, 4),
            "per_class": per_class_strict
        },
        "track_b_compatible": {
            "accuracy": round(accuracy_compat, 4),
            "macro_f1": round(macro_f1_compat, 4),
            "per_class": per_class_compat
        },
        "selective_risk_metrics": {
            "coverage": round(coverage, 4),
            "selective_risk": round(selective_risk, 4),
            "false_invalid_rate_FIR": round(fir, 4),
            "stale_escape_rate_SER": round(ser, 4)
        },
        "operational_efficiency": {
            "avg_action_count": round(avg_actions, 2),
            "avg_wall_time_sec": round(avg_wall_time, 4)
        }
    }
