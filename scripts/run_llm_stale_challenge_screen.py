#!/usr/bin/env python3
"""
scripts/run_llm_stale_challenge_screen.py

Executes the genuine LLM Stale-Challenge Screen for RoleMem Track A reconstructed transitions.
Tests 3 conditions per seed (seeds 42, 123, 999) using Qwen2.5-Coder-7B:
- S0: No Memory Baseline
- S2 / H2: Historical Stale Memory Injected
- S3 / H3: Target Valid Memory Injected

For each generation:
1. LLM Generation (Qwen2.5-Coder-7B, temp=0.2, max_tokens=450)
2. AST Stale Action Detector (checks deprecated symbol active use)
3. Bubblewrap Sandbox Execution (pytest hidden tests on target snapshot)
4. Solution Constraints Verification (API Deprecation, Replacement Mechanism, Behavior Fidelity)

Qualification Rule (Pilot-v1.3-r2.1):
- QUALIFIED_STALE_CHALLENGE:
    H2 stale-active-use >= 1/3
    AND (H3 stale-active-use < H2 stale-active-use OR H3 TSR > H2 TSR)
- STALE_INSENSITIVE_FOR_QWEN7B:
    H2 stale-active-use == 0/3
- EVOLUTION_CONTROL:
    Evolution control transitions without deprecation

Outputs:
- runs/llm-stale-challenge/<tid>/<cond>_seed<seed>.json
- runs/llm-stale-challenge/<tid>/<seed>.json
- reports/llm-stale-challenge.md
"""

import os
import sys
import json
import re
import torch
from typing import Dict, Any, List, Optional

sys.path.insert(0, "/code/rolemem-agent-memory")
from src.sandbox_secure import SecureSandboxExecutor
from src.stale_detector_ast import ASTStaleActionDetector
from scripts.evaluate_solution_constraints import SolutionConstraintEvaluator
from scripts.run_causal_counterfactual_v2 import load_workspace
from transformers import AutoTokenizer, AutoModelForCausalLM

MANIFEST_PATH = "/code/rolemem-agent-memory/data/track_a_reconstructed_manifest.jsonl"
TARGET_MEM_SNAPSHOT = "/code/rolemem-agent-memory/data/handoff_target_memory_snapshot.json"
HIST_MEM_DIR = "/code/rolemem-agent-memory/runs/historical-memory-writer-v4"
OUTPUT_BASE = "/code/rolemem-agent-memory/runs/llm-stale-challenge"
REPORT_PATH = "/code/rolemem-agent-memory/reports/llm-stale-challenge.md"
FIXTURES_DIR = "/code/rolemem-agent-memory/fixtures_v2"
VENVS_ROOT = "/code/rolemem-agent-memory/.venvs"
SEEDS = [42, 123, 999]


def extract_code(text: str) -> str:
    """Extracts python code block or falls back to text."""
    pattern = r"```(?:python)?\s*(.*?)\s*```"
    matches = re.findall(pattern, text, re.DOTALL)
    if matches:
        return matches[-1].strip()
    lines = text.splitlines()
    code_lines = [l for l in lines if not l.startswith("```")]
    return "\n".join(code_lines).strip()


def format_memory_block(statements: List[str]) -> str:
    if not statements:
        return ""
    lines = ["[RELEVANT ARCHITECTURAL MEMORY]"]
    for s in statements:
        lines.append(f"- {s}")
    lines.append("")
    return "\n".join(lines)


def main():
    model_dir = "/code/rolemem-agent-memory/models/qwen2.5-coder-7b"
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Loading Qwen2.5-Coder-7B from {model_dir} on {device}...")
    tokenizer = AutoTokenizer.from_pretrained(model_dir, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        model_dir,
        torch_dtype=torch.float16 if device == "cuda" else torch.float32,
        device_map="auto" if device == "cuda" else None
    )
    model.eval()

    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        transitions = [json.loads(line) for line in f if line.strip()]

    with open(TARGET_MEM_SNAPSHOT, "r", encoding="utf-8") as f:
        target_claims = json.load(f)["claims"]

    os.makedirs(OUTPUT_BASE, exist_ok=True)
    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)

    print(f"Loaded {len(transitions)} transitions. Beginning LLM Stale-Challenge Screen...")

    overall_report = {}
    qualified_count = 0
    insensitive_count = 0
    control_count = 0

    for item in transitions:
        tid = item["transition_id"]
        task_prompt = item.get("current_task", "")
        target_file = item.get("target_file", "solution.py")
        is_control = item.get("track") in ["TRACK_A_EVOLUTION_CONTROL", "TRACK_A_API_EVOLUTION"] or (not item.get("stale_sensitive", True))
        deprecated_symbols = item.get("deprecated_symbols", item.get("changed_symbols", []))

        fixture_dir = os.path.join(FIXTURES_DIR, tid)
        target_ws = load_workspace(os.path.join(fixture_dir, "after"))
        with open(os.path.join(fixture_dir, "hidden_tests", "test_evaluation.py"), "r", encoding="utf-8") as f:
            hidden_test_code = f.read()

        venv_bin = os.path.join(VENVS_ROOT, tid, "bin")
        if os.path.isdir(venv_bin):
            executor = SecureSandboxExecutor(custom_env_bin_dir=venv_bin)
        else:
            executor = SecureSandboxExecutor()

        constraint_evaluator = SolutionConstraintEvaluator(tid)

        task_out_dir = os.path.join(OUTPUT_BASE, tid)
        os.makedirs(task_out_dir, exist_ok=True)

        print(f"\n========================================================")
        print(f"[{tid}] Starting 3-Seed Screen (S0, S2, S3)...")
        print(f"Task: {task_prompt}")
        print(f"========================================================")

        task_results = {"S0": [], "S2": [], "S3": []}

        for seed in SEEDS:
            seed_runs = {}

            for cond in ["S0", "S2", "S3"]:
                torch.manual_seed(seed)

                # Determine memory statement
                mem_statements = []
                if cond == "S0":
                    mem_statements = []
                elif cond == "S2":
                    # Historical Stale Memory
                    hist_file = os.path.join(HIST_MEM_DIR, tid, f"{seed}.json")
                    stale_stmt = item.get("stale_memory_candidate", "")
                    if os.path.exists(hist_file):
                        try:
                            h_data = json.load(open(hist_file))
                            if h_data.get("verdict") == "HIST_MEMORY_VALID" and h_data.get("statement"):
                                stale_stmt = h_data.get("statement")
                        except Exception:
                            pass
                    mem_statements = [stale_stmt]
                elif cond == "S3":
                    # Verified Target Memory
                    target_claim = target_claims.get(tid, {}).get("statement", item.get("valid_memory_candidate", ""))
                    mem_statements = [target_claim]

                mem_block = format_memory_block(mem_statements)

                prompt = f"""You are an autonomous AI software engineer solving a programming task.

{mem_block}[TASK INSTRUCTION]
{task_prompt}

Write the complete Python source code for `{target_file}` to satisfy all requirements and tests.
Output your implementation strictly enclosed inside a ```python ``` code block.
"""
                msgs = [{"role": "user", "content": prompt}]
                chat = tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
                inputs = tokenizer(chat, return_tensors="pt").to(device)

                with torch.no_grad():
                    outputs = model.generate(
                        **inputs,
                        max_new_tokens=450,
                        do_sample=True,
                        temperature=0.2
                    )

                gen_text = tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True)
                code_solution = extract_code(gen_text)

                # 1. AST Stale Action Detector
                stale_analysis = ASTStaleActionDetector.analyze(code_solution, deprecated_symbols)
                is_stale_action = stale_analysis.stale_active_use

                # 2. Bubblewrap Sandbox Execution
                pytest_pass, pytest_log = executor.execute_in_sandbox(
                    workspace_files=target_ws,
                    target_file=target_file,
                    generated_code=code_solution,
                    test_code=hidden_test_code
                )

                # 3. Executable Solution Constraints Verification
                constraint_res = constraint_evaluator.evaluate_code(code_solution, run_id=f"{cond}_seed{seed}")
                constraint_pass = (constraint_res.get("overall_status") == "PASS") or (constraint_res.get("overall_constraint_status") == "PASS")

                # Overall Task Success Rate (TSR)
                # Task Success = pytest PASS AND stale-action-free AND solution constraints PASS
                overall_task_success = pytest_pass and (not is_stale_action) and constraint_pass

                run_telemetry = {
                    "task_id": tid,
                    "condition": cond,
                    "seed": seed,
                    "task_prompt": task_prompt,
                    "memory_statements": mem_statements,
                    "raw_generation": gen_text,
                    "parsed_code": code_solution,
                    "is_stale_action": is_stale_action,
                    "ast_details": {
                        "stale_active_use": stale_analysis.stale_active_use,
                        "stale_mention": stale_analysis.stale_mention,
                        "active_nodes": stale_analysis.active_nodes
                    },
                    "pytest_pass": pytest_pass,
                    "pytest_log_excerpt": pytest_log[:600],
                    "constraint_status": "PASS" if constraint_pass else "FAIL",
                    "constraint_results": constraint_res.get("constraints"),
                    "overall_task_success": overall_task_success,
                    "input_tokens": int(inputs.input_ids.shape[1]),
                    "output_tokens": int(outputs.shape[1] - inputs.input_ids.shape[1])
                }

                # Save condition run
                with open(os.path.join(task_out_dir, f"{cond}_seed{seed}.json"), "w", encoding="utf-8") as f:
                    json.dump(run_telemetry, f, indent=2)

                task_results[cond].append(run_telemetry)
                seed_runs[cond] = run_telemetry

                print(f"  [{cond}] Seed {seed:3d} -> StaleAction={is_stale_action} | Pytest={pytest_pass} | Constraints={'PASS' if constraint_pass else 'FAIL'} | TSR={overall_task_success}")

            # Save aggregate seed JSON
            with open(os.path.join(task_out_dir, f"{seed}.json"), "w", encoding="utf-8") as sf:
                json.dump(seed_runs, sf, indent=2)

        # Qualification Computation
        h2_stale_count = sum(1 for r in task_results["S2"] if r["is_stale_action"])
        h3_stale_count = sum(1 for r in task_results["S3"] if r["is_stale_action"])
        h2_tsr_count = sum(1 for r in task_results["S2"] if r["overall_task_success"])
        h3_tsr_count = sum(1 for r in task_results["S3"] if r["overall_task_success"])
        s0_tsr_count = sum(1 for r in task_results["S0"] if r["overall_task_success"])

        if is_control:
            qualification = "EVOLUTION_CONTROL"
            control_count += 1
        elif h2_stale_count >= 1 and (h3_stale_count < h2_stale_count or h3_tsr_count > h2_tsr_count):
            qualification = "QUALIFIED_STALE_CHALLENGE"
            qualified_count += 1
        elif h2_stale_count == 0:
            qualification = "STALE_INSENSITIVE_FOR_QWEN7B"
            insensitive_count += 1
        else:
            qualification = "STALE_AFFECTED_WITHOUT_TARGET_REPAIR"

        summary_entry = {
            "transition_id": tid,
            "track": item.get("track"),
            "qualification": qualification,
            "h2_stale_rate": f"{h2_stale_count}/3",
            "h3_stale_rate": f"{h3_stale_count}/3",
            "s0_tsr": f"{s0_tsr_count}/3",
            "h2_tsr": f"{h2_tsr_count}/3",
            "h3_tsr": f"{h3_tsr_count}/3"
        }
        overall_report[tid] = summary_entry
        print(f"\n=> [{tid}] QUALIFICATION VERDICT: {qualification}")
        print(f"   H2 Stale: {h2_stale_count}/3 | H3 Stale: {h3_stale_count}/3 | H2 TSR: {h2_tsr_count}/3 | H3 TSR: {h3_tsr_count}/3")

    # Write Markdown Report
    report_lines = [
        "# Real LLM Stale-Challenge Screen Report (Qwen2.5-Coder-7B)",
        "",
        f"**Screened Transitions**: {len(transitions)}",
        f"**Qualified Stale Challenges**: {qualified_count}",
        f"**Evolution Controls**: {control_count}",
        f"**Stale Insensitive for Qwen7B**: {insensitive_count}",
        "",
        "## Per-Transition Evaluation Summary",
        "",
        "| Transition ID | Track | Qualification Verdict | H2 Stale Rate | H3 Stale Rate | S0 TSR | H2 TSR | H3 TSR |",
        "| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |"
    ]

    for tid, entry in overall_report.items():
        report_lines.append(
            f"| `{tid}` | `{entry['track']}` | **{entry['qualification']}** | {entry['h2_stale_rate']} | {entry['h3_stale_rate']} | {entry['s0_tsr']} | {entry['h2_tsr']} | {entry['h3_tsr']} |"
        )

    report_lines.extend([
        "",
        "## Scientific Interpretation",
        "",
        "- **Agent-Generated Qualification**: Classification is strictly based on actual Qwen2.5-Coder-7B generations across 3 independent random seeds (42, 123, 999).",
        "- **Stale-Insensitive Cohort**: Transitions where Qwen2.5-Coder-7B did not adopt the injected stale memory are categorized as `STALE_INSENSITIVE_FOR_QWEN7B` rather than inflating stale vulnerability figures.",
        "- **Benchmark Eligibility**: Stale-insensitive seeds remain fully eligible for transition/regression verification but are appropriately partitioned for role-memory effect analysis.",
        ""
    ])

    with open(REPORT_PATH, "w", encoding="utf-8") as rf:
        rf.write("\n".join(report_lines) + "\n")

    print(f"\nLLM Stale-Challenge Screen Complete: {qualified_count} Qualified Stale Challenges, {control_count} Evolution Controls, {insensitive_count} Stale Insensitive.")
    print(f"Report saved to {REPORT_PATH}\n")


if __name__ == "__main__":
    main()
