"""
evaluation.py

Evaluation CLI Tool for RoleMem Benchmark:
Evaluates formal model predictions against sealed ground truth gold annotations.
Computes 3-class Accuracy, Macro-F1, Strict Track A, Compatible Track B, FIR, and SER.
"""

from __future__ import annotations
import argparse
import json
import os
import sys

from src.evaluation.metrics import evaluate_predictions


def main():
    parser = argparse.ArgumentParser(description="Evaluate RoleMem benchmark predictions against ground truth.")
    parser.add_argument("--predictions", "-p", type=str, default="results/predictions.jsonl", help="Path to predictions JSONL.")
    parser.add_argument("--gold", "-g", type=str, default="data/formal_v2_2/formal_gold_private.jsonl", help="Path to gold annotations JSONL.")
    parser.add_argument("--output", "-o", type=str, default="results/metrics.json", help="Path to output metrics JSON.")
    parser.add_argument("--track", "-t", type=str, default="all", choices=["strict", "compatible", "all"], help="Evaluation track.")
    args = parser.parse_args()

    if not os.path.exists(args.predictions):
        print(f"Error: Predictions file not found: {args.predictions}", file=sys.stderr)
        sys.exit(1)

    if not os.path.exists(args.gold):
        print(f"Error: Gold annotations file not found: {args.gold}", file=sys.stderr)
        sys.exit(1)

    predictions = []
    with open(args.predictions, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                predictions.append(json.loads(line))

    gold_annotations = []
    with open(args.gold, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                gold_annotations.append(json.loads(line))

    metrics = evaluate_predictions(predictions, gold_annotations, track=args.track)

    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    # Print clean summary table
    p3 = metrics.get("primary_3class", {})
    ta = metrics.get("track_a_strict", {})
    tb = metrics.get("track_b_compatible", {})
    risk = metrics.get("selective_risk_metrics", {})
    eff = metrics.get("operational_efficiency", {})

    print("\n" + "=" * 60)
    print("           RoleMem Benchmark Evaluation Report")
    print("=" * 60)
    print(f"Total Evaluated Cases   : {metrics.get('total_evaluated', 0)}")
    print(f"3-Class Accuracy        : {p3.get('accuracy', 0.0) * 100:.2f}%")
    print(f"3-Class Macro-F1        : {p3.get('macro_f1', 0.0) * 100:.2f}%")
    print(f"Track A (Strict) Acc/F1 : {ta.get('accuracy', 0.0) * 100:.2f}% / {ta.get('macro_f1', 0.0) * 100:.2f}%")
    print(f"Track B (Compat) Acc/F1 : {tb.get('accuracy', 0.0) * 100:.2f}% / {tb.get('macro_f1', 0.0) * 100:.2f}%")
    print(f"False Invalid Rate (FIR): {risk.get('false_invalid_rate_FIR', 0.0) * 100:.2f}%")
    print(f"Stale Escape Rate (SER) : {risk.get('stale_escape_rate_SER', 0.0) * 100:.2f}%")
    print(f"Avg Actions / Time      : {eff.get('avg_action_count', 0.0)} acts / {eff.get('avg_wall_time_sec', 0.0):.4f}s")
    print("=" * 60)
    print(f"Metrics written to: {args.output}\n")


if __name__ == "__main__":
    main()
