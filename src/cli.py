"""
Unified CLI interface for RoleMem experiment execution.
Supports: validate, run, summarize.
"""
import argparse
import sys
import json
import os
import platform
import subprocess
from src.evaluate import run_evaluation

def get_environment_info():
    gpu_info = "None"
    try:
        gpu_out = subprocess.check_output(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"], text=True)
        gpu_info = gpu_out.strip()
    except Exception:
        pass

    return {
        "os": platform.platform(),
        "python": sys.version,
        "gpu": gpu_info,
        "platform": platform.uname()._asdict()
    }

def cmd_validate(args):
    """Validates configuration file and test manifest without running costly experiments."""
    if not os.path.exists(args.config):
        print(f"Error: Config file '{args.config}' not found.")
        sys.exit(1)

    with open(args.config, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    data_file = cfg.get("data_file")
    if not data_file or not os.path.exists(data_file):
        print(f"Error: Specified data_file '{data_file}' does not exist.")
        sys.exit(1)

    with open(data_file, "r", encoding="utf-8") as f:
        tasks = [json.loads(line) for line in f if line.strip()]

    print(f"[VALIDATION PASSED] Config '{args.config}' is valid. Found {len(tasks)} tasks in '{data_file}'.")
    sys.exit(0)

def cmd_run(args):
    """Runs the experiment defined by the config file."""
    if not os.path.exists(args.config):
        print(f"Error: Config file '{args.config}' not found.")
        sys.exit(1)

    with open(args.config, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    data_file = cfg.get("data_file", "data/task-specs.jsonl")
    method = cfg.get("method", "full")
    token_budget = cfg.get("token_budget", 2048)
    run_id = cfg.get("run_id", "smoke_run")
    out_dir = os.path.join("runs", run_id)

    os.makedirs(out_dir, exist_ok=True)

    # Save run configs and environment
    with open(os.path.join(out_dir, "config.json"), "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)

    with open(os.path.join(out_dir, "environment.json"), "w", encoding="utf-8") as f:
        json.dump(get_environment_info(), f, indent=2)

    with open(data_file, "r", encoding="utf-8") as f:
        tasks = [json.loads(line) for line in f if line.strip()]

    print(f"Executing experiment '{run_id}' with method '{method}', total tasks: {len(tasks)}...")
    metrics = run_evaluation(tasks, method=method, token_budget=token_budget, output_dir=out_dir)

    print("\n=== Experiment Summary ===")
    print(f"Run ID:            {run_id}")
    print(f"Method:            {method}")
    print(f"Tasks:             {metrics['total_tasks']}")
    print(f"Task Success Rate: {metrics['tsr'] * 100:.1f}%")
    print(f"Stale Error Rate:  {metrics['stale_error_rate'] * 100:.1f}%")
    print(f"Avg Latency:       {metrics['avg_latency_ms']} ms")
    print(f"Artifacts:         {out_dir}/")
    sys.exit(0)

def cmd_summarize(args):
    """Summarizes a completed run directory."""
    if not os.path.exists(args.run_dir):
        print(f"Error: Run directory '{args.run_dir}' not found.")
        sys.exit(1)

    met_file = os.path.join(args.run_dir, "metrics.json")
    if not os.path.exists(met_file):
        print(f"Error: 'metrics.json' not found in '{args.run_dir}'.")
        sys.exit(1)

    with open(met_file, "r", encoding="utf-8") as f:
        metrics = json.load(f)

    print(f"\n--- Run Summary for {args.run_dir} ---")
    for k, v in metrics.items():
        print(f"  {k}: {v}")
    sys.exit(0)

def main():
    parser = argparse.ArgumentParser(description="RoleMem Experiment Runner CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # validate
    p_val = subparsers.add_parser("validate", help="Validate config without executing")
    p_val.add_argument("--config", required=True, help="Path to config.json")
    p_val.set_defaults(func=cmd_validate)

    # run
    p_run = subparsers.add_parser("run", help="Run experiment")
    p_run.add_argument("--config", required=True, help="Path to config.json")
    p_run.set_defaults(func=cmd_run)

    # summarize
    p_sum = subparsers.add_parser("summarize", help="Summarize metrics of a run")
    p_sum.add_argument("--run-dir", required=True, help="Path to runs/<run_id>")
    p_sum.set_defaults(func=cmd_summarize)

    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
