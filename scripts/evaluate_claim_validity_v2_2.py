#!/usr/bin/env python3
"""
scripts/evaluate_claim_validity_v2_2.py

Protocol V2.2-Claim-Aware-V0.1 Comprehensive Benchmark Evaluator & Report Generator:
- Separates Phase 1 (Prediction Generation on Blind Inputs) and Phase 2 (Scoring against Gold Labels).
- Implements Fair Unified Evaluation Context with full file snapshots.
- Evaluates:
    1. File_Level_Baseline (Whole-file SHA256 parity)
    2. Pure_Symbol_AST_Baseline (AST symbol existence/digest)
    3. AST_Heuristic_RoleMem_Baseline (AST digest + diff hunk)
    4. Execution_Evidence_Baseline (Dynamic contract oracle alone)
    5. Claim_Aware_Static (Pure static AST claim verification: zero execution artifacts)
    6. Claim_Aware_StaticPlusExecution (Static claim verification + verified execution artifacts)
- Applies SelectivePolicy, ForcedBinaryValidDefaultPolicy, and ForcedBinaryStaleDefaultPolicy.
- Generates data/claim_validity_v2_2/evaluation_results.json and comprehensive markdown reports.
"""

import os
import sys
import json
import math
import hashlib
import subprocess
from typing import Dict, Any, List, Tuple, Optional

sys.path.insert(0, "/code/rolemem-agent-memory")
from src.evaluation.context import EvaluationContext, build_evaluation_context
from src.claim_validity.types import (
    ClaimType,
    GroundingStatus,
    ValidationStatus,
    MemoryClaim,
    ClaimEvaluationResult
)
from src.claim_validity.engine import ClaimAwareValidityEngine
from src.claim_validity.policy import (
    SelectivePolicy,
    ForcedBinaryValidDefaultPolicy,
    ForcedBinaryStaleDefaultPolicy
)
from src.symbol_validity import SymbolDigestExtractor
from src.validity import (
    FileValidityChecker,
    SymbolValidityChecker,
    DependencyValidityChecker,
    RoleMemValidityEngine
)

DATA_DIR = "/code/rolemem-agent-memory/data/claim_validity_v2_2"
INPUTS_PATH = os.path.join(DATA_DIR, "dev_claim_inputs.jsonl")
GOLD_PATH = os.path.join(DATA_DIR, "dev_claim_gold.jsonl")
PARAPHRASE_PATH = os.path.join(DATA_DIR, "paraphrase_dev.jsonl")
BLIND_INPUTS_PATH = "/code/rolemem-agent-memory/data/memory_validity_v2_1/blind_inputs.jsonl"
V2_1_DIR = "/code/rolemem-agent-memory/data/memory_validity_v2_1"
REPORTS_DIR = "/code/rolemem-agent-memory/reports"

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)


def compute_metrics(
    predictions: List[str],
    gold_labels: List[str],
    categories: List[str],
    claim_types: List[str]
) -> Dict[str, Any]:
    total = len(gold_labels)
    decided_indices = [i for i, p in enumerate(predictions) if p != "UNCERTAIN"]
    decided_count = len(decided_indices)
    coverage = decided_count / total if total > 0 else 0.0

    if decided_count > 0:
        tp = sum(1 for i in decided_indices if predictions[i] == "STALE" and gold_labels[i] == "STALE")
        tn = sum(1 for i in decided_indices if predictions[i] == "VALID" and gold_labels[i] == "VALID")
        fp = sum(1 for i in decided_indices if predictions[i] == "STALE" and gold_labels[i] == "VALID")
        fn = sum(1 for i in decided_indices if predictions[i] == "VALID" and gold_labels[i] == "STALE")

        decided_acc = (tp + tn) / decided_count
        overall_acc = (tp + tn) / total
        selective_risk = (fp + fn) / decided_count

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

        valid_recall = tn / (tn + fp) if (tn + fp) > 0 else 0.0
        stale_recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        balanced_acc = (valid_recall + stale_recall) / 2.0

        valid_prec = tn / (tn + fn) if (tn + fn) > 0 else 0.0
        valid_f1 = (2 * valid_prec * valid_recall) / (valid_prec + valid_recall) if (valid_prec + valid_recall) > 0 else 0.0
        macro_f1 = (f1 + valid_f1) / 2.0

        denom = math.sqrt((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn))
        mcc = ((tp * tn) - (fp * fn)) / denom if denom > 0 else 0.0

        # FIR = False Invalidation Rate: FP / (FP + TN)
        fir = fp / (fp + tn) if (fp + tn) > 0 else 0.0
        # SER = Stale Exposure Rate: FN / (FN + TP)
        ser = fn / (fn + tp) if (fn + tp) > 0 else 0.0
    else:
        decided_acc = overall_acc = selective_risk = precision = recall = f1 = balanced_acc = macro_f1 = mcc = fir = ser = 0.0

    # Per-Category Accuracy
    unique_cats = sorted(list(set(categories)))
    per_cat = {}
    for cat in unique_cats:
        cat_indices = [i for i, c in enumerate(categories) if c == cat]
        cat_decided = [i for i in cat_indices if predictions[i] != "UNCERTAIN"]
        if cat_decided:
            cat_correct = sum(1 for i in cat_decided if predictions[i] == gold_labels[i])
            per_cat[cat] = cat_correct / len(cat_decided)
        else:
            per_cat[cat] = 0.0

    # Per-ClaimType Accuracy
    unique_types = sorted(list(set(claim_types)))
    per_type = {}
    for ct in unique_types:
        ct_indices = [i for i, t in enumerate(claim_types) if t == ct]
        if cat_decided := [i for i in ct_indices if predictions[i] != "UNCERTAIN"]:
            ct_correct = sum(1 for i in cat_decided if predictions[i] == gold_labels[i])
            per_type[ct] = {
                "count": len(ct_indices),
                "decided": len(cat_decided),
                "accuracy": ct_correct / len(cat_decided)
            }
        else:
            per_type[ct] = {
                "count": len(ct_indices),
                "decided": 0,
                "accuracy": 0.0
            }

    return {
        "Coverage": coverage,
        "Accuracy_Overall": overall_acc,
        "Accuracy_Decided": decided_acc,
        "Balanced_Accuracy": balanced_acc,
        "Macro_F1": macro_f1,
        "MCC": mcc,
        "Selective_Risk": selective_risk,
        "Precision": precision,
        "Recall": recall,
        "F1": f1,
        "False_Invalidation_Rate_FIR": fir,
        "Stale_Exposure_Rate_SER": ser,
        "Per_Category_Accuracy": per_cat,
        "Per_ClaimType_Accuracy": per_type
    }


def run_phase_1_predictions() -> Dict[str, str]:
    """
    Phase 1: Generates blind prediction files on disk.
    Strictly independent of gold labels.
    """
    print("--- Running Phase 1: Blind Predictions Generation ---")
    with open(INPUTS_PATH, "r", encoding="utf-8") as f:
        inputs = [json.loads(line) for line in f if line.strip()]

    with open(BLIND_INPUTS_PATH, "r", encoding="utf-8") as f:
        blind_inputs = {r["case_id"]: r for r in [json.loads(line) for line in f if line.strip()]}

    claim_engine = ClaimAwareValidityEngine()
    selective_policy = SelectivePolicy()
    valid_default_policy = ForcedBinaryValidDefaultPolicy()
    stale_default_policy = ForcedBinaryStaleDefaultPolicy()

    file_checker = FileValidityChecker()
    sym_checker = SymbolValidityChecker()
    dep_checker = DependencyValidityChecker()
    rolemem_engine = RoleMemValidityEngine()

    pred_records_file = []
    pred_records_sym = []
    pred_records_dep = []
    pred_records_rolemem_abstain = []
    pred_records_rolemem_forced = []
    pred_records_exec_only = []

    claim_static_results: List[ClaimEvaluationResult] = []
    claim_exec_results: List[ClaimEvaluationResult] = []

    for item in inputs:
        cid = item.get("source_case_id") or item["claim_id"]
        claim_id = item["claim_id"]
        blind = blind_inputs.get(cid, {})
        fpath = item["file_path"]
        sym = item["symbol"]
        repo = item["repository"]
        b_commit = item.get("base_commit", "")
        t_commit = item.get("target_commit", "")

        repo_root = os.path.join("/code/repo_cache", repo)
        b_src = ""
        t_src = ""
        diff = ""

        # Fetch full files from repository cache if available
        if os.path.isdir(repo_root) and b_commit and t_commit and fpath:
            res_b = subprocess.run(["git", "show", f"{b_commit}:{fpath}"], cwd=repo_root, capture_output=True, text=True)
            if res_b.returncode == 0:
                b_src = res_b.stdout
            res_t = subprocess.run(["git", "show", f"{t_commit}:{fpath}"], cwd=repo_root, capture_output=True, text=True)
            if res_t.returncode == 0:
                t_src = res_t.stdout
            res_d = subprocess.run(["git", "diff", b_commit, t_commit, "--", fpath], cwd=repo_root, capture_output=True, text=True)
            if res_d.returncode == 0:
                diff = res_d.stdout

        if not b_src:
            b_src = blind.get("base_source_excerpt", "")
        if not t_src:
            t_src = blind.get("target_source_excerpt", "")
        if not diff:
            diff = blind.get("diff_hunk", "")

        # Load execution artifact if available
        exec_art = None
        for sub in ["contracts", "counterfactuals", "behavior_breaks"]:
            art_p = os.path.join(V2_1_DIR, sub, f"{cid}.json")
            if os.path.exists(art_p):
                try:
                    with open(art_p, "r", encoding="utf-8") as af:
                        exec_art = json.load(af)
                except Exception:
                    pass
                break

        # Build unified evaluation context
        ctx = build_evaluation_context(
            repository=repo,
            base_commit=b_commit,
            target_commit=t_commit,
            file_path=fpath,
            base_source=b_src,
            target_source=t_src,
            diff=diff,
            memory_statement=item["raw_statement"],
            symbol=sym,
            repository_root=repo_root if os.path.isdir(repo_root) else None,
            execution_evidence=exec_art,
            case_id=cid,
            claim_id=claim_id
        )

        # 1. File-Level Baseline (Whole-file SHA256 comparison)
        file_decision = "VALID" if ctx.is_file_unchanged else "STALE"
        pred_records_file.append({"claim_id": claim_id, "case_id": cid, "decision": file_decision})

        # 2. Pure Symbol AST Baseline
        res_s = sym_checker.evaluate(base_source=ctx.base_full_source, target_source=ctx.target_full_source, symbol_qualified_name=sym)
        pred_records_sym.append({"claim_id": claim_id, "case_id": cid, "decision": res_s.decision})

        # 3. Dependency Validity Baseline
        res_d = dep_checker.evaluate(base_source=ctx.base_full_source, target_source=ctx.target_full_source, symbol_qualified_name=sym, diff_hunk=diff)
        pred_records_dep.append({"claim_id": claim_id, "case_id": cid, "decision": res_d.decision})

        # 4. RoleMem Structural Baseline
        res_rm = rolemem_engine.evaluate(
            memory_statement=ctx.memory_statement,
            symbol_qualified_name=sym,
            base_source=ctx.base_full_source,
            target_source=ctx.target_full_source,
            diff_hunk=diff,
            file_path=fpath
        )
        pred_records_rolemem_abstain.append({"claim_id": claim_id, "case_id": cid, "decision": res_rm.decision})
        pred_records_rolemem_forced.append({"claim_id": claim_id, "case_id": cid, "decision": "VALID" if res_rm.decision == "UNCERTAIN" else res_rm.decision})

        # 5. Execution Evidence Oracle Baseline (measures oracle contribution alone)
        if exec_art:
            target_exec = exec_art.get("target_execution") or exec_art.get("old_on_target") or {}
            if target_exec.get("passed") is True:
                exec_decision = "VALID"
            elif target_exec.get("passed") is False:
                exec_decision = "STALE"
            else:
                exec_decision = "UNCERTAIN"
        else:
            exec_decision = "UNCERTAIN"
        pred_records_exec_only.append({"claim_id": claim_id, "case_id": cid, "decision": exec_decision})

        # 6. Claim-Aware Engine (Static Only: zero execution artifacts passed)
        m_claim = MemoryClaim.from_dict(item)
        res_claim_static = claim_engine.evaluate(
            claim_or_statement=m_claim,
            base_source=ctx.base_full_source,
            target_source=ctx.target_full_source,
            diff_hunk=diff,
            symbol_qualified_name=sym,
            file_path=fpath,
            repository=repo,
            base_commit=ctx.base_commit,
            target_commit=ctx.target_commit,
            execution_artifact=None,
            source_case_id=cid
        )
        claim_static_results.append(res_claim_static)

        # 7. Claim-Aware Engine (Static + Execution: explicitly tagged EXECUTION_EVIDENCE_ASSISTED)
        res_claim_exec = claim_engine.evaluate(
            claim_or_statement=m_claim,
            base_source=ctx.base_full_source,
            target_source=ctx.target_full_source,
            diff_hunk=diff,
            symbol_qualified_name=sym,
            file_path=fpath,
            repository=repo,
            base_commit=ctx.base_commit,
            target_commit=ctx.target_commit,
            execution_artifact=exec_art,
            source_case_id=cid
        )
        claim_exec_results.append(res_claim_exec)

    # Apply policies for claim static and claim static+execution
    preds_static_sel = selective_policy.decide_batch(claim_static_results)
    preds_static_vdef = valid_default_policy.decide_batch(claim_static_results)
    preds_static_sdef = stale_default_policy.decide_batch(claim_static_results)

    preds_exec_sel = selective_policy.decide_batch(claim_exec_results)
    preds_exec_vdef = valid_default_policy.decide_batch(claim_exec_results)
    preds_exec_sdef = stale_default_policy.decide_batch(claim_exec_results)

    prediction_files = {
        "file_level": os.path.join(DATA_DIR, "predictions_file_level.jsonl"),
        "pure_symbol": os.path.join(DATA_DIR, "predictions_pure_symbol.jsonl"),
        "dependency": os.path.join(DATA_DIR, "predictions_dependency.jsonl"),
        "rolemem_abstain": os.path.join(DATA_DIR, "predictions_rolemem_abstain.jsonl"),
        "rolemem_forced": os.path.join(DATA_DIR, "predictions_rolemem_forced.jsonl"),
        "execution_only": os.path.join(DATA_DIR, "predictions_execution_only.jsonl"),
        "claim_static_selective": os.path.join(DATA_DIR, "predictions_claim_static_selective.jsonl"),
        "claim_static_valid_default": os.path.join(DATA_DIR, "predictions_claim_static_valid_default.jsonl"),
        "claim_static_stale_default": os.path.join(DATA_DIR, "predictions_claim_static_stale_default.jsonl"),
        "claim_exec_selective": os.path.join(DATA_DIR, "predictions_claim_exec_selective.jsonl"),
        "claim_exec_valid_default": os.path.join(DATA_DIR, "predictions_claim_exec_valid_default.jsonl"),
        "claim_exec_stale_default": os.path.join(DATA_DIR, "predictions_claim_exec_stale_default.jsonl")
    }

    # Write prediction files
    def write_preds(path: str, records: List[Dict[str, Any]]):
        with open(path, "w", encoding="utf-8") as f:
            for r in records:
                f.write(json.dumps(r) + "\n")

    write_preds(prediction_files["file_level"], pred_records_file)
    write_preds(prediction_files["pure_symbol"], pred_records_sym)
    write_preds(prediction_files["dependency"], pred_records_dep)
    write_preds(prediction_files["rolemem_abstain"], pred_records_rolemem_abstain)
    write_preds(prediction_files["rolemem_forced"], pred_records_rolemem_forced)
    write_preds(prediction_files["execution_only"], pred_records_exec_only)

    write_preds(prediction_files["claim_static_selective"], [{"claim_id": inputs[i]["claim_id"], "decision": p} for i, p in enumerate(preds_static_sel)])
    write_preds(prediction_files["claim_static_valid_default"], [{"claim_id": inputs[i]["claim_id"], "decision": p} for i, p in enumerate(preds_static_vdef)])
    write_preds(prediction_files["claim_static_stale_default"], [{"claim_id": inputs[i]["claim_id"], "decision": p} for i, p in enumerate(preds_static_sdef)])

    write_preds(prediction_files["claim_exec_selective"], [{"claim_id": inputs[i]["claim_id"], "decision": p} for i, p in enumerate(preds_exec_sel)])
    write_preds(prediction_files["claim_exec_valid_default"], [{"claim_id": inputs[i]["claim_id"], "decision": p} for i, p in enumerate(preds_exec_vdef)])
    write_preds(prediction_files["claim_exec_stale_default"], [{"claim_id": inputs[i]["claim_id"], "decision": p} for i, p in enumerate(preds_exec_sdef)])

    print("Phase 1 Predictions generated and saved to disk.")
    return prediction_files


def run_phase_2_evaluation(prediction_files: Dict[str, str]):
    """
    Phase 2: Reads blind predictions and gold labels from disk, scores metrics.
    """
    print("--- Running Phase 2: Scoring & Metric Evaluation ---")
    with open(GOLD_PATH, "r", encoding="utf-8") as f:
        gold_records = [json.loads(line) for line in f if line.strip()]

    gold_labels = [g["gold_label"] for g in gold_records]
    categories = [g["category"] for g in gold_records]
    claim_types = [g["claim_type"] for g in gold_records]

    eval_summary = {}

    for name, path in prediction_files.items():
        with open(path, "r", encoding="utf-8") as f:
            preds = [json.loads(line)["decision"] for line in f if line.strip()]
        eval_summary[name] = compute_metrics(preds, gold_labels, categories, claim_types)

    # Save evaluation results JSON
    eval_json_p = os.path.join(DATA_DIR, "evaluation_results.json")
    with open(eval_json_p, "w", encoding="utf-8") as f:
        json.dump(eval_summary, f, indent=2)

    print(f"Scoring Complete. Results saved to {eval_json_p}")

    # Generate Markdown Design & Fairness Reports
    generate_reports(eval_summary)


def generate_reports(eval_summary: Dict[str, Any]):
    # 1. Generate reports/v2.2-v0.1-baseline-fairness.md
    fairness_lines = [
        "# RoleMem Protocol V2.2-V0.1 — Baseline Fairness & Evidence Budget Audit",
        "",
        "## Formal Status Declaration",
        "```text",
        "PROTOCOL_VERSION = 2.2-claim-aware-v0.1",
        "CURRENT_V0_RESULT_STATUS = DEVELOPMENT_COUPLED_NOT_FOR_SCIENTIFIC_CLAIM",
        "V2_1_DEVELOPMENT_MUTATIONS = 0",
        "V2_2_V0_1_EVALUATION_INTEGRITY = COMPLETE",
        "V2_2_ALGORITHM_FREEZE = NO",
        "V2_2_FORMAL_TEST_OPENED = NO",
        "V2_2_FORMAL_HOLDOUT_DEFINED = NO",
        "FORMAL_AGENT_RESULTS = NO",
        "FORMAL_PAPER_RESULTS = NO",
        "```",
        "",
        "---",
        "",
        "## 1. Evidence Budget & Information Asymmetry Audit",
        "",
        "| Mechanism | Input Context | AST Analysis | Git Diff | Execution Oracle | Decision Policy | Notes |",
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
        "| **File_Level_Baseline** | Full Source File | No | No | No | SHA256 Parity | Whole-file byte hash |",
        "| **Pure_Symbol_AST_Baseline** | Full Source File | Yes | No | No | Symbol Digest Parity | Function/class AST digest |",
        "| **Dependency_Validity_Baseline** | Full Source File | Yes | Yes | No | Intra-module Linkage | Graph & call chain trace |",
        "| **RoleMem_Structural_V2_1** | Full Source File | Yes | Yes | No | AST + Diff Heuristic | Abstain / Forced Valid |",
        "| **Execution_Evidence_Baseline** | None | No | No | Yes | Oracle Execution Result | Dynamic test runner alone |",
        "| **Claim_Aware_Static** | Full Source File | Yes | Yes | **NO (0%)** | Selective / Valid / Stale Default | 100% Static Claim-Aware |",
        "| **Claim_Aware_StaticPlusExecution** | Full Source File | Yes | Yes | **YES (Assisted)** | Selective / Valid / Stale Default | Explicitly Assisted |",
        "",
        "---",
        "",
        "## 2. Performance Breakdown by Mechanism",
        "",
        "| Mechanism | Coverage | Overall Acc | Balanced Acc | Macro F1 | MCC | FIR | SER |",
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |"
    ]

    for name, mdata in eval_summary.items():
        cov = mdata["Coverage"] * 100
        acc = mdata["Accuracy_Overall"] * 100
        bacc = mdata["Balanced_Accuracy"] * 100
        mf1 = mdata["Macro_F1"] * 100
        mcc = mdata["MCC"]
        fir = mdata["False_Invalidation_Rate_FIR"] * 100
        ser = mdata["Stale_Exposure_Rate_SER"] * 100
        fairness_lines.append(f"| **{name}** | {cov:.1f}% | {acc:.1f}% | {bacc:.1f}% | {mf1:.1f}% | {mcc:+.3f} | {fir:.1f}% | {ser:.1f}% |")

    fairness_p = os.path.join(REPORTS_DIR, "v2.2-v0.1-baseline-fairness.md")
    with open(fairness_p, "w", encoding="utf-8") as f:
        f.write("\n".join(fairness_lines) + "\n")

    # 2. Update reports/protocol-v2.2-v0-design.md
    design_lines = [
        "# RoleMem Protocol V2.2-Claim-Aware-V0.1 — Architecture Design & Empirical Report",
        "",
        "## Formal Status Declaration",
        "```text",
        "PROTOCOL_VERSION = 2.2-claim-aware-v0.1",
        "CURRENT_V0_RESULT_STATUS = DEVELOPMENT_COUPLED_NOT_FOR_SCIENTIFIC_CLAIM",
        "V2_1_DEVELOPMENT_MUTATIONS = 0",
        "V2_2_V0_1_EVALUATION_INTEGRITY = COMPLETE",
        "V2_2_ALGORITHM_FREEZE = NO",
        "V2_2_FORMAL_TEST_OPENED = NO",
        "V2_2_FORMAL_HOLDOUT_DEFINED = NO",
        "FORMAL_AGENT_RESULTS = NO",
        "FORMAL_PAPER_RESULTS = NO",
        "```",
        "",
        "---",
        "",
        "## 1. Integrity Hardening & Decoupling in V0.1",
        "",
        "- **Zero Benchmark Heuristic Whitelists**: All case IDs and keyword-specific hacks eliminated from source code.",
        "- **Unified EvaluationContext**: Whole-file SHA256 parity and identical source snapshots for all baselines and claim engines.",
        "- **Separation of Static vs Execution Assisted**: Honest breakdown between pure static claim reasoning and execution-assisted reasoning.",
        "- **Two-Phase Pipeline**: Complete separation of prediction generation on blind inputs and scoring against gold labels.",
        "- **Holdout Invalidation & Contamination Registry**: Formal holdout candidate split marked INVALIDATED due to prior protocol contamination.",
        "",
        "---",
        "",
        "## 2. Benchmark Metrics Summary (55 Development Cases)",
        "",
        "| Mechanism / Policy | Coverage | Overall Acc | Balanced Acc | Macro F1 | MCC | Selective Risk | FIR | SER |",
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |"
    ]

    for name, mdata in eval_summary.items():
        cov = mdata["Coverage"] * 100
        acc = mdata["Accuracy_Overall"] * 100
        bacc = mdata["Balanced_Accuracy"] * 100
        mf1 = mdata["Macro_F1"] * 100
        mcc = mdata["MCC"]
        risk = mdata["Selective_Risk"] * 100
        fir = mdata["False_Invalidation_Rate_FIR"] * 100
        ser = mdata["Stale_Exposure_Rate_SER"] * 100
        design_lines.append(f"| **{name}** | {cov:.1f}% | {acc:.1f}% | {bacc:.1f}% | {mf1:.1f}% | {mcc:+.3f} | {risk:.1f}% | {fir:.1f}% | {ser:.1f}% |")

    design_lines.extend([
        "",
        "---",
        "",
        "## 3. Granular Category Breakdown",
        "",
        "| Mechanism / Policy | Cat A (Valid) | Cat B (Valid) | Cat C (Stale) | Cat D1 (Stale) | Cat D2 (Stale) |",
        "| :--- | :--- | :--- | :--- | :--- | :--- |"
    ])

    for name, mdata in eval_summary.items():
        pca = mdata["Per_Category_Accuracy"]
        a_acc = pca.get("CAT_A_FILE_CHG_SYM_SAME_VALID", 0.0) * 100
        b_acc = pca.get("CAT_B_SYM_CHG_MEMORY_VALID", 0.0) * 100
        c_acc = pca.get("CAT_C_SYM_SAME_MEMORY_STALE", 0.0) * 100
        d1_acc = pca.get("CAT_D1_SYM_REM_STALE", 0.0) * 100
        d2_acc = pca.get("CAT_D2_SYM_CHG_BEHAVIOR_STALE", 0.0) * 100
        design_lines.append(f"| **{name}** | {a_acc:.1f}% | {b_acc:.1f}% | {c_acc:.1f}% | {d1_acc:.1f}% | {d2_acc:.1f}% |")

    design_p = os.path.join(REPORTS_DIR, "protocol-v2.2-v0-design.md")
    with open(design_p, "w", encoding="utf-8") as f:
        f.write("\n".join(design_lines) + "\n")

    print(f"Reports generated:\n  {fairness_p}\n  {design_p}")


if __name__ == "__main__":
    preds = run_phase_1_predictions()
    run_phase_2_evaluation(preds)
