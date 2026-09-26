"""
scripts/analyze_errors.py

Phase S8 Error Analysis Tool:
Compares model predictions against ground truth gold annotations,
identifies false positive, false negative, and misclassified cases,
and outputs analysis/error_cases.json with root-cause diagnostic reasons.
"""

from __future__ import annotations
import json
import os
import sys
from collections import defaultdict

def main():
    inputs_file = "data/formal_v2_2/formal_inputs.jsonl"
    gold_file = "data/formal_v2_2/formal_gold_private.jsonl"
    preds_file = "experiments/exp001_full/predictions_rolemem.jsonl"
    case_map_file = "data/formal_v2_2/formal_case_map_private.json"
    output_file = "analysis/error_cases.json"

    with open(inputs_file, "r", encoding="utf-8") as f:
        inputs = {json.loads(line)["case_id"]: json.loads(line) for line in f if line.strip()}

    with open(gold_file, "r", encoding="utf-8") as f:
        gold = {json.loads(line)["case_id"]: json.loads(line) for line in f if line.strip()}

    with open(preds_file, "r", encoding="utf-8") as f:
        preds = {json.loads(line)["case_id"]: json.loads(line) for line in f if line.strip()}

    with open(case_map_file, "r", encoding="utf-8") as f:
        case_map = json.load(f)

    error_cases = []
    category_errors = defaultdict(list)
    confusion = defaultdict(lambda: defaultdict(int))

    for cid, g in gold.items():
        p = preds.get(cid, {})
        inp = inputs.get(cid, {})
        meta = case_map.get(cid, {})

        gold_label = g["gold_label"]
        pred_label = p.get("predicted_label", "UNKNOWN")
        claim_type = inp.get("claim_type", "UNKNOWN")

        confusion[gold_label][pred_label] += 1

        if gold_label != pred_label:
            # Diagnose root cause reason
            diag_reason = ""
            if claim_type == "DEFAULT_VALUE" and gold_label == "VALID" and pred_label == "STALE":
                diag_reason = "Slot mismatch: parameter_or_attr key in structured_claim was unmapped to parameter_name, causing default validator to search for empty parameter."
            elif claim_type == "BEHAVIORAL_CONTRACT" and gold_label == "VALID" and pred_label != "VALID":
                diag_reason = "Dynamic test execution artifact unattached in pure static mode; needs static test-assertion witness binding."
            elif claim_type == "DEPRECATION_STATUS" and gold_label == "VALID" and pred_label != "VALID":
                diag_reason = "is_deprecated boolean unmapped to expected_status object ('active'/'deprecated'), yielding inconclusive deprecation."
            elif claim_type == "DEPENDENCY_CONTRACT" and gold_label == "VALID" and pred_label != "VALID":
                diag_reason = "Packaging dependency manifest parsing uninvoked on package_name subject."
            elif gold_label == "PARTIALLY_VALID" and pred_label != "PARTIALLY_VALID":
                diag_reason = "Signature widening / optional parameter extension was not mapped to PARTIALLY_VALID state."
            else:
                diag_reason = f"Grounding/escalation mismatch for {claim_type}: gold={gold_label}, pred={pred_label}."

            err_entry = {
                "case_id": cid,
                "claim_type": claim_type,
                "repository": inp.get("repository_name", ""),
                "claim": inp.get("raw_statement", ""),
                "structured_claim": inp.get("structured_claim", {}),
                "gold_label": gold_label,
                "prediction": pred_label,
                "gold_justification": g.get("justification_note", ""),
                "decision_reason": diag_reason,
                "evidence_path": meta.get("base_evidence_path", "")
            }
            error_cases.append(err_entry)
            category_errors[claim_type].append(err_entry)

    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({
            "total_evaluated": len(gold),
            "total_errors": len(error_cases),
            "accuracy": (len(gold) - len(error_cases)) / len(gold),
            "confusion_matrix": {k: dict(v) for k, v in confusion.items()},
            "error_counts_by_claim_type": {k: len(v) for k, v in category_errors.items()},
            "error_cases": error_cases
        }, f, indent=2)

    print("\n" + "=" * 60)
    print("           RoleMem Error Analysis Summary")
    print("=" * 60)
    print(f"Total Cases     : {len(gold)}")
    print(f"Total Errors    : {len(error_cases)} ({len(error_cases)/len(gold)*100:.1f}%)")
    print("\nError Breakdown by Claim Type:")
    for ct, errs in category_errors.items():
        print(f"  - {ct:22s}: {len(errs)} errors")
    print("\nConfusion Matrix:")
    for g_lbl in ["VALID", "STALE", "PARTIALLY_VALID"]:
        row = [f"{p_lbl}:{confusion[g_lbl][p_lbl]}" for p_lbl in ["VALID", "STALE", "PARTIALLY_VALID", "UNCERTAIN"]]
        print(f"  Gold {g_lbl:15s} -> {', '.join(row)}")
    print("=" * 60)
    print(f"Detailed error cases written to: {output_file}\n")


if __name__ == "__main__":
    main()
