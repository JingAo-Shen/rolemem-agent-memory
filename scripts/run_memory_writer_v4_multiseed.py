#!/usr/bin/env python3
"""
scripts/run_memory_writer_v4_multiseed.py
Runs Memory Writer V4 multi-seed evaluation under Pilot-v1.3-r1 standards:
- Symbol Normalization (unqualified vs qualified)
- Structural Attribution Consistency (exact target commit + diff artifact check)
- Semantic Entailment Judge (direction + replacement + diff entailment)
- Evaluates multi-seed runs (42, 123, 999)
- Outputs to runs/memory-writer-v4/ and generates reports/memory-writer-v4.md
"""

import os
import sys
import json
import numpy as np
from typing import Dict, Any, List

sys.path.insert(0, "/code/rolemem-agent-memory")
from src.memory_writer_evaluator_v4 import evaluate_memory_writer_v4

INPUT_DIR = "/code/rolemem-agent-memory/runs/memory-writer-v2"
OUTPUT_DIR = "/code/rolemem-agent-memory/runs/memory-writer-v4"
GOLD_DIR = "/code/rolemem-agent-memory/data/gold_memory_claims_v2"
REPORTS_DIR = "/code/rolemem-agent-memory/reports"
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)

SEEDS = [42, 123, 999]


def main():
    print("=== Running Memory Writer V4 Multi-Seed Evaluation ===")
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
        with open(seed_in_file, "r", encoding="utf-8") as f:
            seed_data = json.load(f)

        gen_claims = seed_data["generated_claims"]

        eval_res = evaluate_memory_writer_v4(
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

        print(f"\n[Seed {seed} V4 Evaluation]")
        print(f"  Total Claims:                {eval_res['total_claims_evaluated']}")
        print(f"  Matched Required:            {eval_res['total_matched_required']} / {eval_res['total_required']}")
        print(f"  Matched Optional:            {eval_res['total_matched_optional']} / {eval_res['total_optional']}")
        print(f"  Required Recall:             {eval_res['required_recall']:.4f}")
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

    summary_out = os.path.join(OUTPUT_DIR, "multiseed_summary_v4.json")
    with open(summary_out, "w", encoding="utf-8") as f:
        json.dump(summary_payload, f, indent=2)

    # Generate Markdown Report
    generate_markdown_report(final_stats, summary_payload)
    print(f"\nWrote multi-seed summary to {summary_out}")


def generate_markdown_report(stats: Dict[str, Any], payload: Dict[str, Any]):
    report_file = os.path.join(REPORTS_DIR, "memory-writer-v4.md")
    lines = [
        "# Pilot-v1.3-r1 — Memory Writer V4 Multi-Seed Evaluation Report",
        "",
        "## 1. Executive Summary",
        "",
        "Memory Writer Evaluator V4 introduces strict Symbol Normalization (handling fully qualified vs unqualified symbols), Structural Attribution Consistency (verifying exact git commit and diff hunk presence), and a Semantic Entailment Judge (direction and replacement validation).",
        "",
        "## 2. Multi-Seed Aggregate Performance",
        "",
        f"- **Seeds Evaluated**: `{payload['seeds']}`",
        f"- **Tasks Evaluated**: `{len(payload['tasks_evaluated'])}` ({', '.join(payload['tasks_evaluated'])})",
        "",
        "| Metric | Mean ± Std | Seed 42 | Seed 123 | Seed 999 |",
        "| :--- | :---: | :---: | :---: | :---: |",
    ]

    metric_labels = [
        ("Required Recall", "required_recall"),
        ("Valid Prediction Precision", "valid_precision"),
        ("F1 Score", "f1"),
        ("Optional Valid Discovery Rate", "optional_valid_discovery_rate"),
        ("Supported Attribution Accuracy", "supported_attribution_accuracy"),
        ("Unsupported Claim Rate", "unsupported_claim_rate"),
        ("Average Claims per Task", "claims_per_task"),
    ]

    for label, key in metric_labels:
        data = stats[key]
        m, s = data["mean"], data["std"]
        v42 = data["values"][0]
        v123 = data["values"][1]
        v999 = data["values"][2]
        lines.append(f"| **{label}** | {m:.4f} ± {s:.4f} | {v42:.4f} | {v123:.4f} | {v999:.4f} |")

    lines.extend([
        "",
        "## 3. Key Methodological Improvements in V4",
        "1. **Symbol Normalization**: Canonical resolution for symbols (e.g. `click.testing.isolated_filesystem` and `isolated_filesystem` match symmetrically).",
        "2. **Structural Attribution**: Explicit git diff inspection ensures claims cannot cite non-existent files or phantom commits.",
        "3. **Semantic Entailment**: Statements are verified to entail the change direction (deprecation, replacement) rather than simply regurgitating tokens.",
        "4. **Zero Fallback Toleration**: Missing commit fields or ungrounded assertions are flagged as `MISSING_COMMIT_ATTRIBUTION` or `UNSUPPORTED`.",
        ""
    ])

    with open(report_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Generated {report_file}")


if __name__ == "__main__":
    main()
