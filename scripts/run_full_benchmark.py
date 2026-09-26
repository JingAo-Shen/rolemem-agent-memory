"""
scripts/run_full_benchmark.py

Full Benchmark Evaluation Pipeline for RoleMem:
Runs all 150 benchmark cases across RoleMem and baselines (Majority, Static AST, Naive RAG),
generates complete experimental metrics, comparison table, and claim-type breakdown.
"""

from __future__ import annotations
import argparse
import json
import os
import sys
import time
from typing import Dict, Any, List, Optional

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.benchmark_runner import BenchmarkRunner
from src.evaluation.metrics import evaluate_predictions, compute_per_class_metrics


def categorize_claim_type(raw_type: str) -> str:
    """Map fine-grained benchmark claim type to 5 primary experimental categories."""
    raw = raw_type.upper().strip()
    if raw in ("SIGNATURE_COMPATIBLE", "SIGNATURE"):
        return "SIGNATURE"
    elif raw in ("DEFAULT_VALUE", "DEFAULT"):
        return "DEFAULT"
    elif raw in ("BEHAVIORAL_CONTRACT", "BEHAVIOR", "RETURN_VALUE"):
        return "BEHAVIOR"
    elif raw in ("DEPENDENCY_CONTRACT", "DEPENDENCY"):
        return "DEPENDENCY"
    elif raw in ("DEPRECATION_STATUS", "CONFIG", "CONFIG_FLAG"):
        return "CONFIG"
    else:
        return "CONFIG"


def compute_claim_type_analysis(
    inputs: List[Dict[str, Any]],
    gold_annotations: List[Dict[str, Any]],
    all_predictions: Dict[str, List[Dict[str, Any]]]
) -> Dict[str, Any]:
    """
    Compute fine-grained accuracy and Macro-F1 across claim types for all models.
    """
    case_types = {c["case_id"]: c.get("claim_type", "UNKNOWN") for c in inputs}
    case_cats = {c["case_id"]: categorize_claim_type(c.get("claim_type", "UNKNOWN")) for c in inputs}

    categories = ["SIGNATURE", "DEFAULT", "BEHAVIOR", "DEPENDENCY", "CONFIG"]
    fine_types = sorted(list({c.get("claim_type", "UNKNOWN") for c in inputs}))

    analysis: Dict[str, Any] = {
        "by_category": {},
        "by_fine_grained_type": {},
        "category_case_counts": {}
    }

    # Count category distributions
    for cat in categories:
        cids = [cid for cid, ccat in case_cats.items() if ccat == cat]
        gold_sub = [g for g in gold_annotations if g["case_id"] in cids]
        analysis["category_case_counts"][cat] = {
            "total_cases": len(cids),
            "valid_cases": sum(1 for g in gold_sub if g["gold_label"] == "VALID"),
            "stale_cases": sum(1 for g in gold_sub if g["gold_label"] == "STALE"),
            "partially_valid_cases": sum(1 for g in gold_sub if g["gold_label"] == "PARTIALLY_VALID"),
        }

    # Compute per-model per-category metrics
    for cat in categories:
        cat_cids = {cid for cid, ccat in case_cats.items() if ccat == cat}
        gold_sub = [g for g in gold_annotations if g["case_id"] in cat_cids]
        analysis["by_category"][cat] = {}

        for method, preds in all_predictions.items():
            preds_sub = [p for p in preds if p["case_id"] in cat_cids]
            m_res = evaluate_predictions(preds_sub, gold_sub)
            p3 = m_res.get("primary_3class", {})
            ta = m_res.get("track_a_strict", {})
            tb = m_res.get("track_b_compatible", {})

            analysis["by_category"][cat][method] = {
                "total_cases": len(preds_sub),
                "accuracy": p3.get("accuracy", 0.0),
                "macro_f1": p3.get("macro_f1", 0.0),
                "track_a_strict_accuracy": ta.get("accuracy", 0.0),
                "track_a_strict_macro_f1": ta.get("macro_f1", 0.0),
                "track_b_compatible_accuracy": tb.get("accuracy", 0.0),
                "track_b_compatible_macro_f1": tb.get("macro_f1", 0.0),
                "per_class": p3.get("per_class", {})
            }

    # Compute per-model per-fine-grained-type metrics
    for ftype in fine_types:
        ftype_cids = {cid for cid, ft in case_types.items() if ft == ftype}
        gold_sub = [g for g in gold_annotations if g["case_id"] in ftype_cids]
        analysis["by_fine_grained_type"][ftype] = {}

        for method, preds in all_predictions.items():
            preds_sub = [p for p in preds if p["case_id"] in ftype_cids]
            m_res = evaluate_predictions(preds_sub, gold_sub)
            p3 = m_res.get("primary_3class", {})
            ta = m_res.get("track_a_strict", {})

            analysis["by_fine_grained_type"][ftype][method] = {
                "total_cases": len(preds_sub),
                "accuracy": p3.get("accuracy", 0.0),
                "macro_f1": p3.get("macro_f1", 0.0),
                "track_a_strict_accuracy": ta.get("accuracy", 0.0),
                "track_a_strict_macro_f1": ta.get("macro_f1", 0.0)
            }

    return analysis


def generate_comparison_table_data(
    all_metrics: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Generate structured comparison table data for export."""
    display_order = ["majority", "static_ast", "naive_rag", "rolemem"]
    method_labels = {
        "majority": "Baseline-1: Majority",
        "static_ast": "Baseline-2: Static AST Checker",
        "naive_rag": "Baseline-3: Naive RAG",
        "rolemem": "RoleMem (Ours)"
    }

    table_rows = []
    for m_key in display_order:
        if m_key not in all_metrics:
            continue
        m = all_metrics[m_key]
        p3 = m.get("primary_3class", {})
        ta = m.get("track_a_strict", {})
        tb = m.get("track_b_compatible", {})
        risk = m.get("selective_risk_metrics", {})
        eff = m.get("operational_efficiency", {})

        table_rows.append({
            "method_key": m_key,
            "method_label": method_labels.get(m_key, m_key),
            "accuracy_3class": p3.get("accuracy", 0.0),
            "macro_f1_3class": p3.get("macro_f1", 0.0),
            "track_a_strict_accuracy": ta.get("accuracy", 0.0),
            "track_a_strict_macro_f1": ta.get("macro_f1", 0.0),
            "track_b_compatible_accuracy": tb.get("accuracy", 0.0),
            "track_b_compatible_macro_f1": tb.get("macro_f1", 0.0),
            "false_invalid_rate_FIR": risk.get("false_invalid_rate_FIR", 0.0),
            "stale_escape_rate_SER": risk.get("stale_escape_rate_SER", 0.0),
            "coverage": risk.get("coverage", 0.0),
            "selective_risk": risk.get("selective_risk", 0.0),
            "avg_actions": eff.get("avg_action_count", 0.0),
            "avg_wall_time_sec": eff.get("avg_wall_time_sec", 0.0)
        })
    return table_rows


def main():
    parser = argparse.ArgumentParser(description="Run Full RoleMem Benchmark Experiments.")
    parser.add_argument("--inputs", type=str, default="data/formal_v2_2/formal_inputs.jsonl", help="Inputs JSONL path.")
    parser.add_argument("--gold", type=str, default="data/formal_v2_2/formal_gold_private.jsonl", help="Gold JSONL path.")
    parser.add_argument("--case-map", type=str, default="data/formal_v2_2/formal_case_map_private.json", help="Case map path.")
    parser.add_argument("--output-dir", "-o", type=str, default="experiments/exp001_full", help="Output experiment directory.")
    parser.add_argument("--limit", "-n", type=int, default=None, help="Limit number of cases (default: None for all 150).")
    args = parser.parse_args()

    print("\n" + "=" * 70)
    print("        RoleMem Full Benchmark Experimental Execution")
    print("=" * 70)
    print(f"Inputs Path      : {args.inputs}")
    print(f"Gold Path        : {args.gold}")
    print(f"Case Map Path    : {args.case_map}")
    print(f"Output Directory : {args.output_dir}")
    print(f"Case Limit       : {args.limit or 'All (150)'}")
    print("=" * 70 + "\n")

    runner = BenchmarkRunner(
        inputs_path=args.inputs,
        gold_path=args.gold,
        case_map_path=args.case_map,
        output_dir=args.output_dir
    )

    methods = ["majority", "static_ast", "naive_rag", "rolemem"]
    all_predictions: Dict[str, List[Dict[str, Any]]] = {}

    # Run inference for all methods
    for m in methods:
        print(f"-> Running inference for method: {m} ...")
        t_start = time.time()
        preds, _ = runner.run_method(m, limit=args.limit)
        all_predictions[m] = preds
        print(f"   Completed {len(preds)} cases in {time.time() - t_start:.2f}s")

    # Execute all metrics & save standard artifacts
    print("\n-> Evaluating metrics across all models ...")
    all_metrics = runner.execute_all(methods=methods, limit=args.limit, track="strict")

    # Generate and save comparison_table.json
    table_data = generate_comparison_table_data(all_metrics)
    comp_file = os.path.join(args.output_dir, "comparison_table.json")
    with open(comp_file, "w", encoding="utf-8") as f:
        json.dump(table_data, f, indent=2)
    print(f"-> Saved comparison table to: {comp_file}")

    # Generate and save claim_type_analysis.json
    claim_analysis = compute_claim_type_analysis(runner.inputs[:args.limit], runner.gold_annotations, all_predictions)
    claim_file = os.path.join(args.output_dir, "claim_type_analysis.json")
    with open(claim_file, "w", encoding="utf-8") as f:
        json.dump(claim_analysis, f, indent=2)
    print(f"-> Saved claim type analysis to: {claim_file}")

    # Render Table 1
    table_str = runner.render_table(all_metrics, track="strict")
    print(table_str)

    # Render Claim Type Analysis Breakdown Table
    print("\n### Table 2: Performance Breakdown by Epistemic Claim Category\n")
    print("| Category | Cases | Majority Acc/F1 | Static AST Acc/F1 | Naive RAG Acc/F1 | RoleMem Acc/F1 |")
    print("| :--- | :---: | :---: | :---: | :---: | :---: |")

    cat_order = ["SIGNATURE", "DEFAULT", "BEHAVIOR", "DEPENDENCY", "CONFIG"]
    for cat in cat_order:
        cat_info = claim_analysis["by_category"].get(cat, {})
        counts = claim_analysis["category_case_counts"].get(cat, {})
        n = counts.get("total_cases", 0)

        maj_m = cat_info.get("majority", {})
        ast_m = cat_info.get("static_ast", {})
        rag_m = cat_info.get("naive_rag", {})
        rol_m = cat_info.get("rolemem", {})

        maj_str = f"{maj_m.get('accuracy', 0.0)*100:.1f}% / {maj_m.get('macro_f1', 0.0)*100:.1f}%"
        ast_str = f"{ast_m.get('accuracy', 0.0)*100:.1f}% / {ast_m.get('macro_f1', 0.0)*100:.1f}%"
        rag_str = f"{rag_m.get('accuracy', 0.0)*100:.1f}% / {rag_m.get('macro_f1', 0.0)*100:.1f}%"
        rol_str = f"**{rol_m.get('accuracy', 0.0)*100:.1f}% / {rol_m.get('macro_f1', 0.0)*100:.1f}%**"

        print(f"| **{cat}** | {n} | {maj_str} | {ast_str} | {rag_str} | {rol_str} |")

    print("\n" + "=" * 70)
    print("Full benchmark experiment finished successfully!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
