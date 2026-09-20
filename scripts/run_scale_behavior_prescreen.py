#!/usr/bin/env python3
"""
scripts/run_scale_behavior_prescreen.py
Executes the 1-seed (seed 42) Behavior Prescreen on the Track A Scale Cohort (transitions 11-30)
using Qwen2.5-Coder-7B across S0, S2, S3 conditions.
Persists raw telemetry to runs/scale-behavior-prescreen/<tid>/ and
updates data/agent_stale_challenge_status.jsonl dynamically.
"""

import os
import sys
import json
import re
import torch
from typing import Dict, Any, List

sys.path.insert(0, "/code/rolemem-agent-memory")
from src.sandbox_secure import SecureSandboxExecutor
from src.stale_detector_ast_v2 import ASTStaleActionDetectorV2
from src.bm25_retriever import RepoBM25Retriever
from scripts.run_causal_counterfactual_v2 import load_workspace
from transformers import AutoTokenizer, AutoModelForCausalLM

SCALE_MANIFEST_PATH = "/code/rolemem-agent-memory/data/track_a_scale_manifest.jsonl"
CALIBRATION_CHALLENGE_PATH = "/code/rolemem-agent-memory/data/agent_stale_challenge_status.jsonl"
OUTPUT_BASE = "/code/rolemem-agent-memory/runs/scale-behavior-prescreen"
FIXTURES_DIR = "/code/rolemem-agent-memory/fixtures_v2"
VENVS_ROOT = "/code/rolemem-agent-memory/.venvs"
MODEL_PATH = "/code/rolemem-agent-memory/models/qwen2.5-coder-7b"
SEED = 42

os.makedirs(OUTPUT_BASE, exist_ok=True)


class SimpleTokenizer:
    def encode(self, text: str, add_special_tokens: bool = False):
        return re.findall(r"\w+|[^\w\s]", text)

    def decode(self, tokens: List[str]):
        return " ".join(tokens)


def extract_code(text: str) -> str:
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


def run_prescreen():
    print("=== Running Track A Scale Cohort Behavior Prescreen (Seed 42) ===")
    print(f"Loading judge model from {MODEL_PATH}...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_PATH,
        torch_dtype=torch.float16,
        device_map="cuda"
    )
    model.eval()
    device = "cuda"

    with open(SCALE_MANIFEST_PATH, "r", encoding="utf-8") as f:
        scale_specs = [json.loads(line) for line in f if line.strip()]

    print(f"Loaded {len(scale_specs)} scale transitions.\n")

    scale_challenge_records = []

    for item in scale_specs:
        tid = item["transition_id"]
        repo_name = item["repo_name"]
        target_file = item.get("target_file", "solution.py")
        task_prompt = item.get("current_task", "")
        stale_stmt = item.get("stale_memory_candidate", "")
        valid_stmt = item.get("valid_memory_candidate", "")
        is_control = (not item.get("stale_sensitive", True)) or (item.get("transition_type") == "API_EVOLUTION")

        task_out_dir = os.path.join(OUTPUT_BASE, tid)
        os.makedirs(task_out_dir, exist_ok=True)

        fixture_dir = os.path.join(FIXTURES_DIR, tid)
        target_ws = load_workspace(os.path.join(fixture_dir, "after"))

        # Hidden test code
        hidden_test_p = os.path.join(fixture_dir, "hidden_tests", "test_evaluation.py")
        with open(hidden_test_p, "r", encoding="utf-8") as tf:
            hidden_test_code = tf.read()

        # Bubblewrap executor
        venv_bin = os.path.join(VENVS_ROOT, tid, "bin")
        if os.path.isdir(venv_bin):
            executor = SecureSandboxExecutor(custom_env_bin_dir=venv_bin)
        else:
            executor = SecureSandboxExecutor()

        # BM25 Context retrieval
        retriever = RepoBM25Retriever(target_ws)
        s_tokenizer = SimpleTokenizer()
        repo_context, repo_tokens = retriever.retrieve_context(
            query=task_prompt,
            tokenizer=s_tokenizer,
            max_tokens=1200
        )
        retrieved_files = []

        condition_results = {}

        print(f"[{tid}] Evaluating (is_control={is_control})...")

        for cond in ["S0", "S2", "S3"]:
            torch.manual_seed(SEED)

            if cond == "S0":
                mem_statements = []
                mem_source = "NO_MEMORY"
            elif cond == "S2":
                mem_statements = [stale_stmt] if stale_stmt else []
                mem_source = "STALE_MEMORY_CANDIDATE"
            elif cond == "S3":
                mem_statements = [valid_stmt] if valid_stmt else []
                mem_source = "VALID_MEMORY_CANDIDATE"

            mem_block = format_memory_block(mem_statements)

            prompt = f"""You are an autonomous AI software engineer solving a programming task.

{mem_block}[TASK INSTRUCTION]
{task_prompt}

{repo_context}

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

            # AST Stale Action Detector V2
            stale_analysis = ASTStaleActionDetectorV2.analyze(code_solution, item)
            is_stale_action = stale_analysis.stale_active_use

            # Sandbox Execution
            pytest_pass, pytest_log = executor.execute_in_sandbox(
                workspace_files=target_ws,
                target_file=target_file,
                generated_code=code_solution,
                test_code=hidden_test_code
            )

            overall_task_success = pytest_pass and (not is_stale_action)

            run_telemetry = {
                "task_id": tid,
                "condition": cond,
                "seed": SEED,
                "memory_source": mem_source,
                "memory_statements": mem_statements,
                "retrieved_files": retrieved_files,
                "repository_context_tokens": repo_tokens,
                "is_stale_action": is_stale_action,
                "ast_details": {
                    "stale_active_use": stale_analysis.stale_active_use,
                    "stale_mention": stale_analysis.stale_mention,
                    "active_nodes": stale_analysis.active_nodes
                },
                "pytest_pass": pytest_pass,
                "pytest_log_excerpt": pytest_log[:400],
                "overall_task_success": overall_task_success,
                "parsed_code": code_solution
            }

            out_file = os.path.join(task_out_dir, f"{cond}_seed{SEED}.json")
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(run_telemetry, f, indent=2)

            condition_results[cond] = run_telemetry
            print(f"   [{cond}] StaleAction={is_stale_action} | PytestPass={pytest_pass} | TSR={overall_task_success}")

        # Classify Status
        s2 = condition_results["S2"]
        s3 = condition_results["S3"]
        s0 = condition_results["S0"]

        if is_control:
            status = "EVOLUTION_CONTROL"
        elif s2["is_stale_action"] and ((not s3["is_stale_action"]) or (s3["overall_task_success"] and not s2["overall_task_success"])):
            status = "AGENT_STALE_CHALLENGE_READY"
        elif not s2["is_stale_action"]:
            status = "STALE_INSENSITIVE_FOR_QWEN7B"
        else:
            status = "STALE_AFFECTED_WITHOUT_TARGET_REPAIR"

        challenge_rec = {
            "transition_id": tid,
            "track": item.get("track", "TRACK_A_SCALE"),
            "status": status,
            "valid_historical_runs": "1/1",
            "repo_leakage": "CURRENT_REPO_INFORMATIONAL",
            "h2_stale_rate": f"{1 if s2['is_stale_action'] else 0}/1",
            "h3_stale_rate": f"{1 if s3['is_stale_action'] else 0}/1",
            "h2_tsr": f"{1 if s2['overall_task_success'] else 0}/1",
            "h3_tsr": f"{1 if s3['overall_task_success'] else 0}/1"
        }
        scale_challenge_records.append(challenge_rec)
        print(f" -> Classification: {status}\n")

    # Load calibration records and merge
    with open(CALIBRATION_CHALLENGE_PATH, "r", encoding="utf-8") as f:
        existing_records = [json.loads(line) for line in f if line.strip()]

    # Filter out any duplicate transition ids from existing
    existing_ids = {r["transition_id"] for r in scale_challenge_records}
    final_records = [r for r in existing_records if r["transition_id"] not in existing_ids] + scale_challenge_records

    # Re-write agent_stale_challenge_status.jsonl
    with open(CALIBRATION_CHALLENGE_PATH, "w", encoding="utf-8") as f:
        for r in final_records:
            f.write(json.dumps(r) + "\n")

    print(f"Updated {CALIBRATION_CHALLENGE_PATH} with {len(final_records)} total transitions.")


if __name__ == "__main__":
    run_prescreen()
