#!/usr/bin/env python3
"""
scripts/run_scale_agent_challenge_v2.py

Executes the formal 3-seed (42, 123, 999) Scale Agent Challenge V2 on qualified candidates.
Conditions:
- S0: Task + Repo Context (no memory)
- S2: Task + Repo Context + Agent A Historical Memory (runs/historical-memory-writer-scale/)
- S3: Task + Repo Context + Verified Target Memory (data/handoff_target_memory_scale.json)

Integrates:
- SolutionConstraintEvaluatorV2 for unified constraint checking matching Calibration
- Full taxonomy:
  - AGENT_STALE_CHALLENGE_READY (S2 stale > 0, S3 TSR > S2 TSR, S3 stale == 0)
  - STALE_INSENSITIVE_FOR_QWEN7B (S2 stale == 0)
  - STALE_AFFECTED_WITHOUT_TARGET_REPAIR (S2 stale > 0, S3 does not recover)
  - TARGET_MEMORY_HARMFUL (S3 TSR < S0 TSR)
  - TARGET_MEMORY_STALE_REGRESSION (S3 stale > S0 stale)
  - EVOLUTION_CONTROL

Outputs:
- runs/scale-agent-challenge-v2/<tid>/<cond>_seed<seed>.json
- data/scale_agent_challenge_v2_status.jsonl
- reports/scale-agent-challenge-v2.md
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
from scripts.evaluate_solution_constraints_v2 import SolutionConstraintEvaluatorV2
from scripts.run_causal_counterfactual_v2 import load_workspace
from transformers import AutoTokenizer, AutoModelForCausalLM

SCALE_MANIFEST_PATH = "/code/rolemem-agent-memory/data/track_a_scale_manifest.jsonl"
SCALE_HIST_DIR = "/code/rolemem-agent-memory/runs/historical-memory-writer-scale"
SCALE_TARGET_PATH = "/code/rolemem-agent-memory/data/handoff_target_memory_scale.json"
TARGET_AUDIT_DIR = "/code/rolemem-agent-memory/data/scale_target_memory_audit_v3"
OUTPUT_BASE = "/code/rolemem-agent-memory/runs/scale-agent-challenge-v2"
STATUS_JSONL = "/code/rolemem-agent-memory/data/scale_agent_challenge_v2_status.jsonl"
REPORT_PATH = "/code/rolemem-agent-memory/reports/scale-agent-challenge-v2.md"
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


def run_scale_agent_challenge_v2():
    print("=== Running Track A Scale Agent Challenge V2 (3 Seeds: 42, 123, 999) ===")
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
        constraint_evaluator = SolutionConstraintEvaluatorV2(tid)

        retriever = RepoBM25Retriever(target_ws)
        s_tokenizer = SimpleTokenizer()
        repo_context, repo_tokens = retriever.retrieve_context(
            query=task_prompt,
            tokenizer=s_tokenizer,
            max_tokens=1200
        )

        target_audit_file = os.path.join(TARGET_AUDIT_DIR, f"{tid}.json")
        target_verified = False
        target_claim = {}
        if os.path.exists(target_audit_file):
            with open(target_audit_file) as f:
                ta = json.load(f)
                if ta.get("provenance_status") == "TARGET_MEMORY_VERIFIED":
                    target_verified = True
                    target_claim = ta.get("claim", {})

        valid_hist_count = 0
        h0_stale_count = 0
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
            s0_c_res = constraint_evaluator.evaluate_code(s0_code, run_id=f"S0_seed{seed}")
            s0_c_pass = (s0_c_res.get("overall_status") == "PASS")
            s0_succ = s0_pass and (not s0_ast.stale_active_use) and s0_c_pass
            if s0_ast.stale_active_use: h0_stale_count += 1
            if s0_succ: h0_tsr_count += 1

            with open(s0_out_path, "w", encoding="utf-8") as f:
                json.dump({
                    "task_id": tid, "condition": "S0",
                    "requested_seed": seed, "actual_generation_seed": seed, "attempt": 0,
                    "memory_source": "NO_MEMORY",
                    "overall_task_success": s0_succ, "pytest_pass": s0_pass, "constraint_pass": s0_c_pass,
                    "is_stale_action": s0_ast.stale_active_use, "parsed_code": s0_code
                }, f, indent=2)

            # 2. S2: Agent A Historical Memory
            hist_file = os.path.join(SCALE_HIST_DIR, tid, f"{seed}.json")
            hist_stmt = None
            actual_gen_seed = seed
            attempt_num = 0
            if os.path.exists(hist_file):
                with open(hist_file) as f:
                    h_data = json.load(f)
                    actual_gen_seed = h_data.get("seed", seed)
                    attempt_num = h_data.get("attempt", 0)
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
                s2_c_res = constraint_evaluator.evaluate_code(s2_code, run_id=f"S2_seed{seed}")
                s2_c_pass = (s2_c_res.get("overall_status") == "PASS")
                s2_succ = s2_pass and (not s2_ast.stale_active_use) and s2_c_pass
                if s2_ast.stale_active_use: h2_stale_count += 1
                if s2_succ: h2_tsr_count += 1

                with open(s2_out_path, "w", encoding="utf-8") as f:
                    json.dump({
                        "task_id": tid, "condition": "S2",
                        "requested_seed": seed, "actual_generation_seed": actual_gen_seed, "attempt": attempt_num,
                        "memory_source": "AGENT_A_HISTORICAL",
                        "statement": hist_stmt, "overall_task_success": s2_succ, "pytest_pass": s2_pass,
                        "constraint_pass": s2_c_pass, "is_stale_action": s2_ast.stale_active_use, "parsed_code": s2_code
                    }, f, indent=2)
            else:
                with open(s2_out_path, "w", encoding="utf-8") as f:
                    json.dump({
                        "task_id": tid, "condition": "S2",
                        "requested_seed": seed, "actual_generation_seed": actual_gen_seed, "attempt": attempt_num,
                        "memory_source": "INVALID_HISTORICAL_MEMORY",
                        "overall_task_success": False, "pytest_pass": False, "constraint_pass": False, "is_stale_action": False
                    }, f, indent=2)

            # 3. S3: Verified Target Memory (Zero Fallback)
            s3_out_path = os.path.join(task_out_dir, f"S3_seed{seed}.json")
            if target_verified and target_claim.get("statement"):
                target_stmt = target_claim["statement"]
                torch.manual_seed(seed)
                mem_block = format_memory_block([target_stmt])
                s3_prompt = f"TASK:\n{task_prompt}\n\n{mem_block}CURRENT REPOSITORY CONTEXT:\n{repo_context}\n\nProvide clean, complete Python code for {target_file} inside ```python ... ```."
                s3_msgs = [{"role": "user", "content": s3_prompt}]
                s3_chat = tokenizer.apply_chat_template(s3_msgs, tokenize=False, add_generation_prompt=True)
                s3_inputs = tokenizer(s3_chat, return_tensors="pt").to("cuda")
                with torch.no_grad():
                    s3_gen = model.generate(**s3_inputs, max_new_tokens=400, temperature=0.2, do_sample=True)
                s3_code = extract_code(tokenizer.decode(s3_gen[0][s3_inputs.input_ids.shape[1]:], skip_special_tokens=True))
                s3_ast = ASTStaleActionDetectorV2.analyze(s3_code, item)
                s3_pass, s3_log = executor.execute_in_sandbox(target_ws, target_file, s3_code, hidden_test_code)
                s3_c_res = constraint_evaluator.evaluate_code(s3_code, run_id=f"S3_seed{seed}")
                s3_c_pass = (s3_c_res.get("overall_status") == "PASS")
                s3_succ = s3_pass and (not s3_ast.stale_active_use) and s3_c_pass
                if s3_ast.stale_active_use: h3_stale_count += 1
                if s3_succ: h3_tsr_count += 1

                with open(s3_out_path, "w", encoding="utf-8") as f:
                    json.dump({
                        "task_id": tid, "condition": "S3",
                        "requested_seed": seed, "actual_generation_seed": seed, "attempt": 0,
                        "memory_source": "TARGET_MEMORY_VERIFIED",
                        "statement": target_stmt, "overall_task_success": s3_succ, "pytest_pass": s3_pass,
                        "constraint_pass": s3_c_pass, "is_stale_action": s3_ast.stale_active_use, "parsed_code": s3_code
                    }, f, indent=2)
            else:
                with open(s3_out_path, "w", encoding="utf-8") as f:
                    json.dump({
                        "task_id": tid, "condition": "S3",
                        "requested_seed": seed, "actual_generation_seed": seed, "attempt": 0,
                        "memory_source": "S3_INVALID_TARGET_MEMORY",
                        "overall_task_success": False, "pytest_pass": False, "constraint_pass": False, "is_stale_action": False
                    }, f, indent=2)

        # Classify transition with full taxonomy
        if is_control:
            category = "EVOLUTION_CONTROL"
        elif h3_stale_count > h0_stale_count:
            category = "TARGET_MEMORY_STALE_REGRESSION"
        elif h3_tsr_count < h0_tsr_count:
            category = "TARGET_MEMORY_HARMFUL"
        elif h2_stale_count > 0:
            if h3_tsr_count > h2_tsr_count and h3_stale_count == 0:
                category = "AGENT_STALE_CHALLENGE_READY"
            else:
                category = "STALE_AFFECTED_WITHOUT_TARGET_REPAIR"
        else:
            category = "STALE_INSENSITIVE_FOR_QWEN7B"

        rec = {
            "transition_id": tid,
            "category": category,
            "valid_historical_runs": valid_hist_count,
            "s0_tsr": f"{h0_tsr_count}/3",
            "s2_stale_rate": f"{h2_stale_count}/3",
            "s2_tsr": f"{h2_tsr_count}/3",
            "s3_stale_rate": f"{h3_stale_count}/3",
            "s3_tsr": f"{h3_tsr_count}/3"
        }
        challenge_records.append(rec)
        print(f"[{category}] {tid}: S0 TSR={h0_tsr_count}/3, S2 Stale={h2_stale_count}/3, S2 TSR={h2_tsr_count}/3, S3 Stale={h3_stale_count}/3, S3 TSR={h3_tsr_count}/3")

    with open(STATUS_JSONL, "w", encoding="utf-8") as f:
        for r in challenge_records:
            f.write(json.dumps(r) + "\n")

    # Generate Markdown Report
    md = []
    md.append("# Scale Agent Challenge Evaluation Report V2\n")
    md.append("## Executive Summary\n")
    md.append(f"- **Evaluated Candidates**: {len(target_specs)}")
    md.append("- **Condition Structure**: S0 (No memory) vs S2 (Agent-A Historical) vs S3 (Verified Target Memory)")
    md.append("- **Constraint Validation**: SolutionConstraintEvaluatorV2 fail-closed integration\n")
    md.append("## Classification Distribution\n")
    cat_counts = {}
    for r in challenge_records:
        cat_counts[r["category"]] = cat_counts.get(r["category"], 0) + 1
    for k, v in sorted(cat_counts.items()):
        md.append(f"- `{k}`: {v} / {len(challenge_records)} ({v/len(challenge_records)*100:.1f}%)")
    md.append("")
    md.append("## Candidate Performance Breakdown\n")
    md.append("| Transition ID | Category | S0 TSR | S2 Stale Rate | S2 TSR | S3 Stale Rate | S3 TSR |")
    md.append("| :--- | :--- | :---: | :---: | :---: | :---: | :---: |")
    for r in challenge_records:
        md.append(f"| `{r['transition_id']}` | **`{r['category']}`** | {r['s0_tsr']} | {r['s2_stale_rate']} | {r['s2_tsr']} | {r['s3_stale_rate']} | {r['s3_tsr']} |")
    md.append("")

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")

    print(f"\n[OK] Scale Agent Challenge V2 complete. Saved report to {REPORT_PATH}")


if __name__ == "__main__":
    run_scale_agent_challenge_v2()
