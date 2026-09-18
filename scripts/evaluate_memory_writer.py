"""
scripts/evaluate_memory_writer.py
Evaluates Real Agent A Memory Writer across 4 tasks on Qwen2.5-Coder-7B.
Computes real Precision, Recall, F1, and non-tautological Evidence Attribution Accuracy.
Saves all raw generations to runs/memory-writer/<task>/seed_<seed>.json.
"""

import os
import sys
import json
import torch
import subprocess
from typing import Dict, Any, List

sys.path.insert(0, "/code/rolemem-agent-memory")
from src.memory_writer_v1 import RealAgentAMemoryWriter
from transformers import AutoTokenizer, AutoModelForCausalLM

REPO_MAP = {
    "pallets/werkzeug": "/code/repo_cache/werkzeug",
    "pallets/click": "/code/repo_cache/click",
    "psf/requests": "/code/repo_cache/requests",
    "urllib3/urllib3": "/code/repo_cache/urllib3",
}

TASKS = [
    "trans_gold_werkzeug_01_cached_property",
    "trans_gold_click_02_isolated_filesystem",
    "trans_gold_requests_01_tls_context_adapter",
    "trans_gold_urllib3_01_retry_allowed_methods",
]

OUTPUT_DIR = "/code/rolemem-agent-memory/runs/memory-writer"


def verify_evidence_attribution(repo_path: str, base_commit: str, target_commit: str, claim: Dict[str, Any]) -> bool:
    """
    Non-tautological Evidence Attribution:
    Verifies that the claimed artifact_uri and symbol actually appear in the modified hunks of git diff.
    """
    uri = claim.get("artifact_uri", "")
    sym = claim.get("symbol", "")
    if not uri:
        return False
    try:
        # Check if file is modified in the commit diff
        diff = subprocess.check_output(
            ["git", "-C", repo_path, "diff", f"{base_commit}..{target_commit}", "--", uri],
            stderr=subprocess.DEVNULL
        ).decode("utf-8", errors="ignore")
        if not diff.strip():
            return False
        # Check if symbol or changed logic appears in diff
        if sym and sym.lower() in diff.lower():
            return True
        # If symbol name is qualified or generic, check statement keywords in diff
        stmt = claim.get("statement", "").lower()
        words = [w for w in sym.split(".") if len(w) > 3]
        for w in words:
            if w.lower() in diff.lower():
                return True
        return False
    except Exception:
        return False


def run_evaluation():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    model_dir = "/code/rolemem-agent-memory/models/qwen2.5-coder-7b"
    print(f"Loading Qwen2.5-Coder-7B from {model_dir}...")
    tokenizer = AutoTokenizer.from_pretrained(model_dir, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        model_dir,
        torch_dtype=torch.float16,
        device_map="auto"
    )
    model.eval()

    writer = RealAgentAMemoryWriter(model_dir=model_dir, tokenizer=tokenizer, model=model)

    task_metrics = []
    total_tp = 0
    total_fp = 0
    total_fn = 0
    total_claims = 0
    attributed_claims = 0

    seeds = [42]  # representative run

    for tid in TASKS:
        gold_file = f"/code/rolemem-agent-memory/data/gold_memory_claims/{tid}.json"
        with open(gold_file) as f:
            gold_data = json.load(f)

        repo_name = gold_data["repo_name"]
        repo_path = REPO_MAP[repo_name]
        base_commit = gold_data["base_commit"]
        target_commit = gold_data["target_commit"]
        gold_claims = gold_data["gold_claims"]
        distractor_files = set(gold_data.get("distractor_files", []))

        print(f"\n========================================================")
        print(f"Evaluating Memory Writer on Task: {tid}")
        print(f"========================================================")

        task_dir = os.path.join(OUTPUT_DIR, tid)
        os.makedirs(task_dir, exist_ok=True)

        for seed in seeds:
            gen_text, extracted_claims = writer.generate_memory_claims(
                repo_path, base_commit, target_commit, seed=seed
            )

            records = writer.build_memory_records(
                tid, repo_path, base_commit, target_commit, extracted_claims
            )

            run_log = {
                "task_id": tid,
                "seed": seed,
                "base_commit": base_commit,
                "target_commit": target_commit,
                "raw_generation": gen_text,
                "parsed_claims": extracted_claims,
                "memory_records": [r.to_dict() for r in records]
            }

            log_p = os.path.join(task_dir, f"seed_{seed}.json")
            with open(log_p, "w") as f:
                json.dump(run_log, f, indent=2)
            print(f"Saved raw writer telemetry to {log_p}")

            # Compute TP, FP, FN
            tp = 0
            fp = 0
            covered_gold = set()

            for c in extracted_claims:
                total_claims += 1
                uri = c.get("artifact_uri", "")
                stmt = c.get("statement", "").lower()
                sym = c.get("symbol", "").lower()

                # Evidence attribution verification
                is_attributed = verify_evidence_attribution(repo_path, base_commit, target_commit, c)
                if is_attributed:
                    attributed_claims += 1

                # Match against gold
                matched_gold = False
                for g in gold_claims:
                    gid = g["claim_id"]
                    g_uri = g["artifact_uri"]
                    g_sym = g["symbol"].lower()
                    kw_matches = sum(1 for kw in g["core_fact_keywords"] if kw.lower() in stmt or kw.lower() in sym)

                    if uri == g_uri and (g_sym in sym or g_sym in stmt or kw_matches >= 2):
                        tp += 1
                        covered_gold.add(gid)
                        matched_gold = True
                        break

                if not matched_gold:
                    # Check if it targeted a distractor or hallucination
                    fp += 1

            fn = len(gold_claims) - len(covered_gold)

            prec = round(tp / (tp + fp), 4) if (tp + fp) > 0 else 0.0
            rec = round(tp / (tp + fn), 4) if (tp + fn) > 0 else 0.0
            f1 = round(2 * prec * rec / (prec + rec), 4) if (prec + rec) > 0 else 0.0

            total_tp += tp
            total_fp += fp
            total_fn += fn

            print(f"Claims Extracted: {len(extracted_claims)}")
            print(f"  TP={tp}, FP={fp}, FN={fn} -> Precision={prec}, Recall={rec}, F1={f1}")

            task_metrics.append({
                "task_id": tid,
                "seed": seed,
                "claims_count": len(extracted_claims),
                "tp": tp,
                "fp": fp,
                "fn": fn,
                "precision": prec,
                "recall": rec,
                "f1": f1
            })

    overall_prec = round(total_tp / (total_tp + total_fp), 4) if (total_tp + total_fp) > 0 else 0.0
    overall_rec = round(total_tp / (total_tp + total_fn), 4) if (total_tp + total_fn) > 0 else 0.0
    overall_f1 = round(2 * overall_prec * overall_rec / (overall_prec + overall_rec), 4) if (overall_prec + overall_rec) > 0 else 0.0
    attribution_acc = round(attributed_claims / total_claims, 4) if total_claims > 0 else 0.0

    summary = {
        "tasks_evaluated": len(TASKS),
        "total_claims_extracted": total_claims,
        "total_tp": total_tp,
        "total_fp": total_fp,
        "total_fn": total_fn,
        "precision": overall_prec,
        "recall": overall_rec,
        "f1_score": overall_f1,
        "evidence_attribution_accuracy": attribution_acc,
        "task_breakdown": task_metrics
    }

    summary_p = os.path.join(OUTPUT_DIR, "memory_writer_evaluation_summary.json")
    with open(summary_p, "w") as f:
        json.dump(summary, f, indent=2)

    print("\n========================================================")
    print("Agent A Memory Writer Evaluation Summary")
    print(f"Overall Precision: {overall_prec} ({total_tp}/{total_tp + total_fp})")
    print(f"Overall Recall:    {overall_rec} ({total_tp}/{total_tp + total_fn})")
    print(f"Overall F1-Score:  {overall_f1}")
    print(f"Evidence Attribution Accuracy: {attribution_acc} ({attributed_claims}/{total_claims})")
    print(f"Saved summary to {summary_p}")
    print("========================================================")


if __name__ == "__main__":
    run_evaluation()
