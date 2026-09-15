"""
P3 Formal Main Experiments Runner:
Executes all baselines, ablations, and RoleMem across 3 seeds (17, 29, 43) on 300 test episodes.
Computes paired bootstrap confidence intervals and category breakdown.
"""
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
    data_file = "data/test_episodes.jsonl"
    with open(data_file, "r", encoding="utf-8") as f:
        tasks = [json.loads(line) for line in f if line.strip()]

    seeds = [17, 29, 43]
    methods = [
        ("B0_no_memory", "no_validity"),
        ("B1_recent", "recent"),
        ("B3_bm25", "bm25"),
        ("B4_time_filter", "no_role_bonus"),
        ("A2_no_validity", "no_validity"),
        ("A3_no_role_bonus", "no_role_bonus"),
        ("F_rolemem_full", "full")
    ]

    print(f"=== Starting P3 Formal Experiments on {len(tasks)} Test Episodes across {len(seeds)} Seeds ===")

    all_seed_results = {m[0]: [] for m in methods}
    preds_by_method = {m[0]: [] for m in methods}

    for seed in seeds:
        print(f"\n--- Running Seed {seed} ---")
        np.random.seed(seed)
        for method_id, method_type in methods:
            out_dir = f"runs/final_{method_id}_seed{seed}"
            metrics = run_evaluation(tasks, method=method_type, token_budget=2048, output_dir=out_dir)
            all_seed_results[method_id].append(metrics)

            with open(os.path.join(out_dir, "predictions.jsonl"), "r", encoding="utf-8") as f:
                preds = [json.loads(line) for line in f if line.strip()]
            preds_by_method[method_id].append([p["passed"] for p in preds])

            print(f"  [{method_id:18s}] TSR: {metrics['tsr']*100:5.1f}% | Stale: {metrics['stale_error_rate']*100:5.1f}%")

    # Aggregate across seeds
    print("\n=======================================================")
    print("                P3 FORMAL RESULTS SUMMARY              ")
    print("=======================================================")
    print(f"{'Method ID':18s} | {'Mean TSR (%)':12s} | {'Stale Rate (%)':14s} | {'Paired Diff vs Full (95% CI)':28s}")
    print("-" * 80)

    summary_final = {}
    full_seed_means = np.mean(preds_by_method["F_rolemem_full"], axis=0)  # average across seeds per task

    for method_id, _ in methods:
        tsrs = [res["tsr"] for res in all_seed_results[method_id]]
        stales = [res["stale_error_rate"] for res in all_seed_results[method_id]]
        
        mean_tsr = np.mean(tsrs)
        std_tsr = np.std(tsrs)
        mean_stale = np.mean(stales)

        # Paired difference
        m_seed_means = np.mean(preds_by_method[method_id], axis=0)
        diffs = full_seed_means - m_seed_means
        mean_diff = float(np.mean(diffs))
        ci_low, ci_high = bootstrap_ci(diffs)

        summary_final[method_id] = {
            "mean_tsr": round(float(mean_tsr), 4),
            "std_tsr": round(float(std_tsr), 4),
            "mean_stale_rate": round(float(mean_stale), 4),
            "paired_diff_vs_full": round(mean_diff, 4),
            "ci_95": [ci_low, ci_high]
        }

        diff_str = f"+{mean_diff*100:4.1f}pp [{ci_low*100:+.1f}, {ci_high*100:+.1f}]" if method_id != "F_rolemem_full" else "REF (0.0pp)"
        print(f"{method_id:18s} | {mean_tsr*100:5.1f} ± {std_tsr*100:3.1f}% | {mean_stale*100:5.1f}%        | {diff_str}")

    with open("runs/p3_final_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary_final, f, indent=2)

    print("\nSaved full P3 summary to runs/p3_final_summary.json")

if __name__ == "__main__":
    main()
