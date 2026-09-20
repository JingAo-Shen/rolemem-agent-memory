#!/usr/bin/env python3
"""
scripts/score_validity_predictions_v2_1.py

Strict Phase 2 Scoring Runner for Protocol V2.1:
- Loads gold_labels.jsonl and predictions_<mech>.jsonl.
- Computes standard metrics: Accuracy, Precision, Recall, F1, False Invalidation Rate (FIR), Stale Exposure Rate (SER).
- Computes per-category granular breakdown (Cat A, B, C, D).
- Outputs data/memory_validity_v2_1/evaluation_results.json.
"""

import os
import sys
import json
from typing import Dict, Any, List

sys.path.insert(0, "/code/rolemem-agent-memory")

DATA_DIR = "/code/rolemem-agent-memory/data/memory_validity_v2_1"
GOLD_LABELS_PATH = os.path.join(DATA_DIR, "gold_labels.jsonl")
OUT_JSON = os.path.join(DATA_DIR, "evaluation_results.json")


def score_predictions():
    print(f"Loading gold ground truth from: {GOLD_LABELS_PATH}")
    with open(GOLD_LABELS_PATH, "r", encoding="utf-8") as f:
        gold_list = [json.loads(line) for line in f if line.strip()]

    gold_map = {g["case_id"]: g for g in gold_list}
    total_cases = len(gold_list)

    valid_cases = sum(1 for g in gold_list if g["gold_label"] == "VALID")
    stale_cases = sum(1 for g in gold_list if g["gold_label"] == "STALE")

    cat_counts = {}
    for g in gold_list:
        c = g["category"]
        cat_counts[c] = cat_counts.get(c, 0) + 1

    mechanisms = [
        ("File_Level_Baseline", "predictions_file.jsonl"),
        ("Pure_Symbol_AST_Baseline", "predictions_symbol.jsonl"),
        ("Dependency_Validity_Baseline", "predictions_dependency.jsonl"),
        ("RoleMem_Validity_Engine", "predictions_rolemem.jsonl"),
        ("RoleMem_Validity_Engine_Abstain", "predictions_rolemem_abstain.jsonl"),
    ]

    mech_results = {}

    for mname, pred_file in mechanisms:
        pred_path = os.path.join(DATA_DIR, pred_file)
        if not os.path.exists(pred_path):
            print(f"Warning: {pred_path} does not exist. Skipping.")
            continue

        with open(pred_path, "r", encoding="utf-8") as f:
            preds = [json.loads(line) for line in f if line.strip()]

        tp = tn = fp = fn = abstain = 0
        cat_correct = {cat: 0 for cat in cat_counts}
        cat_total = {cat: 0 for cat in cat_counts}

        for p in preds:
            cid = p["case_id"]
            if cid not in gold_map:
                continue
            g = gold_map[cid]
            gold = g["gold_label"]  # "VALID" or "STALE"
            cat = g["category"]
            pred = p["prediction"]  # "VALID", "STALE", or "ABSTAIN"

            cat_total[cat] += 1

            if pred == "ABSTAIN":
                abstain += 1
                continue

            # In binary validity classification:
            # Positive class = STALE (Memory needs invalidation)
            # Negative class = VALID (Memory is valid/reusable)
            if gold == "STALE" and pred == "STALE":
                tp += 1
                cat_correct[cat] += 1
            elif gold == "VALID" and pred == "VALID":
                tn += 1
                cat_correct[cat] += 1
            elif gold == "VALID" and pred == "STALE":
                fp += 1  # False Invalidation
            elif gold == "STALE" and pred == "VALID":
                fn += 1  # Stale Exposure

        decided = tp + tn + fp + fn
        coverage = decided / total_cases if total_cases > 0 else 0.0
        acc_decided = (tp + tn) / decided if decided > 0 else 0.0
        acc_overall = (tp + tn) / total_cases if total_cases > 0 else 0.0

        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0

        fir = fp / (tn + fp) if (tn + fp) > 0 else 0.0
        ser = fn / (tp + fn) if (tp + fn) > 0 else 0.0
        vmr = tn / (tn + fp) if (tn + fp) > 0 else 0.0
        smr = tp / (tp + fn) if (tp + fn) > 0 else 0.0

        per_cat_acc = {}
        for cat in sorted(cat_counts):
            tot = cat_total[cat]
            cor = cat_correct[cat]
            per_cat_acc[cat] = (cor / tot) if tot > 0 else 0.0

        mech_results[mname] = {
            "TP": tp,
            "TN": tn,
            "FP": fp,
            "FN": fn,
            "ABSTAIN": abstain,
            "Coverage": coverage,
            "Accuracy_Decided": acc_decided,
            "Accuracy_Overall": acc_overall,
            "Precision": prec,
            "Recall": rec,
            "F1": f1,
            "False_Invalidation_Rate_FIR": fir,
            "Stale_Exposure_Rate_SER": ser,
            "Valid_Memory_Recall": vmr,
            "Stale_Memory_Recall": smr,
            "Per_Category_Accuracy": per_cat_acc
        }

    out_data = {
        "benchmark_summary": {
            "protocol_version": "2.1",
            "total_cases": total_cases,
            "valid_cases": valid_cases,
            "stale_cases": stale_cases,
            "category_distribution": cat_counts
        },
        "mechanisms": mech_results
    }

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(out_data, f, indent=2)

    print(f"=== Scoring Complete ===")
    print(f"  Saved evaluation results to: {OUT_JSON}")
    for mname, res in mech_results.items():
        print(f"  - {mname}: Acc={res['Accuracy_Overall']*100:.1f}%, F1={res['F1']*100:.1f}%, FIR={res['False_Invalidation_Rate_FIR']*100:.1f}%, SER={res['Stale_Exposure_Rate_SER']*100:.1f}%")


if __name__ == "__main__":
    score_predictions()
