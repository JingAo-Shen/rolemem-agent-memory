import os
import sys
import json

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.smoke_tasks_v1 import get_smoke_tasks_v1
from src.baselines_v1 import BaselineRunnerV1
from src.evaluator_v1 import RealLLMRunnerV1



def main():
    tasks = get_smoke_tasks_v1()
    runner = RealLLMRunnerV1()
    output_dir = "runs/pilot_v1_smoke"
    os.makedirs(output_dir, exist_ok=True)

    methods = [
        ("B0_no_memory", BaselineRunnerV1.run_B0_no_memory),
        ("B1_recent_history", BaselineRunnerV1.run_B1_recent_raw_history),
        ("B3_bm25_unscoped", BaselineRunnerV1.run_B3_bm25_unscoped),
        ("B5_memstrata_supersession", BaselineRunnerV1.run_B5_memstrata_temporal_supersession),
        ("F_rolemem_full", BaselineRunnerV1.run_F_rolemem_full),
    ]

    all_results = {}

    print(f"=== Starting Pilot-v1 Smoke Run across {len(tasks)} Domain-Specific Tasks ===")
    print("Methods evaluated:", [m[0] for m in methods])
    print()

    for method_name, method_func in methods:
        print(f"--- Running Method: {method_name} ---")
        method_logs = []
        passed_count = 0
        stale_count = 0
        total_tokens = 0

        for idx, task in enumerate(tasks, 1):
            current_ws = task.get_current_workspace()
            current_time = 500.0  # Current logical evaluation timestamp
            
            # Generate memory block using method-specific retrieval
            mem_block = method_func(
                query=task.current_task_instruction,
                role="coder",
                current_time=current_time,
                workspace_files=current_ws,
                all_memories=task.historical_memories
            )

            # Evaluate with real LLM and sandbox pytest
            res = runner.evaluate_task(
                task=task,
                method_name=method_name,
                memory_block=mem_block,
                role="coder"
            )

            if res["passed"]:
                passed_count += 1
            if res.get("stale_used", False):
                stale_count += 1
            total_tokens += res["tokens"].get("total_tokens", 0)

            status_str = "PASS" if res["passed"] else "FAIL"
            stale_str = "YES" if res.get("stale_used", False) else "NO"
            print(f"  [{idx:02d}/10] {task.task_id[:25]:<25} | Result: {status_str} | Stale: {stale_str} | Latency: {res['latency']:.2f}s | Tokens: {res['tokens']['total_tokens']}")
            
            method_logs.append(res)

        tsr = (passed_count / len(tasks)) * 100
        stale_rate = (stale_count / len(tasks)) * 100
        print(f"  >> {method_name} Summary: TSR = {tsr:.1f}% ({passed_count}/{len(tasks)}), Stale Rate = {stale_rate:.1f}%, Total Tokens = {total_tokens}\n")

        all_results[method_name] = {
            "tsr": tsr / 100.0,
            "passed_count": passed_count,
            "total_tasks": len(tasks),
            "stale_rate": stale_rate / 100.0,
            "stale_count": stale_count,
            "total_tokens": total_tokens,
            "logs": method_logs
        }

    out_file = os.path.join(output_dir, "smoke_results.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)

    print(f"=== Smoke Evaluation Complete! Raw logs saved to {out_file} ===")


if __name__ == "__main__":
    main()
