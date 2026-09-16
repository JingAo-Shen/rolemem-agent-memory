"""
scripts/run_benchmark_sanity_v2.py
Executes Multi-Seed Benchmark Sanity Evaluation (Pilot-v1.2d).
Evaluates 3 independent seeds (42, 123, 999) with temperature=0.2 across S0, S1, S2, S3:
- S0: No Memory
- S1: Raw Stale Memory
- S2: Oracle Valid Memory
- S3: RoleMem Full (genuine base/target artifact SHA-256 digests)

Rigorous Classification Rules:
- TASK_TOO_HARD: max(TSR_S0, TSR_S2, TSR_S3) == 0
- Track B:
  - NOT_MEMORY_REQUIRED: TSR_S0 == 1.0 and TSR_S2 == 1.0
  - TRACK_B_MEMORY_REQUIRED: TSR_S2 - TSR_S0 >= 0.33
  - UNRESOLVED: otherwise
- Track A:
  - TRACK_A_STALE_SENSITIVE: TSR_S0 - TSR_S1 >= 0.33
  - TRACK_A_API_EVOLUTION: max(TSR_S0, TSR_S2, TSR_S3) > 0 and StaleDegradation < 0.33

Outputs raw JSON telemetry to runs/sanity-v2/<task_id>/<condition>/seed_<seed>.json.
"""

import os
import sys
import json
import time
import hashlib
import subprocess
import torch
from typing import Dict, Any, List

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from transformers import AutoModelForCausalLM, AutoTokenizer
from src.schema_v1 import MemoryRecordV1
from src.rolemem_core_v1 import RoleMemStoreV1
from src.sandbox_secure import SecureSandboxExecutor
from src.stale_detector_ast import ASTStaleActionDetector

MODEL_DIR = "/code/rolemem-agent-memory/models/qwen2.5-coder-7b"
SPECS_DIR = "/code/rolemem-agent-memory/data/specs"
FIXTURES_DIR = "/code/rolemem-agent-memory/fixtures_v2"
RUNS_DIR = "/code/rolemem-agent-memory/runs/sanity-v2"
REPO_CACHE_ROOT = "/code/repo_cache"

REPO_DIR_MAP = {
    "pallets/werkzeug": os.path.join(REPO_CACHE_ROOT, "werkzeug"),
    "pallets/flask": os.path.join(REPO_CACHE_ROOT, "flask"),
    "pallets/click": os.path.join(REPO_CACHE_ROOT, "click"),
    "urllib3/urllib3": os.path.join(REPO_CACHE_ROOT, "urllib3"),
    "psf/requests": os.path.join(REPO_CACHE_ROOT, "requests"),
}

SANITY_TASKS = [
    "trans_gold_werkzeug_01_cached_property",
    "trans_gold_flask_02_should_ignore_error",
    "trans_gold_urllib3_01_retry_allowed_methods",
    "trans_gold_urllib3_02_empty_allowed_methods"
]

SEEDS = [42, 123, 999]
TEMPERATURE = 0.2


def extract_code(text: str) -> str:
    if "```python" in text:
        return text.split("```python", 1)[1].split("```", 1)[0].strip()
    if "```" in text:
        return text.split("```", 1)[0].strip()
    return text.strip()


def compute_git_file_hash(git_dir: str, commit: str, rel_path: str) -> str:
    res = subprocess.run(["git", "-C", git_dir, "show", f"{commit}:{rel_path}"], capture_output=True)
    if res.returncode != 0:
        return ""
    return hashlib.sha256(res.stdout).hexdigest()


def run_benchmark_sanity_v2():
    print(f"=== Loading Qwen2.5-Coder-7B-Instruct for Multi-Seed Sanity V2 ===")
    print(f"Seeds: {SEEDS} | Temperature: {TEMPERATURE}")

    tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_DIR,
        dtype=torch.float16,
        device_map="cuda:0"
    )

    summary_results = []

    for tid in SANITY_TASKS:
        spec_path = os.path.join(SPECS_DIR, f"{tid}.json")
        with open(spec_path, "r", encoding="utf-8") as f:
            spec = json.load(f)

        track = spec.get("track", "A")
        print(f"\n==========================================")
        print(f"Task: {tid} (Track {track})")
        print(f"==========================================")

        fixture_dir = os.path.join(FIXTURES_DIR, tid)
        after_dir = os.path.join(fixture_dir, "after")
        git_dir = REPO_DIR_MAP[spec["repo_name"]]
        primary_file = spec["changed_files"][0]

        # Authentic file digests
        base_digest = compute_git_file_hash(git_dir, spec["base_commit"], primary_file)
        target_digest = compute_git_file_hash(git_dir, spec["target_commit"], primary_file)

        # Workspace files
        workspace_files = {}
        for root, _, files in os.walk(after_dir):
            for fn in files:
                fp = os.path.join(root, fn)
                rel = os.path.relpath(fp, after_dir)
                with open(fp, "r", encoding="utf-8", errors="ignore") as f:
                    workspace_files[rel] = f.read()

        # Hidden test
        with open(os.path.join(fixture_dir, "hidden_tests", "test_evaluation.py"), "r", encoding="utf-8") as f:
            test_code = f.read()

        custom_bin = os.path.join("/code/rolemem-agent-memory/.venvs", tid, "bin")
        if os.path.exists(custom_bin):
            executor = SecureSandboxExecutor(custom_env_bin_dir=custom_bin)
        else:
            executor = SecureSandboxExecutor()

        target_file = spec["target_file"]
        task_prompt = spec["current_task"]
        stale_mem = spec.get("stale_memory_candidate", "")
        valid_mem = spec.get("valid_memory_candidate", "")

        condition_stats = {}

        for cond in ["S0", "S1", "S2", "S3"]:
            cond_dir = os.path.join(RUNS_DIR, tid, cond)
            os.makedirs(cond_dir, exist_ok=True)
            passes = []

            for seed in SEEDS:
                torch.manual_seed(seed)
                torch.cuda.manual_seed_all(seed)

                if cond == "S0":
                    mem_context = ""
                elif cond == "S1":
                    mem_context = f"Project Context Memory: {stale_mem}\n"
                elif cond == "S2":
                    mem_context = f"Project Context Memory: {valid_mem}\n"
                elif cond == "S3":
                    # RoleMem Full with authentic digests
                    store = RoleMemStoreV1()
                    rec_stale = MemoryRecordV1(
                        memory_id="mem_stale_1",
                        artifact_uri=primary_file,
                        artifact_type="file",
                        symbol=spec.get("changed_symbols", [None])[0],
                        source_commit=spec["base_commit"],
                        observed_at=100.0,
                        evidence_type="diff",
                        evidence_ref=spec["pr_url"],
                        valid_from=100.0,
                        valid_to=float("inf"),
                        status="ACTIVE",
                        role_tags=["coder"],
                        statement=stale_mem,
                        artifact_digest=base_digest
                    )
                    rec_valid = MemoryRecordV1(
                        memory_id="mem_valid_1",
                        artifact_uri=primary_file,
                        artifact_type="file",
                        symbol=spec.get("changed_symbols", [None])[0],
                        source_commit=spec["target_commit"],
                        observed_at=200.0,
                        evidence_type="diff",
                        evidence_ref=spec["pr_url"],
                        valid_from=200.0,
                        valid_to=float("inf"),
                        status="ACTIVE",
                        role_tags=["coder"],
                        statement=valid_mem,
                        artifact_digest=target_digest
                    )
                    store.add_record(rec_stale)
                    store.add_record(rec_valid)

                    store.selective_artifact_invalidation(workspace_files)
                    retrieved = store.retrieve(
                        query=task_prompt,
                        role="coder",
                        current_time=250.0,
                        workspace_files=workspace_files
                    )
                    if retrieved:
                        mem_context = f"Project Context Memory: {retrieved[0].statement}\n"
                    else:
                        mem_context = ""

                prompt_text = (
                    f"<|im_start|>system\nYou are an expert Python engineer for {spec['repo_name']}. "
                    f"Implement the requested solution for {target_file}. "
                    f"Provide ONLY executable python code inside ```python code block without extra explanations.<|im_end|>\n"
                    f"<|im_start|>user\n"
                    f"{mem_context}"
                    f"Task: {task_prompt}\n"
                    f"File: {target_file}\n<|im_end|>\n"
                    f"<|im_start|>assistant\n```python\n"
                )

                inputs = tokenizer(prompt_text, return_tensors="pt").to("cuda:0")
                prompt_tokens = inputs.input_ids.shape[1]

                t0 = time.time()
                with torch.no_grad():
                    outputs = model.generate(
                        **inputs,
                        max_new_tokens=300,
                        temperature=TEMPERATURE,
                        do_sample=True
                    )
                latency = time.time() - t0
                gen_tokens = outputs.shape[1] - prompt_tokens
                gen_text = tokenizer.decode(outputs[0][prompt_tokens:], skip_special_tokens=True)
                code = extract_code(gen_text)

                stale_symbols = [s.split(".")[-1] for s in spec.get("changed_symbols", [])]
                ast_res = ASTStaleActionDetector.analyze(code, stale_symbols)

                passed, pytest_log = executor.execute_in_sandbox(
                    workspace_files=workspace_files,
                    target_file=target_file,
                    generated_code=code,
                    test_code=test_code
                )
                passes.append(passed)

                run_data = {
                    "task_id": tid,
                    "condition": cond,
                    "seed": seed,
                    "temperature": TEMPERATURE,
                    "passed": passed,
                    "stale_ast": ast_res.stale_active_use,
                    "latency": round(latency, 2),
                    "prompt_tokens": prompt_tokens,
                    "gen_tokens": gen_tokens,
                    "code_snippet": code[:150],
                    "pytest_log_preview": pytest_log[:300]
                }
                seed_file = os.path.join(cond_dir, f"seed_{seed}.json")
                with open(seed_file, "w", encoding="utf-8") as f:
                    json.dump(run_data, f, indent=2)

            tsr = sum(1 for p in passes if p) / len(passes)
            condition_stats[cond] = {
                "tsr": round(tsr, 2),
                "passes": passes,
                "n_runs": len(passes)
            }
            print(f"[{cond}] TSR: {tsr:.2f} ({passes.count(True)}/{len(passes)})")

        tsr_s0 = condition_stats["S0"]["tsr"]
        tsr_s1 = condition_stats["S1"]["tsr"]
        tsr_s2 = condition_stats["S2"]["tsr"]
        tsr_s3 = condition_stats["S3"]["tsr"]

        max_solvability = max(tsr_s0, tsr_s2, tsr_s3)
        stale_deg = round(tsr_s0 - tsr_s1, 2)
        mem_lift = round(tsr_s2 - tsr_s0, 2)

        if max_solvability == 0:
            classification = "TASK_TOO_HARD"
        elif track == "B":
            if tsr_s0 == 1.0 and tsr_s2 == 1.0:
                classification = "NOT_MEMORY_REQUIRED"
            elif mem_lift >= 0.33:
                classification = "TRACK_B_MEMORY_REQUIRED"
            else:
                classification = "UNRESOLVED"
        else: # Track A
            if stale_deg >= 0.33:
                classification = "TRACK_A_STALE_SENSITIVE"
            else:
                classification = "TRACK_A_API_EVOLUTION"

        task_summary = {
            "task_id": tid,
            "track": track,
            "repo_name": spec["repo_name"],
            "tsr_s0": tsr_s0,
            "tsr_s1": tsr_s1,
            "tsr_s2": tsr_s2,
            "tsr_s3": tsr_s3,
            "stale_degradation": stale_deg,
            "memory_lift": mem_lift,
            "max_solvability": max_solvability,
            "classification": classification,
            "conditions": condition_stats
        }
        print(f"Classification: {classification} (Lift: {mem_lift}, Degradation: {stale_deg})")
        summary_results.append(task_summary)

    os.makedirs(RUNS_DIR, exist_ok=True)
    summary_path = os.path.join(RUNS_DIR, "sanity_v2_summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary_results, f, indent=2)
    print(f"\nMulti-Seed Sanity V2 Complete. Wrote summary to {summary_path}")


if __name__ == "__main__":
    run_benchmark_sanity_v2()
