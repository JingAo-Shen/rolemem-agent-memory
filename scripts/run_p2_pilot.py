import os
import sys
import json
import numpy as np

sys.path.insert(0, "/code/rolemem-agent-memory")

from src.evaluate import run_evaluation

def bootstrap_ci(diffs, n_boot=2000, ci=0.95):
    boot_means = []
    n = len(diffs)
    for _ in range(n_boot):
        sample = np.random.choice(diffs, size=n, replace=True)
        boot_means.append(np.mean(sample))
    low = np.percentile(boot_means, (1 - ci) / 2 * 100)
    high = np.percentile(boot_means, (1 + ci) / 2 * 100)
    return round(float(low), 4), round(float(high), 4)

def main():
    data_file = "data/dev_episodes.jsonl"
    with open(data_file, "r", encoding="utf-8") as f:
        tasks = [json.loads(line) for line in f if line.strip()]

    methods = [
        ("B1_recent", "recent"),
        ("B3_bm25", "bm25"),
        ("B4_time_filter", "no_role_bonus"),
        ("A2_no_validity", "no_validity"),
        ("A3_no_role_bonus", "no_role_bonus"),
        ("F_rolemem_full", "full")
    ]

    all_results = {}
    preds_by_method = {}

    print(f"Starting P2 Pilot on {len(tasks)} dev episodes across {len(methods)} methods...\n")

    for method_id, method_type in methods:
        out_dir = f"runs/pilot_{method_id}"
        metrics = run_evaluation(tasks, method=method_type, token_budget=2048, output_dir=out_dir)
        all_results[method_id] = metrics

        with open(os.path.join(out_dir, "predictions.jsonl"), "r", encoding="utf-8") as f:
            preds = [json.loads(line) for line in f if line.strip()]
        preds_by_method[method_id] = preds

        print(f"[{method_id:18s}] TSR: {metrics['tsr']*100:5.1f}% | Stale Error Rate: {metrics['stale_error_rate']*100:5.1f}% | Latency: {metrics['avg_latency_ms']:5.2f} ms")

    full_preds = [p["passed"] for p in preds_by_method["F_rolemem_full"]]
    paired_summary = {}

    print("\n=== Paired Analysis vs Full RoleMem (F) ===")
    for method_id, _ in methods[:-1]:
        m_preds = [p["passed"] for p in preds_by_method[method_id]]
        diffs = np.array(full_preds, dtype=float) - np.array(m_preds, dtype=float)
        mean_diff = float(np.mean(diffs))
        ci_low, ci_high = bootstrap_ci(diffs)
        paired_summary[method_id] = {
            "mean_tsr_diff": round(mean_diff, 4),
            "ci_95": [ci_low, ci_high]
        }
        print(f"  F - {method_id:16s}: Diff = +{mean_diff*100:4.1f}pp (95% CI: [{ci_low*100:+.1f}pp, {ci_high*100:+.1f}pp])")

    summary_output = {
        "methods": all_results,
        "paired_vs_full": paired_summary
    }

    with open("runs/p2_pilot_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary_output, f, indent=2)

    print("\nSaved P2 Pilot Summary to runs/p2_pilot_summary.json")

if __name__ == "__main__":
    main()
