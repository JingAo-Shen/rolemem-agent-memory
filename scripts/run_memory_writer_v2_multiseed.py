#!/usr/bin/env python3
"""
scripts/run_memory_writer_v2_multiseed.py
Runs Real Agent A Memory Writer across multiple seeds [42, 123, 999] on Qwen2.5-Coder-7B.
Evaluates with MemoryWriterEvaluatorV2 (bipartite matching, gold status, statement-level attribution).
Saves individual run results and computes mean and std for all metrics.
"""

import os
import sys
import json
import numpy as np
import torch

sys.path.insert(0, "/code/rolemem-agent-memory")
from src.memory_writer_v1 import RealAgentAMemoryWriter
from src.memory_writer_evaluator_v2 import evaluate_memory_writer_v2

OUTPUT_DIR = "/code/rolemem-agent-memory/runs/memory-writer-v2"
os.makedirs(OUTPUT_DIR, exist_ok=True)

GOLD_DIR = "/code/rolemem-agent-memory/data/gold_memory_claims_v2"
SEEDS = [42, 123, 999]

TASKS = [
    {
        "tid": "trans_gold_click_02_isolated_filesystem",
        "repo_path": "/code/repo_cache/click",
        "base_commit": "333c28d79cd982990ee98eef61ec20ab1a4f38ba",
        "target_commit": "cfa01eeb7894a408af70b29d28c0b24f8680f9fb"
    },
    {
        "tid": "trans_gold_requests_01_tls_context_adapter",
        "repo_path": "/code/repo_cache/requests",
        "base_commit": "970e8cec988421bd43da57350723b05c8ce8dc7e",
        "target_commit": "c98e4d133ef29c46a9b68cd783087218a8075e05"
    },
    {
        "tid": "trans_gold_urllib3_01_retry_allowed_methods",
        "repo_path": "/code/repo_cache/urllib3",
        "base_commit": "6d38f171c4921043e1ff633e2a3e9f7ea382e1d5",
        "target_commit": "382ab32f23795c44faae83b4e8b18a16fb605a0a"
    },
    {
        "tid": "trans_gold_werkzeug_01_cached_property",
        "repo_path": "/code/repo_cache/werkzeug",
        "base_commit": "25ca9cd92956e48a38f7a32c837e0f8a54c8ae31",
        "target_commit": "f50fbf5659875821c19ae21b237b4290b12e1e2d"
    }
]


def main():
    print(f"Initializing Qwen2.5-Coder-7B Memory Writer across {len(SEEDS)} seeds: {SEEDS}...")
    writer = RealAgentAMemoryWriter()

    all_seed_results = {}
    metrics_summary = {
        "precision": [],
        "recall": [],
        "f1": [],
        "supported_attribution_accuracy": [],
        "unsupported_claim_rate": [],
        "claims_per_task": [],
        "tp": [],
        "fp": [],
        "fn": []
    }

    for seed in SEEDS:
        print(f"\n================ Running Memory Writer Seed {seed} ================")
        generated_by_task = {}
        for t in TASKS:
            tid = t["tid"]
            print(f"  Extracting claims for {tid}...")
            raw_text, claims = writer.generate_memory_claims(
                repo_path=t["repo_path"],
                base_commit=t["base_commit"],
                target_commit=t["target_commit"],
                seed=seed
            )
            # Tag claims with evidence commit
            for c in claims:
                c["evidence_commit"] = t["target_commit"]
                c["claim_id"] = f"{tid}_{c.get('symbol', 'claim')}_{seed}"
            generated_by_task[tid] = claims
            print(f"    Generated {len(claims)} claims: {[c.get('symbol') for c in claims]}")

        # Evaluate seed
        eval_res = evaluate_memory_writer_v2(
            generated_results_by_task=generated_by_task,
            gold_specs_dir=GOLD_DIR
        )

        all_seed_results[str(seed)] = {
            "seed": seed,
            "evaluation": eval_res,
            "generated_claims": generated_by_task
        }

        # Save single seed run
        with open(os.path.join(OUTPUT_DIR, f"seed_{seed}.json"), "w", encoding="utf-8") as f:
            json.dump(all_seed_results[str(seed)], f, indent=2)

        # Collect metrics
        metrics_summary["precision"].append(eval_res["precision"])
        metrics_summary["recall"].append(eval_res["recall"])
        metrics_summary["f1"].append(eval_res["f1"])
        metrics_summary["supported_attribution_accuracy"].append(eval_res["supported_attribution_accuracy"])
        metrics_summary["unsupported_claim_rate"].append(eval_res["unsupported_claim_rate"])
        metrics_summary["claims_per_task"].append(eval_res["claims_per_task"])
        metrics_summary["tp"].append(eval_res["total_tp"])
        metrics_summary["fp"].append(eval_res["total_fp"])
        metrics_summary["fn"].append(eval_res["total_fn"])

        print(f"  [Seed {seed} Results]")
        print(f"    TP: {eval_res['total_tp']}, FP: {eval_res['total_fp']}, FN: {eval_res['total_fn']}")
        print(f"    Precision: {eval_res['precision']:.4f}")
        print(f"    Recall:    {eval_res['recall']:.4f}")
        print(f"    F1:        {eval_res['f1']:.4f}")
        print(f"    Supported Attribution: {eval_res['supported_attribution_accuracy']:.4f}")
        print(f"    Unsupported Claim Rate: {eval_res['unsupported_claim_rate']:.4f}")
        print(f"    Claims Per Task: {eval_res['claims_per_task']:.2f}")

    # Compute mean and std
    final_stats = {}
    for k, v in metrics_summary.items():
        final_stats[k] = {
            "values": v,
            "mean": float(np.mean(v)),
            "std": float(np.std(v))
        }

    summary_payload = {
        "seeds": SEEDS,
        "tasks_evaluated": [t["tid"] for t in TASKS],
        "statistics": final_stats,
        "per_seed_runs": {s: all_seed_results[str(s)]["evaluation"] for s in SEEDS}
    }

    summary_file = os.path.join(OUTPUT_DIR, "multiseed_summary.json")
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary_payload, f, indent=2)

    print("\n" + "=" * 60)
    print("MULTI-SEED MEMORY WRITER V2 EVALUATION SUMMARY (N=3)")
    print("=" * 60)
    for m in ["precision", "recall", "f1", "supported_attribution_accuracy", "unsupported_claim_rate", "claims_per_task"]:
        stat = final_stats[m]
        print(f"{m:<32}: Mean = {stat['mean']:.4f} (+/- {stat['std']:.4f})  Values: {[round(x, 4) for x in stat['values']]}")
    print("=" * 60)
    print(f"Saved full evaluation outputs to {summary_file}")


if __name__ == "__main__":
    main()
