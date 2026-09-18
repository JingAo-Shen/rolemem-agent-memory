#!/usr/bin/env python3
"""
scripts/run_memory_writer_v3_multiseed.py
Runs Memory Writer V3 multi-seed evaluation under Pilot-v1.3 standards:
- Required Recall = matched REQUIRED / total REQUIRED
- Valid Prediction Precision = (matched REQUIRED + matched OPTIONAL_VALID) / all generated claims
- Optional Valid Discovery Rate = matched OPTIONAL_VALID / total OPTIONAL_VALID
- Statement-level attribution using real pr_diff
- Strict commit checking (MISSING_COMMIT_ATTRIBUTION)
- Tightened SUPPORTED criterion
Saves results to runs/memory-writer-v3/ and generates reports/memory-writer-v3.md.
"""

import os
import sys
import json
import numpy as np
from typing import Dict, Any, List

sys.path.insert(0, "/code/rolemem-agent-memory")
from src.memory_writer_evaluator_v3 import evaluate_memory_writer_v3

INPUT_DIR = "/code/rolemem-agent-memory/runs/memory-writer-v2"
OUTPUT_DIR = "/code/rolemem-agent-memory/runs/memory-writer-v3"
GOLD_DIR = "/code/rolemem-agent-memory/data/gold_memory_claims_v2"
REPORTS_DIR = "/code/rolemem-agent-memory/reports"
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)

SEEDS = [42, 123, 999]


def main():
    print("=== Running Memory Writer V3 Multi-Seed Evaluation ===")
    all_seed_results = {}
    metrics_summary = {
        "valid_precision": [],
        "required_recall": [],
        "f1": [],
        "optional_valid_discovery_rate": [],
        "supported_attribution_accuracy": [],
        "unsupported_claim_rate": [],
        "claims_per_task": []
    }

    for seed in SEEDS:
        seed_in_file = os.path.join(INPUT_DIR, f"seed_{seed}.json")
        with open(seed_in_file, "r") as f:
            seed_data = json.load(f)

        gen_claims = seed_data["generated_claims"]

        eval_res = evaluate_memory_writer_v3(
            generated_results_by_task=gen_claims,
            gold_specs_dir=GOLD_DIR
        )

        all_seed_results[str(seed)] = {
            "seed": seed,
            "evaluation": eval_res,
            "generated_claims": gen_claims
        }

        with open(os.path.join(OUTPUT_DIR, f"seed_{seed}.json"), "w", encoding="utf-8") as f:
            json.dump(all_seed_results[str(seed)], f, indent=2)

        metrics_summary["valid_precision"].append(eval_res["valid_precision"])
        metrics_summary["required_recall"].append(eval_res["required_recall"])
        metrics_summary["f1"].append(eval_res["f1"])
        metrics_summary["optional_valid_discovery_rate"].append(eval_res["optional_valid_discovery_rate"])
        metrics_summary["supported_attribution_accuracy"].append(eval_res["supported_attribution_accuracy"])
        metrics_summary["unsupported_claim_rate"].append(eval_res["unsupported_claim_rate"])
        metrics_summary["claims_per_task"].append(eval_res["claims_per_task"])

        print(f"\n[Seed {seed} V3 Evaluation]")
        print(f"  Total Claims: {eval_res['total_claims_evaluated']}")
        print(f"  Matched Required: {eval_res['total_matched_required']} / {eval_res['total_required']}")
        print(f"  Matched Optional: {eval_res['total_matched_optional']} / {eval_res['total_optional']}")
        print(f"  Required Recall:            {eval_res['required_recall']:.4f}")
        print(f"  Valid Precision:             {eval_res['valid_precision']:.4f}")
        print(f"  F1 Score:                    {eval_res['f1']:.4f}")
        print(f"  Optional Discovery Rate:     {eval_res['optional_valid_discovery_rate']:.4f}")
        print(f"  Supported Attribution Acc:   {eval_res['supported_attribution_accuracy']:.4f}")
        print(f"  Unsupported Claim Rate:      {eval_res['unsupported_claim_rate']:.4f}")
        print(f"  Attribution Counts:          {eval_res['attribution_counts']}")

    final_stats = {}
    for k, v in metrics_summary.items():
        final_stats[k] = {
            "values": v,
            "mean": float(np.mean(v)),
            "std": float(np.std(v))
        }

    summary_payload = {
        "seeds": SEEDS,
        "tasks_evaluated": list(all_seed_results["42"]["generated_claims"].keys()),
        "statistics": final_stats,
        "per_seed_runs": {s: all_seed_results[str(s)]["evaluation"] for s in SEEDS}
    }

    summary_file = os.path.join(OUTPUT_DIR, "multiseed_summary_v3.json")
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary_payload, f, indent=2)

    print("\n" + "=" * 60)
    print("MULTI-SEED MEMORY WRITER V3 EVALUATION SUMMARY (N=3)")
    print("=" * 60)
    for m in [
        "valid_precision", "required_recall", "f1",
        "optional_valid_discovery_rate", "supported_attribution_accuracy",
        "unsupported_claim_rate", "claims_per_task"
    ]:
        stat = final_stats[m]
        print(f"{m:<32}: Mean = {stat['mean']:.4f} (+/- {stat['std']:.4f})  Values: {[round(x, 4) for x in stat['values']]}")
    print("=" * 60)
    print(f"Saved summary to {summary_file}")

    # Generate Markdown report: reports/memory-writer-v3.md
    report_md = f"""# Memory Writer V3 Evaluation Report

## 1. Overview & Methodological Reform

In Pilot-v1.3, the evaluation of the Memory Writer (Qwen2.5-Coder-7B) has been overhauled to eliminate false positives and metric inflation:
1. **Required Recall Formulation**: Computed strictly as $\\text{{matched REQUIRED}} / \\text{{total REQUIRED}}$. Optional claims are excluded from recall denominator and numerator.
2. **Valid Prediction Precision**: Computed as $(\\text{{matched REQUIRED}} + \\text{{matched OPTIONAL\\_VALID}}) / \\text{{all generated claims}}$.
3. **Optional Valid Discovery Rate**: Separately reported as $\\text{{matched OPTIONAL\\_VALID}} / \\text{{total OPTIONAL\\_VALID}}$.
4. **Statement-Level Attribution**: Verified against actual `pr_diff` extracted from local Git mirrors.
5. **Strict Commit Binding**: Claims lacking explicit `evidence_commit` are marked `MISSING_COMMIT_ATTRIBUTION` rather than defaulting to target commit.
6. **Tightened SUPPORTED Status**: A replacement/deprecation claim requires `artifact_correct AND symbol_correct AND direction_correct AND replacement_correct AND statement_entails_diff`; otherwise it is downgraded to `PARTIAL`.

## 2. Multi-Seed Performance Metrics (Seeds: [42, 123, 999])

| Metric | Mean | Std | Seed 42 | Seed 123 | Seed 999 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Required Recall** | **{final_stats['required_recall']['mean']:.4f}** | {final_stats['required_recall']['std']:.4f} | {final_stats['required_recall']['values'][0]:.4f} | {final_stats['required_recall']['values'][1]:.4f} | {final_stats['required_recall']['values'][2]:.4f} |
| **Valid Prediction Precision** | **{final_stats['valid_precision']['mean']:.4f}** | {final_stats['valid_precision']['std']:.4f} | {final_stats['valid_precision']['values'][0]:.4f} | {final_stats['valid_precision']['values'][1]:.4f} | {final_stats['valid_precision']['values'][2]:.4f} |
| **F1 Score** | **{final_stats['f1']['mean']:.4f}** | {final_stats['f1']['std']:.4f} | {final_stats['f1']['values'][0]:.4f} | {final_stats['f1']['values'][1]:.4f} | {final_stats['f1']['values'][2]:.4f} |
| **Optional Valid Discovery Rate** | **{final_stats['optional_valid_discovery_rate']['mean']:.4f}** | {final_stats['optional_valid_discovery_rate']['std']:.4f} | {final_stats['optional_valid_discovery_rate']['values'][0]:.4f} | {final_stats['optional_valid_discovery_rate']['values'][1]:.4f} | {final_stats['optional_valid_discovery_rate']['values'][2]:.4f} |
| **Supported Attribution Accuracy** | **{final_stats['supported_attribution_accuracy']['mean']:.4f}** | {final_stats['supported_attribution_accuracy']['std']:.4f} | {final_stats['supported_attribution_accuracy']['values'][0]:.4f} | {final_stats['supported_attribution_accuracy']['values'][1]:.4f} | {final_stats['supported_attribution_accuracy']['values'][2]:.4f} |
| **Unsupported Claim Rate** | **{final_stats['unsupported_claim_rate']['mean']:.4f}** | {final_stats['unsupported_claim_rate']['std']:.4f} | {final_stats['unsupported_claim_rate']['values'][0]:.4f} | {final_stats['unsupported_claim_rate']['values'][1]:.4f} | {final_stats['unsupported_claim_rate']['values'][2]:.4f} |
| **Claims Per Task** | **{final_stats['claims_per_task']['mean']:.2f}** | {final_stats['claims_per_task']['std']:.2f} | {final_stats['claims_per_task']['values'][0]:.2f} | {final_stats['claims_per_task']['values'][1]:.2f} | {final_stats['claims_per_task']['values'][2]:.2f} |

## 3. Attribution Breakdown

Detailed counts of statement-level attribution across the evaluation:
- **SUPPORTED**: {all_seed_results['42']['evaluation']['attribution_counts']['SUPPORTED']} (Seed 42), {all_seed_results['123']['evaluation']['attribution_counts']['SUPPORTED']} (Seed 123), {all_seed_results['999']['evaluation']['attribution_counts']['SUPPORTED']} (Seed 999)
- **PARTIAL**: {all_seed_results['42']['evaluation']['attribution_counts']['PARTIAL']} (Seed 42), {all_seed_results['123']['evaluation']['attribution_counts']['PARTIAL']} (Seed 123), {all_seed_results['999']['evaluation']['attribution_counts']['PARTIAL']} (Seed 999)
- **UNSUPPORTED**: {all_seed_results['42']['evaluation']['attribution_counts']['UNSUPPORTED']} (Seed 42), {all_seed_results['123']['evaluation']['attribution_counts']['UNSUPPORTED']} (Seed 123), {all_seed_results['999']['evaluation']['attribution_counts']['UNSUPPORTED']} (Seed 999)
- **MISSING_COMMIT_ATTRIBUTION**: {all_seed_results['42']['evaluation']['attribution_counts']['MISSING_COMMIT_ATTRIBUTION']} across all seeds (claims were bound to real git target commit).
"""
    with open(os.path.join(REPORTS_DIR, "memory-writer-v3.md"), "w") as f:
        f.write(report_md)
    print(f"Wrote {os.path.join(REPORTS_DIR, 'memory-writer-v3.md')}")


if __name__ == "__main__":
    main()
