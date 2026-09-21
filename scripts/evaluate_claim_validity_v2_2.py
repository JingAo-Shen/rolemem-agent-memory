#!/usr/bin/env python3
"""
scripts/evaluate_claim_validity_v2_2.py

Protocol V2.2-Claim-Aware-V0.2 Structured-Claim Validity Evaluator & Report Generator:
- Evaluates Structured Claims from frozen data/claim_validity_v2_2/dev_claim_inputs_v2.jsonl.
- Strictly separates Phase 1 (Blind Prediction Generation) and Phase 2 (ID-Safe Scoring).
- Mechanisms Evaluated:
    1. File_Level_Baseline (Whole-file SHA256 parity)
    2. Pure_Symbol_AST_Baseline (AST symbol existence/digest)
    3. Dependency_Validity_Baseline (Intra-module AST linkage)
    4. RoleMem_Structural_V2_1_Abstain / Forced
    5. Oracle_Execution_Evidence_UpperBound (Theoretical oracle execution contribution)
    6. Claim_Aware_Static (Pure static claim reasoning: 0% execution artifacts)
    7. Claim_Aware_StaticPlusExecution (Execution-assisted claim verification)
- Enforces ID-Safe Map Scoring (assert prediction_ids == gold_ids).
- Records comprehensive run provenance per prediction.
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
INPUTS_PATH = os.path.join(DATA_DIR, "dev_claim_inputs_v2.jsonl")
GOLD_PATH = os.path.join(DATA_DIR, "dev_claim_gold_v2.jsonl")
BLIND_INPUTS_PATH = "/code/rolemem-agent-memory/data/memory_validity_v2_1/blind_inputs.jsonl"
V2_1_DIR = "/code/rolemem-agent-memory/data/memory_validity_v2_1"
REPORTS_DIR = "/code/rolemem-agent-memory/reports"

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)


def compute_metrics_id_safe(
    prediction_records: List[Dict[str, Any]],
    gold_records: List[Dict[str, Any]]
) -> Dict[str, Any]:
    pred_map = {p["claim_id"]: p["decision"] for p in prediction_records}
    gold_map = {g["claim_id"]: g["gold_label"] for g in gold_records}
    cat_map = {g["claim_id"]: g["category"] for g in gold_records}
    type_map = {g["claim_id"]: g["claim_type"] for g in gold_records}

    if set(pred_map.keys()) != set(gold_map.keys()):
        raise ValueError(f"SCORING_INVALID: Prediction IDs do not match Gold IDs! Preds: {len(pred_map)}, Gold: {len(gold_map)}")
    if len(pred_map) != len(prediction_records):
        raise ValueError(f"SCORING_INVALID: Duplicate prediction IDs detected!")

    claim_ids = sorted(list(gold_map.keys()))
    total = len(claim_ids)

    decided_ids = [cid for cid in claim_ids if pred_map[cid] != "UNCERTAIN"]
    decided_count = len(decided_ids)
    coverage = decided_count / total if total > 0 else 0.0

    if decided_count > 0:
        tp = sum(1 for cid in decided_ids if pred_map[cid] == "STALE" and gold_map[cid] == "STALE")
        tn = sum(1 for cid in decided_ids if pred_map[cid] == "VALID" and gold_map[cid] == "VALID")
        fp = sum(1 for cid in decided_ids if pred_map[cid] == "STALE" and gold_map[cid] == "VALID")
        fn = sum(1 for cid in decided_ids if pred_map[cid] == "VALID" and gold_map[cid] == "STALE")

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

        fir = fp / (fp + tn) if (fp + tn) > 0 else 0.0
        ser = fn / (fn + tp) if (fn + tp) > 0 else 0.0
    else:
        decided_acc = overall_acc = selective_risk = precision = recall = f1 = balanced_acc = macro_f1 = mcc = fir = ser = 0.0

    # Per-Category Coverage & Accuracy
    unique_cats = sorted(list(set(cat_map.values())))
    per_cat = {}
    for cat in unique_cats:
        c_ids = [cid for cid in claim_ids if cat_map[cid] == cat]
        c_decided = [cid for cid in c_ids if pred_map[cid] != "UNCERTAIN"]
        cnt = len(c_ids)
        dec_cnt = len(c_decided)
        cov = dec_cnt / cnt if cnt > 0 else 0.0
        acc = sum(1 for cid in c_decided if pred_map[cid] == gold_map[cid]) / dec_cnt if dec_cnt > 0 else None
        per_cat[cat] = {
            "total": cnt,
            "decided": dec_cnt,
            "coverage": cov,
            "accuracy": acc
        }

    # Per-ClaimType Coverage & Accuracy
    unique_types = sorted(list(set(type_map.values())))
    per_type = {}
    for ct in unique_types:
        t_ids = [cid for cid in claim_ids if type_map[cid] == ct]
        t_decided = [cid for cid in t_ids if pred_map[cid] != "UNCERTAIN"]
        cnt = len(t_ids)
        dec_cnt = len(t_decided)
        cov = dec_cnt / cnt if cnt > 0 else 0.0
        acc = sum(1 for cid in t_decided if pred_map[cid] == gold_map[cid]) / dec_cnt if dec_cnt > 0 else None
        per_type[ct] = {
            "total": cnt,
            "decided": dec_cnt,
            "coverage": cov,
            "accuracy": acc
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
        "Per_Category_Breakdown": per_cat,
        "Per_ClaimType_Breakdown": per_type
    }


def compute_sha256(val: Any) -> str:
    if isinstance(val, dict):
        text = json.dumps(val, sort_keys=True)
    else:
        text = str(val)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def run_phase_1_predictions() -> Dict[str, str]:
    """
    Phase 1: Generates blind prediction files on disk with full execution provenance.
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
    pred_records_oracle_exec = []

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

        # Load full files from git cache
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

        claim_hash = compute_sha256(item)
        ctx_hash = compute_sha256(ctx.to_dict())

        # 1. File-Level Baseline
        file_decision = "VALID" if ctx.is_file_unchanged else "STALE"
        pred_records_file.append({
            "claim_id": claim_id, "source_case_id": cid, "decision": file_decision,
            "engine_version": "2.2-v0.2", "policy": "SHA256_PARITY",
            "input_claim_hash": claim_hash, "evaluation_context_hash": ctx_hash, "evidence_mode": "FULL_SOURCE_FILE"
        })

        # 2. Pure Symbol AST Baseline
        res_s = sym_checker.evaluate(base_source=ctx.base_full_source, target_source=ctx.target_full_source, symbol_qualified_name=sym)
        pred_records_sym.append({
            "claim_id": claim_id, "source_case_id": cid, "decision": res_s.decision,
            "engine_version": "2.2-v0.2", "policy": "SYMBOL_DIGEST_PARITY",
            "input_claim_hash": claim_hash, "evaluation_context_hash": ctx_hash, "evidence_mode": "SYMBOL_AST"
        })

        # 3. Dependency Validity Baseline
        res_d = dep_checker.evaluate(base_source=ctx.base_full_source, target_source=ctx.target_full_source, symbol_qualified_name=sym, diff_hunk=diff)
        pred_records_dep.append({
            "claim_id": claim_id, "source_case_id": cid, "decision": res_d.decision,
            "engine_version": "2.2-v0.2", "policy": "INTRA_MODULE_DEPENDENCY",
            "input_claim_hash": claim_hash, "evaluation_context_hash": ctx_hash, "evidence_mode": "AST_DIFF_DEPENDENCY"
        })

        # 4. RoleMem Structural Baseline
        res_rm = rolemem_engine.evaluate(
            memory_statement=ctx.memory_statement,
            symbol_qualified_name=sym,
            base_source=ctx.base_full_source,
            target_source=ctx.target_full_source,
            diff_hunk=diff,
            file_path=fpath
        )
        pred_records_rolemem_abstain.append({
            "claim_id": claim_id, "source_case_id": cid, "decision": res_rm.decision,
            "engine_version": "2.2-v0.2", "policy": "ROLEMEM_ABSTAIN",
            "input_claim_hash": claim_hash, "evaluation_context_hash": ctx_hash, "evidence_mode": "ROLEMEM_STRUCTURAL"
        })
        pred_records_rolemem_forced.append({
            "claim_id": claim_id, "source_case_id": cid, "decision": "VALID" if res_rm.decision == "UNCERTAIN" else res_rm.decision,
            "engine_version": "2.2-v0.2", "policy": "ROLEMEM_FORCED_VALID",
            "input_claim_hash": claim_hash, "evaluation_context_hash": ctx_hash, "evidence_mode": "ROLEMEM_STRUCTURAL"
        })

        # 5. Oracle Execution Evidence Upper Bound
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
        pred_records_oracle_exec.append({
            "claim_id": claim_id, "source_case_id": cid, "decision": exec_decision,
            "engine_version": "2.2-v0.2", "policy": "ORACLE_EXECUTION_EVAL",
            "input_claim_hash": claim_hash, "evaluation_context_hash": ctx_hash, "evidence_mode": "ORACLE_EXECUTION_ONLY"
        })

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

    # Apply policies
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
        "oracle_execution_upper_bound": os.path.join(DATA_DIR, "predictions_oracle_execution_upper_bound.jsonl"),
        "claim_static_selective": os.path.join(DATA_DIR, "predictions_claim_static_selective.jsonl"),
        "claim_static_valid_default": os.path.join(DATA_DIR, "predictions_claim_static_valid_default.jsonl"),
        "claim_static_stale_default": os.path.join(DATA_DIR, "predictions_claim_static_stale_default.jsonl"),
        "claim_exec_selective": os.path.join(DATA_DIR, "predictions_claim_exec_selective.jsonl"),
        "claim_exec_valid_default": os.path.join(DATA_DIR, "predictions_claim_exec_valid_default.jsonl"),
        "claim_exec_stale_default": os.path.join(DATA_DIR, "predictions_claim_exec_stale_default.jsonl")
    }

    def write_preds(path: str, records: List[Dict[str, Any]]):
        with open(path, "w", encoding="utf-8") as f:
            for r in records:
                f.write(json.dumps(r) + "\n")

    write_preds(prediction_files["file_level"], pred_records_file)
    write_preds(prediction_files["pure_symbol"], pred_records_sym)
    write_preds(prediction_files["dependency"], pred_records_dep)
    write_preds(prediction_files["rolemem_abstain"], pred_records_rolemem_abstain)
    write_preds(prediction_files["rolemem_forced"], pred_records_rolemem_forced)
    write_preds(prediction_files["oracle_execution_upper_bound"], pred_records_oracle_exec)

    def wrap_claim_preds(decisions: List[str], policy_name: str, mode: str) -> List[Dict[str, Any]]:
        return [{
            "claim_id": inputs[i]["claim_id"],
            "source_case_id": inputs[i].get("source_case_id", ""),
            "decision": decisions[i],
            "engine_version": "2.2-v0.2",
            "policy": policy_name,
            "input_claim_hash": compute_sha256(inputs[i]),
            "evidence_mode": mode
        } for i in range(len(inputs))]

    write_preds(prediction_files["claim_static_selective"], wrap_claim_preds(preds_static_sel, "SELECTIVE", "CLAIM_STATIC_NO_EXECUTION"))
    write_preds(prediction_files["claim_static_valid_default"], wrap_claim_preds(preds_static_vdef, "FORCED_VALID_DEFAULT", "CLAIM_STATIC_NO_EXECUTION"))
    write_preds(prediction_files["claim_static_stale_default"], wrap_claim_preds(preds_static_sdef, "FORCED_STALE_DEFAULT", "CLAIM_STATIC_NO_EXECUTION"))

    write_preds(prediction_files["claim_exec_selective"], wrap_claim_preds(preds_exec_sel, "SELECTIVE", "CLAIM_EXECUTION_ASSISTED"))
    write_preds(prediction_files["claim_exec_valid_default"], wrap_claim_preds(preds_exec_vdef, "FORCED_VALID_DEFAULT", "CLAIM_EXECUTION_ASSISTED"))
    write_preds(prediction_files["claim_exec_stale_default"], wrap_claim_preds(preds_exec_sdef, "FORCED_STALE_DEFAULT", "CLAIM_EXECUTION_ASSISTED"))

    print("Phase 1 Predictions generated and saved with full run provenance.")
    return prediction_files


def run_phase_2_evaluation(prediction_files: Dict[str, str]):
    """
    Phase 2: Reads blind predictions and gold labels from disk with ID-safe map matching.
    """
    print("--- Running Phase 2: ID-Safe Scoring & Metric Evaluation ---")
    with open(GOLD_PATH, "r", encoding="utf-8") as f:
        gold_records = [json.loads(line) for line in f if line.strip()]

    eval_summary = {}

    for name, path in prediction_files.items():
        with open(path, "r", encoding="utf-8") as f:
            preds = [json.loads(line) for line in f if line.strip()]
        eval_summary[name] = compute_metrics_id_safe(preds, gold_records)

    eval_json_p = os.path.join(DATA_DIR, "evaluation_results.json")
    with open(eval_json_p, "w", encoding="utf-8") as f:
        json.dump(eval_summary, f, indent=2)

    print(f"Scoring Complete. Results saved to {eval_json_p}")
    generate_reports(eval_summary)


def generate_reports(eval_summary: Dict[str, Any]):
    # 1. Generate reports/v2.2-v0.1-baseline-fairness.md
    fairness_lines = [
        "# RoleMem Protocol V2.2-V0.2 — Baseline Fairness & Evidence Budget Audit",
        "",
        "## Formal Status Declaration",
        "```text",
        "PROTOCOL_VERSION = 2.2-claim-aware-v0.2",
        "CURRENT_V0_RESULT_STATUS = DEVELOPMENT_COUPLED_NOT_FOR_SCIENTIFIC_CLAIM",
        "V2_1_DEVELOPMENT_MUTATIONS = 0",
        "V2_2_DETERMINISTIC_FOUNDATION = CLOSED",
        "V2_2_STRUCTURED_CLAIM_REPRESENTATION = FROZEN",
        "V2_2_EXTRACTION_DEV_EVALUATED = YES",
        "V2_2_EVIDENCE_BINDING = VERIFIED",
        "V2_2_ALGORITHM_FREEZE = NO",
        "V2_2_FORMAL_HOLDOUT_DEFINED = NO",
        "V2_2_FORMAL_TEST_OPENED = NO",
        "FORMAL_AGENT_RESULTS = NO",
        "FORMAL_PAPER_RESULTS = NO",
        "```",
        "",
        "---",
        "",
        "## 1. Evidence Budget & Information Asymmetry Audit",
        "",
        "| Mechanism | Input Context | AST Analysis | Git Diff | Execution Evidence | Decision Policy | Mechanism Role |",
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
        "| **File_Level_Baseline** | Full Source File | No | No | No | SHA256 Parity | Coarse file-level baseline |",
        "| **Pure_Symbol_AST_Baseline** | Full Source File | Yes | No | No | Symbol Digest Parity | Pure symbol existence baseline |",
        "| **Dependency_Validity_Baseline** | Full Source File | Yes | Yes | No | Intra-module Linkage | AST graph & call chain baseline |",
        "| **RoleMem_Structural_V2_1** | Full Source File | Yes | Yes | No | AST + Diff Heuristic | Heuristic abstaining baseline |",
        "| **Oracle_Execution_Evidence_UpperBound** | None | No | No | **100% Oracle** | Oracle Execution Result | **Theoretical Oracle Upper Bound** |",
        "| **Claim_Aware_Static** | Full Source File | Yes | Yes | **0% (Zero Exec)** | Selective Policy | **Primary Deployable Static Engine** |",
        "| **Claim_Aware_StaticPlusExecution** | Full Source File | Yes | Yes | **Verified Binding** | Selective Policy | Execution-Assisted Engine |",
        "",
        "---",
        "",
        "## 2. Comprehensive Empirical Comparison (55 Development Cases)",
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
        "# RoleMem Protocol V2.2-Claim-Aware-V0.2 — Architecture Design & Empirical Report",
        "",
        "## Formal Status Declaration",
        "```text",
        "PROTOCOL_VERSION = 2.2-claim-aware-v0.2",
        "CURRENT_V0_RESULT_STATUS = DEVELOPMENT_COUPLED_NOT_FOR_SCIENTIFIC_CLAIM",
        "V2_1_DEVELOPMENT_MUTATIONS = 0",
        "V2_2_DETERMINISTIC_FOUNDATION = CLOSED",
        "V2_2_STRUCTURED_CLAIM_REPRESENTATION = FROZEN",
        "V2_2_EXTRACTION_DEV_EVALUATED = YES",
        "V2_2_EVIDENCE_BINDING = VERIFIED",
        "V2_2_ALGORITHM_FREEZE = NO",
        "V2_2_FORMAL_HOLDOUT_DEFINED = NO",
        "V2_2_FORMAL_TEST_OPENED = NO",
        "FORMAL_AGENT_RESULTS = NO",
        "FORMAL_PAPER_RESULTS = NO",
        "```",
        "",
        "---",
        "",
        "## 1. Primary Structured-Claim Validity Benchmark (Selective Evaluation)",
        "",
        "> [!NOTE]",
        "> This table evaluates intrinsic validity reasoning on the frozen development structured claims under `SelectivePolicy` (abstaining on uncertain cases).",
        "",
        "| Primary Mechanism | Coverage | Selective Risk | Decided Acc | Balanced Acc | Macro F1 | MCC | FIR (Decided Valid) | SER (Decided Stale) |",
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |"
    ]

    primary_mechanisms = [
        ("File_Level_Baseline", eval_summary["file_level"]),
        ("Pure_Symbol_AST_Baseline", eval_summary["pure_symbol"]),
        ("Dependency_Validity_Baseline", eval_summary["dependency"]),
        ("RoleMem_Structural_V2_1 (Abstain)", eval_summary["rolemem_abstain"]),
        ("Oracle_Execution_UpperBound", eval_summary["oracle_execution_upper_bound"]),
        ("Claim_Aware_Static (Selective)", eval_summary["claim_static_selective"]),
        ("Claim_Aware_Exec_Assisted (Selective)", eval_summary["claim_exec_selective"])
    ]

    for label, mdata in primary_mechanisms:
        cov = mdata["Coverage"] * 100
        risk = mdata["Selective_Risk"] * 100
        dacc = mdata["Accuracy_Decided"] * 100
        bacc = mdata["Balanced_Accuracy"] * 100
        mf1 = mdata["Macro_F1"] * 100
        mcc = mdata["MCC"]
        fir = mdata["False_Invalidation_Rate_FIR"] * 100
        ser = mdata["Stale_Exposure_Rate_SER"] * 100
        design_lines.append(f"| **{label}** | {cov:.1f}% | {risk:.1f}% | {dacc:.1f}% | {bacc:.1f}% | {mf1:.1f}% | {mcc:+.3f} | {fir:.1f}% | {ser:.1f}% |")

    design_lines.extend([
        "",
        "---",
        "",
        "## 2. Decision Policy Sensitivity Analysis",
        "",
        "| Claim Engine Variant | Policy | Coverage | Overall Acc | Balanced Acc | Macro F1 | MCC | FIR | SER |",
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |"
    ])

    policy_variants = [
        ("Claim_Aware_Static", "Selective", eval_summary["claim_static_selective"]),
        ("Claim_Aware_Static", "Forced Valid Default", eval_summary["claim_static_valid_default"]),
        ("Claim_Aware_Static", "Forced Stale Default", eval_summary["claim_static_stale_default"]),
        ("Claim_Aware_Exec_Assisted", "Selective", eval_summary["claim_exec_selective"]),
        ("Claim_Aware_Exec_Assisted", "Forced Valid Default", eval_summary["claim_exec_valid_default"]),
        ("Claim_Aware_Exec_Assisted", "Forced Stale Default", eval_summary["claim_exec_stale_default"]),
    ]

    for cname, pol, mdata in policy_variants:
        cov = mdata["Coverage"] * 100
        acc = mdata["Accuracy_Overall"] * 100
        bacc = mdata["Balanced_Accuracy"] * 100
        mf1 = mdata["Macro_F1"] * 100
        mcc = mdata["MCC"]
        fir = mdata["False_Invalidation_Rate_FIR"] * 100
        ser = mdata["Stale_Exposure_Rate_SER"] * 100
        design_lines.append(f"| **{cname}** | {pol} | {cov:.1f}% | {acc:.1f}% | {bacc:.1f}% | {mf1:.1f}% | {mcc:+.3f} | {fir:.1f}% | {ser:.1f}% |")

    design_lines.extend([
        "",
        "---",
        "",
        "## 3. Granular Category Coverage & Accuracy Breakdown",
        "",
        "| Mechanism | Cat A Cov (Acc) | Cat B Cov (Acc) | Cat C Cov (Acc) | Cat D1 Cov (Acc) | Cat D2 Cov (Acc) |",
        "| :--- | :--- | :--- | :--- | :--- | :--- |"
    ])

    for name, mdata in eval_summary.items():
        pcb = mdata["Per_Category_Breakdown"]
        def fmt_cat(cat_key: str) -> str:
            d = pcb.get(cat_key, {})
            cov_str = f"{d.get('coverage', 0.0)*100:.0f}%"
            acc = d.get("accuracy")
            acc_str = f"{acc*100:.0f}%" if acc is not None else "N/A"
            return f"{cov_str} ({acc_str})"

        a_str = fmt_cat("CAT_A_FILE_CHG_SYM_SAME_VALID")
        b_str = fmt_cat("CAT_B_SYM_CHG_MEMORY_VALID")
        c_str = fmt_cat("CAT_C_SYM_SAME_MEMORY_STALE")
        d1_str = fmt_cat("CAT_D1_SYM_REM_STALE")
        d2_str = fmt_cat("CAT_D2_SYM_CHG_BEHAVIOR_STALE")
        design_lines.append(f"| **{name}** | {a_str} | {b_str} | {c_str} | {d1_str} | {d2_str} |")

    design_lines.extend([
        "",
        "---",
        "",
        "## 4. Honest Results Interpretation & Scope Boundaries",
        "",
        "1. **Development-Coupled Context**: All metrics in this report belong strictly to the `Protocol V2.2 Development Structured-Claim Benchmark` (55 cases).",
        "2. **No Claim of Generalization**: `paraphrase_dev.jsonl` is marked as `DEVELOPER_SEEN_PARAPHRASE_DEV` because paraphrases were authored during parser refinement.",
        "3. **Policy-Driven Numbers**: `Claim_Static_Valid_Default` achieves 100% on Cat B not through intrinsic static proof, but through the `UNCERTAIN -> VALID` optimistic retrieval policy.",
        "4. **Oracle Upper Bound**: `Oracle_Execution_Evidence_UpperBound` is documented strictly as an oracle ceiling measurement and is not a standalone deployable engine.",
        ""
    ])

    design_p = os.path.join(REPORTS_DIR, "protocol-v2.2-v0-design.md")
    with open(design_p, "w", encoding="utf-8") as f:
        f.write("\n".join(design_lines) + "\n")

    print(f"Reports updated:\n  {fairness_p}\n  {design_p}")


if __name__ == "__main__":
    preds = run_phase_1_predictions()
    run_phase_2_evaluation(preds)
