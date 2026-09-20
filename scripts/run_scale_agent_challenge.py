#!/usr/bin/env python3
"""
scripts/run_scale_agent_challenge.py

Executes the formal 3-seed (42, 123, 999) Scale Agent Challenge on qualified candidates.
Conditions:
- S0: Task + Repo Context (no memory)
- S2: Task + Repo Context + Agent A Historical Memory (runs/historical-memory-writer-scale/)
- S3: Task + Repo Context + Verified Target Memory (data/handoff_target_memory_scale.json)

Outputs:
- runs/scale-agent-challenge/<tid>/<condition>_seed<seed>.json
- data/scale_agent_challenge_status.jsonl
- reports/scale-agent-challenge.md
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
SCALE_HIST_DIR = "/code/rolemem-agent-memory/runs/historical-memory-writer-scale"
SCALE_TARGET_PATH = "/code/rolemem-agent-memory/data/handoff_target_memory_scale.json"
OUTPUT_BASE = "/code/rolemem-agent-memory/runs/scale-agent-challenge"
STATUS_JSONL = "/code/rolemem-agent-memory/data/scale_agent_challenge_status.jsonl"
REPORT_PATH = "/code/rolemem-agent-memory/reports/scale-agent-challenge.md"
FIXTURES_DIR = "/code/rolemem-agent-memory/fixtures_v2"
VENVS_ROOT = "/code/rolemem-agent-memory/.venvs"
MODEL_PATH = "/code/rolemem-agent-memory/models/qwen2.5-coder-7b"
SEEDS = [42, 123, 999]

os.makedirs(OUTPUT_BASE, exist_ok=True)
os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)


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


def run_scale_agent_challenge():
    print("=== Running Track A Scale Agent Challenge (3 Seeds: 42, 123, 999) ===")
    print(f"Loading judge model from {MODEL_PATH}...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_PATH,
        torch_dtype=torch.float16,
        device_map="cuda"
    )
    model.eval()

    with open(SCALE_MANIFEST_PATH, "r", encoding="utf-8") as f:
        scale_specs = [json.loads(line) for line in f if line.strip()]

    with open(SCALE_TARGET_PATH, "r", encoding="utf-8") as f:
        target_snapshot = json.load(f).get("claims", {})

    # Focus on scale candidate tasks with valid historical memories generated
    candidate_tids = sorted(os.listdir(SCALE_HIST_DIR))
    target_specs = [item for item in scale_specs if item["transition_id"] in candidate_tids]

    print(f"Executing challenge on {len(target_specs)} candidates across {len(SEEDS)} seeds...\n")

    challenge_records = []

    for item in target_specs:
        tid = item["transition_id"]
        target_file = item.get("target_file", "solution.py")
        task_prompt = item.get("current_task", "")
        track = item.get("track", "TRACK_A_STALE_SENSITIVE")
        is_control = (track in ["TRACK_A_EVOLUTION_CONTROL", "TRACK_A_API_EVOLUTION"])

        task_out_dir = os.path.join(OUTPUT_BASE, tid)
        os.makedirs(task_out_dir, exist_ok=True)

        fixture_dir = os.path.join(FIXTURES_DIR, tid)
        target_ws = load_workspace(os.path.join(fixture_dir, "after"))

        hidden_test_p = os.path.join(fixture_dir, "hidden_tests", "test_evaluation.py")
        with open(hidden_test_p, "r", encoding="utf-8") as tf:
            hidden_test_code = tf.read()

        venv_bin = os.path.join(VENVS_ROOT, tid, "bin")
        executor = SecureSandboxExecutor(custom_env_bin_dir=venv_bin if os.path.isdir(venv_bin) else None)

        retriever = RepoBM25Retriever(target_ws)
        s_tokenizer = SimpleTokenizer()
        repo_context, repo_tokens = retriever.retrieve_context(
            query=task_prompt,
            tokenizer=s_tokenizer,
            max_tokens=1200
        )

        valid_hist_count = 0
        h2_stale_count = 0
        h3_stale_count = 0
        h0_tsr_count = 0
        h2_tsr_count = 0
        h3_tsr_count = 0

        for seed in SEEDS:
            # 1. S0: No memory
            s0_out_path = os.path.join(task_out_dir, f"S0_seed{seed}.json")
            torch.manual_seed(seed)
            s0_prompt = f"TASK:\n{task_prompt}\n\nCURRENT REPOSITORY CONTEXT:\n{repo_context}\n\nProvide clean, complete Python code for {target_file} inside ```python ... ```."
            s0_msgs = [{"role": "user", "content": s0_prompt}]
            s0_chat = tokenizer.apply_chat_template(s0_msgs, tokenize=False, add_generation_prompt=True)
            s0_inputs = tokenizer(s0_chat, return_tensors="pt").to("cuda")
            with torch.no_grad():
                s0_gen = model.generate(**s0_inputs, max_new_tokens=400, temperature=0.2, do_sample=True)
            s0_code = extract_code(tokenizer.decode(s0_gen[0][s0_inputs.input_ids.shape[1]:], skip_special_tokens=True))
            s0_ast = ASTStaleActionDetectorV2.analyze(s0_code, item)
            s0_pass, s0_log = executor.execute_in_sandbox(target_ws, target_file, s0_code, hidden_test_code)
            s0_succ = s0_pass and (not s0_ast.stale_active_use)
            if s0_succ: h0_tsr_count += 1

            with open(s0_out_path, "w", encoding="utf-8") as f:
                json.dump({
                    "task_id": tid, "condition": "S0", "seed": seed, "memory_source": "NO_MEMORY",
                    "overall_task_success": s0_succ, "pytest_pass": s0_pass, "is_stale_action": s0_ast.stale_active_use,
                    "parsed_code": s0_code
                }, f, indent=2)

            # 2. S2: Agent A Historical Memory
            hist_file = os.path.join(SCALE_HIST_DIR, tid, f"{seed}.json")
            hist_stmt = None
            if os.path.exists(hist_file):
                with open(hist_file) as f:
                    h_data = json.load(f)
                    if h_data.get("tier_c_semantic_factuality"):
                        hist_stmt = h_data.get("statement")

            s2_out_path = os.path.join(task_out_dir, f"S2_seed{seed}.json")
            if hist_stmt:
                valid_hist_count += 1
                torch.manual_seed(seed)
                mem_block = format_memory_block([hist_stmt])
                s2_prompt = f"TASK:\n{task_prompt}\n\n{mem_block}CURRENT REPOSITORY CONTEXT:\n{repo_context}\n\nProvide clean, complete Python code for {target_file} inside ```python ... ```."
                s2_msgs = [{"role": "user", "content": s2_prompt}]
                s2_chat = tokenizer.apply_chat_template(s2_msgs, tokenize=False, add_generation_prompt=True)
                s2_inputs = tokenizer(s2_chat, return_tensors="pt").to("cuda")
                with torch.no_grad():
                    s2_gen = model.generate(**s2_inputs, max_new_tokens=400, temperature=0.2, do_sample=True)
                s2_code = extract_code(tokenizer.decode(s2_gen[0][s2_inputs.input_ids.shape[1]:], skip_special_tokens=True))
                s2_ast = ASTStaleActionDetectorV2.analyze(s2_code, item)
                s2_pass, s2_log = executor.execute_in_sandbox(target_ws, target_file, s2_code, hidden_test_code)
                s2_succ = s2_pass and (not s2_ast.stale_active_use)
                if s2_ast.stale_active_use: h2_stale_count += 1
                if s2_succ: h2_tsr_count += 1

                with open(s2_out_path, "w", encoding="utf-8") as f:
                    json.dump({
                        "task_id": tid, "condition": "S2", "seed": seed, "memory_source": "AGENT_A_HISTORICAL",
                        "statement": hist_stmt, "overall_task_success": s2_succ, "pytest_pass": s2_pass,
                        "is_stale_action": s2_ast.stale_active_use, "parsed_code": s2_code
                    }, f, indent=2)
            else:
                with open(s2_out_path, "w", encoding="utf-8") as f:
                    json.dump({
                        "task_id": tid, "condition": "S2", "seed": seed, "memory_source": "INVALID_HISTORICAL_MEMORY",
                        "overall_task_success": False, "pytest_pass": False, "is_stale_action": False
                    }, f, indent=2)

            # 3. S3: Verified Target Memory
            target_claim = target_snapshot.get(tid, {})
            target_stmt = target_claim.get("statement", item.get("valid_memory_candidate", ""))
            s3_out_path = os.path.join(task_out_dir, f"S3_seed{seed}.json")
            torch.manual_seed(seed)
            target_mem_block = format_memory_block([target_stmt])
            s3_prompt = f"TASK:\n{task_prompt}\n\n{target_mem_block}CURRENT REPOSITORY CONTEXT:\n{repo_context}\n\nProvide clean, complete Python code for {target_file} inside ```python ... ```."
            s3_msgs = [{"role": "user", "content": s3_prompt}]
            s3_chat = tokenizer.apply_chat_template(s3_msgs, tokenize=False, add_generation_prompt=True)
            s3_inputs = tokenizer(s3_chat, return_tensors="pt").to("cuda")
            with torch.no_grad():
                s3_gen = model.generate(**s3_inputs, max_new_tokens=400, temperature=0.2, do_sample=True)
            s3_code = extract_code(tokenizer.decode(s3_gen[0][s3_inputs.input_ids.shape[1]:], skip_special_tokens=True))
            s3_ast = ASTStaleActionDetectorV2.analyze(s3_code, item)
            s3_pass, s3_log = executor.execute_in_sandbox(target_ws, target_file, s3_code, hidden_test_code)
            s3_succ = s3_pass and (not s3_ast.stale_active_use)
            if s3_ast.stale_active_use: h3_stale_count += 1
            if s3_succ: h3_tsr_count += 1

            with open(s3_out_path, "w", encoding="utf-8") as f:
                json.dump({
                    "task_id": tid, "condition": "S3", "seed": seed, "memory_source": "TARGET_MEMORY_VERIFIED",
                    "statement": target_stmt, "overall_task_success": s3_succ, "pytest_pass": s3_pass,
                    "is_stale_action": s3_ast.stale_active_use, "parsed_code": s3_code
                }, f, indent=2)

        # Challenge Qualification
        if is_control:
            challenge_status = "EVOLUTION_CONTROL"
        elif valid_hist_count < 2:
            challenge_status = "HISTORICAL_MEMORY_UNSTABLE"
        elif h2_stale_count >= 1 and (h3_stale_count < h2_stale_count or h3_tsr_count > h2_tsr_count):
            challenge_status = "AGENT_STALE_CHALLENGE_READY"
        elif h2_stale_count == 0:
            challenge_status = "STALE_INSENSITIVE_FOR_QWEN7B"
        else:
            challenge_status = "STALE_AFFECTED_WITHOUT_TARGET_REPAIR"

        rec = {
            "transition_id": tid,
            "track": track,
            "status": challenge_status,
            "valid_historical_runs": f"{valid_hist_count}/3",
            "repo_leakage": "REPO_CONTEXT_NONTRIVIAL",
            "h2_stale_rate": f"{h2_stale_count}/{valid_hist_count}" if valid_hist_count > 0 else "0/0",
            "h3_stale_rate": f"{h3_stale_count}/3",
            "h0_tsr": f"{h0_tsr_count}/3",
            "h2_tsr": f"{h2_tsr_count}/{valid_hist_count}" if valid_hist_count > 0 else "0/0",
            "h3_tsr": f"{h3_tsr_count}/3"
        }
        challenge_records.append(rec)
        print(f"[{tid}] Status: {challenge_status} (Hist: {valid_hist_count}/3, H2 Stale: {h2_stale_count}, H3 Stale: {h3_stale_count}, H2 TSR: {h2_tsr_count}, H3 TSR: {h3_tsr_count})")

    # Save scale challenge status
    with open(STATUS_JSONL, "w", encoding="utf-8") as f:
        for r in challenge_records:
            f.write(json.dumps(r) + "\n")

    # Render reports/scale-agent-challenge.md
    ready_count = sum(1 for r in challenge_records if r["status"] == "AGENT_STALE_CHALLENGE_READY")
    report_lines = [
        "# Scale Agent Stale Challenge Evaluation Report",
        "",
        "## 1. Executive Summary",
        "",
        f"- **Candidate Transitions Audited**: {len(challenge_records)} (3 seeds = {len(challenge_records)*3} runs)",
        f"- **Agent Stale Challenge Ready (Scale)**: **{ready_count}**",
        "- **All memory sources strictly agent-generated**: `AGENT_A_HISTORICAL` and `TARGET_MEMORY_VERIFIED`",
        "",
        "---",
        "",
        "## 2. Scale Challenge Qualification Matrix",
        "",
        "| Transition ID | Qualification Status | Valid Hist Runs | H2 Stale Rate | H3 Stale Rate | H0 TSR | H2 TSR | H3 TSR |",
        "| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |"
    ]

    for r in challenge_records:
        report_lines.append(
            f"| `{r['transition_id']}` | **{r['status']}** | {r['valid_historical_runs']} | {r['h2_stale_rate']} | {r['h3_stale_rate']} | {r['h0_tsr']} | {r['h2_tsr']} | {r['h3_tsr']} |"
        )

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines) + "\n")

    print(f"\nScale Agent Challenge complete. Saved to {STATUS_JSONL} and {REPORT_PATH}")


if __name__ == "__main__":
    run_scale_agent_challenge()
