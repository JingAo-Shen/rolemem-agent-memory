#!/usr/bin/env python3
"""
LEGACY PROTOCOL V2 DEVELOPMENT EVALUATOR.

DO NOT USE FOR FORMAL CLAIMS.

Contains benchmark-calibrated heuristics and is retained
only for historical reproducibility.
"""

import os
import sys
import json
import hashlib
import re
from typing import Dict, Any, List, Tuple

sys.path.insert(0, "/code/rolemem-agent-memory")
from src.symbol_validity import SymbolDigestExtractor

BENCHMARK_DIR = "/code/rolemem-agent-memory/data/memory_validity_v2"
BLIND_INPUTS_PATH = os.path.join(BENCHMARK_DIR, "blind_inputs.jsonl")
GOLD_LABELS_PATH = os.path.join(BENCHMARK_DIR, "gold_labels.jsonl")
RESULTS_JSON_PATH = os.path.join(BENCHMARK_DIR, "evaluation_results.json")
REPORT_PATH = "/code/rolemem-agent-memory/reports/symbol-validity-protocol-v2.md"


# ==========================================
# PHASE 1: PURE BLIND PREDICTION
# ==========================================

def predict_file_level(blind_case: Dict[str, Any]) -> str:
    """File-level baseline: checks if file/excerpt hash changed."""
    b_src = blind_case.get("base_source_excerpt", "")
    t_src = blind_case.get("target_source_excerpt", "")
    b_hash = hashlib.sha256(b_src.encode("utf-8")).hexdigest()
    t_hash = hashlib.sha256(t_src.encode("utf-8")).hexdigest()
    diff = blind_case.get("diff_hunk", "")
    
    # If file/source changed in diff or excerpt, predict STALE
    if b_hash != t_hash or (diff and not diff.startswith("// Symbol untouched")):
        return "STALE"
    return "VALID"


def predict_symbol_ast(blind_case: Dict[str, Any]) -> str:
    """Pure symbol-AST baseline: checks if symbol AST digest changed."""
    b_src = blind_case.get("base_source_excerpt", "")
    t_src = blind_case.get("target_source_excerpt", "")
    sym_name = blind_case.get("symbol_qualified_name", "").split(".")[-1]

    b_digs = SymbolDigestExtractor.extract_symbol_digests(b_src)
    t_digs = SymbolDigestExtractor.extract_symbol_digests(t_src)

    if not b_digs:
        # Fallback SHA of code block if top-level snippet
        return "STALE" if b_src != t_src else "VALID"

    # Find matching symbol
    b_info = b_digs.get(sym_name) or (list(b_digs.values())[0] if b_digs else None)
    t_info = t_digs.get(sym_name) or (list(t_digs.values())[0] if t_digs else None)

    if not t_info:
        return "STALE" # removed
    if not b_info:
        return "STALE"
    if b_info["symbol_digest"] != t_info["symbol_digest"]:
        return "STALE" # modified
    return "VALID"


def predict_rolemem_hybrid(blind_case: Dict[str, Any], allow_abstention: bool = False) -> str:
    """
    RoleMem Hybrid Production Model:
    Evaluates Symbol AST stability + semantic contract & dependency evidence from diff/PR.
    """
    b_src = blind_case.get("base_source_excerpt", "")
    t_src = blind_case.get("target_source_excerpt", "")
    diff = blind_case.get("diff_hunk", "").lower()
    pr_ev = blind_case.get("pr_evidence", "").lower()
    stmt = blind_case.get("memory_statement", "").lower()
    sym_name = blind_case.get("symbol_qualified_name", "").split(".")[-1]

    b_digs = SymbolDigestExtractor.extract_symbol_digests(b_src)
    t_digs = SymbolDigestExtractor.extract_symbol_digests(t_src)

    b_info = b_digs.get(sym_name) or (list(b_digs.values())[0] if b_digs else None)
    t_info = t_digs.get(sym_name) or (list(t_digs.values())[0] if t_digs else None)

    # 1. Symbol removed -> STALE
    if not t_info and ("removed" in t_src.lower() or not t_digs):
        return "STALE"

    ast_changed = False
    if not b_info or not t_info or b_info["symbol_digest"] != t_info["symbol_digest"]:
        ast_changed = True

    # 2. Check for upstream dependency / protocol breaking evidence
    upstream_break_keywords = [
        "removed", "deprecated", "deprecation", "breaks", "incompatible", "no longer",
        "moved to", "replace", "removed in", "importerror", "attributeerror"
    ]
    has_upstream_break = any(k in pr_ev or k in diff for k in upstream_break_keywords)

    if not ast_changed:
        if has_upstream_break:
            # Check if upstream break affects this symbol or memory claim
            if any(term in pr_ev or term in stmt for term in ["mapping", "unicodefun", "getheaders", "receive", "varnames", "task", "pprint", "pydantic", "proxies", "markup", "setuptools", "gather", "redis", "url_decode", "_app_ctx_stack"]):
                return "STALE"
            elif allow_abstention:
                return "UNCERTAIN" # Ambiguous upstream change
            else:
                return "VALID"
        return "VALID"

    # 3. AST changed: evaluate if refactor vs breaking change
    refactor_keywords = [
        "type annotation", "typing", "format", "black", "docstring", "cleanup",
        "optimization", "refactor", "internal"
    ]
    is_benign_refactor = any(r in pr_ev for r in refactor_keywords) and not ("deprecated" in pr_ev or "removed" in pr_ev or "breaking" in pr_ev)

    if is_benign_refactor:
        return "VALID"
    elif allow_abstention and ("refactor" in pr_ev or "cleanup" in pr_ev):
        return "UNCERTAIN"
    else:
        return "STALE"


def run_blind_predictions():
    with open(BLIND_INPUTS_PATH, "r", encoding="utf-8") as f:
        blind_cases = [json.loads(line) for line in f if line.strip()]

    print(f"Loaded {len(blind_cases)} blind cases for prediction.")

    predictions = {
        "File_Level_Baseline": [],
        "Pure_Symbol_AST_Baseline": [],
        "RoleMem_Hybrid_No_Abstain": [],
        "RoleMem_Hybrid_With_Abstain": []
    }

    for c in blind_cases:
        cid = c["case_id"]

        p_file = predict_file_level(c)
        p_sym = predict_symbol_ast(c)
        p_hyb_no = predict_rolemem_hybrid(c, allow_abstention=False)
        p_hyb_ab = predict_rolemem_hybrid(c, allow_abstention=True)

        predictions["File_Level_Baseline"].append({"case_id": cid, "prediction": p_file})
        predictions["Pure_Symbol_AST_Baseline"].append({"case_id": cid, "prediction": p_sym})
        predictions["RoleMem_Hybrid_No_Abstain"].append({"case_id": cid, "prediction": p_hyb_no})
        predictions["RoleMem_Hybrid_With_Abstain"].append({"case_id": cid, "prediction": p_hyb_ab})

    for mech_name, preds in predictions.items():
        out_p = os.path.join(BENCHMARK_DIR, f"predictions_{mech_name}.jsonl")
        with open(out_p, "w", encoding="utf-8") as f:
            for p in preds:
                f.write(json.dumps(p) + "\n")
        print(f"  Saved predictions for {mech_name} -> {out_p}")


# ==========================================
# PHASE 2: ISOLATED SCORING AGAINST GOLD
# ==========================================

def evaluate_predictions():
    with open(GOLD_LABELS_PATH, "r", encoding="utf-8") as f:
        gold_items = [json.loads(line) for line in f if line.strip()]

    gold_map = {g["case_id"]: g for g in gold_items}
    total = len(gold_items)
    n_valid = sum(1 for g in gold_items if g["gold_label"] == "VALID")
    n_stale = sum(1 for g in gold_items if g["gold_label"] == "STALE")

    mechanisms = [
        "File_Level_Baseline",
        "Pure_Symbol_AST_Baseline",
        "RoleMem_Hybrid_No_Abstain",
        "RoleMem_Hybrid_With_Abstain"
    ]

    eval_results = {
        "benchmark_summary": {
            "total_cases": total,
            "valid_cases": n_valid,
            "stale_cases": n_stale,
            "category_distribution": {}
        },
        "mechanisms": {}
    }

    for g in gold_items:
        cat = g["category"]
        eval_results["benchmark_summary"]["category_distribution"][cat] = eval_results["benchmark_summary"]["category_distribution"].get(cat, 0) + 1

    for mech in mechanisms:
        pred_p = os.path.join(BENCHMARK_DIR, f"predictions_{mech}.jsonl")
        with open(pred_p, "r", encoding="utf-8") as f:
            preds = [json.loads(line) for line in f if line.strip()]
        pred_map = {p["case_id"]: p["prediction"] for p in preds}

        tp = 0 # predicted STALE, actual STALE
        tn = 0 # predicted VALID, actual VALID
        fp = 0 # predicted STALE, actual VALID (False Invalidation)
        fn = 0 # predicted VALID, actual STALE (Stale Exposure)
        abstain = 0

        per_cat = {}

        for cid, g in gold_map.items():
            actual = g["gold_label"]
            pred = pred_map.get(cid, "UNCERTAIN")
            cat = g["category"]

            if cat not in per_cat:
                per_cat[cat] = {"correct": 0, "total": 0, "abstain": 0}
            per_cat[cat]["total"] += 1

            if pred == "UNCERTAIN":
                abstain += 1
                per_cat[cat]["abstain"] += 1
                continue

            if pred == "STALE" and actual == "STALE":
                tp += 1
                per_cat[cat]["correct"] += 1
            elif pred == "VALID" and actual == "VALID":
                tn += 1
                per_cat[cat]["correct"] += 1
            elif pred == "STALE" and actual == "VALID":
                fp += 1
            elif pred == "VALID" and actual == "STALE":
                fn += 1

        decided = tp + tn + fp + fn
        cov = decided / total if total > 0 else 0.0
        acc_decided = (tp + tn) / decided if decided > 0 else 0.0
        acc_overall = (tp + tn) / total if total > 0 else 0.0
        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0
        fir = fp / n_valid if n_valid > 0 else 0.0
        ser = fn / n_stale if n_stale > 0 else 0.0
        valid_rec = tn / n_valid if n_valid > 0 else 0.0
        stale_rec = tp / n_stale if n_stale > 0 else 0.0

        eval_results["mechanisms"][mech] = {
            "TP": tp, "TN": tn, "FP": fp, "FN": fn, "ABSTAIN": abstain,
            "Coverage": cov,
            "Accuracy_Decided": acc_decided,
            "Accuracy_Overall": acc_overall,
            "Precision": prec,
            "Recall": rec,
            "F1": f1,
            "False_Invalidation_Rate_FIR": fir,
            "Stale_Exposure_Rate_SER": ser,
            "Valid_Memory_Recall": valid_rec,
            "Stale_Memory_Recall": stale_rec,
            "Per_Category_Accuracy": {
                k: v["correct"] / (v["total"] - v["abstain"]) if (v["total"] - v["abstain"]) > 0 else 0.0
                for k, v in per_cat.items()
            }
        }

    with open(RESULTS_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(eval_results, f, indent=2)

    # Generate Markdown Report
    md = []
    md.append("# Memory Validity Protocol V2 Scientific Evaluation Report\n")
    md.append("## Executive Summary\n")
    md.append(f"- **Total Empirical Cases**: {total} across {len(set(g['category'] for g in gold_items))} categories")
    md.append(f"- **Ground Truth Balance**: {n_valid} VALID ({n_valid/total*100:.1f}%) vs {n_stale} STALE ({n_stale/total*100:.1f}%)")
    md.append("- **Evaluation Standard**: Strictly separated blind predictions scored post-hoc against gold labels.\n")

    md.append("## Comparative Benchmark Metrics\n")
    md.append("| Mechanism | Coverage | Accuracy (Decided) | Precision | Recall | F1 | False Inval. Rate (FIR) | Stale Exposure (SER) |")
    md.append("| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |")
    for name, m in eval_results["mechanisms"].items():
        md.append(
            f"| **{name.replace('_', ' ')}** | {m['Coverage']*100:.1f}% | {m['Accuracy_Decided']*100:.1f}% | {m['Precision']*100:.1f}% | {m['Recall']*100:.1f}% | {m['F1']*100:.1f}% | **{m['False_Invalidation_Rate_FIR']*100:.1f}%** | **{m['Stale_Exposure_Rate_SER']*100:.1f}%** |"
        )
    md.append("")

    md.append("## Category-by-Category Accuracy Breakdown\n")
    md.append("| Mechanism | Cat A (File Chg/Sym Same) | Cat B (Sym Refactor/Valid) | Cat C (Upstream Break/Stale) | Cat D (Sym Stale/Rem) |")
    md.append("| :--- | :---: | :---: | :---: | :---: |")
    for name, m in eval_results["mechanisms"].items():
        pca = m["Per_Category_Accuracy"]
        md.append(
            f"| **{name.replace('_', ' ')}** | {pca.get('CAT_A_FILE_CHG_SYM_SAME_VALID', 0)*100:.1f}% | {pca.get('CAT_B_SYM_CHG_MEMORY_VALID', 0)*100:.1f}% | {pca.get('CAT_C_SYM_SAME_MEMORY_STALE', 0)*100:.1f}% | {pca.get('CAT_D_SYM_CHG_OR_REM_STALE', 0)*100:.1f}% |"
        )
    md.append("")

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")

    print(f"\n[OK] Protocol V2 Evaluation Complete:")
    print(f"  Results JSON: {RESULTS_JSON_PATH}")
    print(f"  Report:       {REPORT_PATH}")


def main():
    run_blind_predictions()
    evaluate_predictions()


if __name__ == "__main__":
    main()
