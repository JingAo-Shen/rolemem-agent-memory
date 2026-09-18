"""
scripts/run_real_agent_handoff.py
Executes the Real Agent-Generated Memory Handoff E2E Pipeline on Qwen2.5-Coder-7B.
Compares four conditions across real repository tasks:
  H0: No Memory (Zero-shot)
  H1: Oracle Memory
  H2: Agent-Generated Memory without Invalidation (Stale Hand-off)
  H3: Agent-Generated Memory with RoleMem Selective Invalidation

Evaluates in Bubblewrap sandbox using SecureSandboxExecutor and ASTStaleActionDetector.
Saves raw per-task generation telemetry and dynamic comparative summary.
"""

import os
import sys
import json
import torch
import hashlib
import subprocess
from typing import Dict, Any, List, Tuple

sys.path.insert(0, "/code/rolemem-agent-memory")
from src.rolemem_core_v1 import RoleMemStoreV1
from src.schema_v1 import MemoryRecordV1
from src.sandbox_secure import SecureSandboxExecutor
from src.stale_detector_ast import ASTStaleActionDetector
from transformers import AutoTokenizer, AutoModelForCausalLM

TASKS = [
    "trans_gold_werkzeug_01_cached_property",
    "trans_gold_click_02_isolated_filesystem",
    "trans_gold_requests_01_tls_context_adapter",
    "trans_gold_urllib3_01_retry_allowed_methods",
]

REPO_MAP = {
    "pallets/werkzeug": "/code/repo_cache/werkzeug",
    "pallets/click": "/code/repo_cache/click",
    "psf/requests": "/code/repo_cache/requests",
    "urllib3/urllib3": "/code/repo_cache/urllib3",
}

OUTPUT_DIR = "/code/rolemem-agent-memory/runs/real-agent-handoff"
SPECS_DIR = "/code/rolemem-agent-memory/data/specs"
FIXTURES_DIR = "/code/rolemem-agent-memory/fixtures_v2"
WRITER_DIR = "/code/rolemem-agent-memory/runs/memory-writer"


def load_workspace_files(fixture_dir: str) -> Dict[str, str]:
    files = {}
    after_dir = os.path.join(fixture_dir, "after")
    if not os.path.exists(after_dir):
        return files
    for root, _, fnames in os.walk(after_dir):
        for fn in fnames:
            abs_p = os.path.join(root, fn)
            rel_p = os.path.relpath(abs_p, after_dir)
            try:
                with open(abs_p, "r", encoding="utf-8", errors="ignore") as f:
                    files[rel_p] = f.read()
            except Exception:
                pass
    return files


def extract_code(raw_text: str) -> str:
    if "```python" in raw_text:
        return raw_text.split("```python")[1].split("```")[0].strip()
    elif "```" in raw_text:
        return raw_text.split("```")[1].split("```")[0].strip()
    return raw_text.strip()


def run_handoff():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model_dir = "/code/rolemem-agent-memory/models/qwen2.5-coder-7b"
    print(f"Loading Qwen2.5-Coder-7B from {model_dir} on {device}...")
    tokenizer = AutoTokenizer.from_pretrained(model_dir, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        model_dir,
        torch_dtype=torch.float16 if device == "cuda" else torch.float32,
        device_map="auto" if device == "cuda" else None
    )
    model.eval()

    detector = ASTStaleActionDetector()

    results_by_condition = {"H0": 0, "H1": 0, "H2": 0, "H3": 0}
    stale_calls_by_condition = {"H0": 0, "H1": 0, "H2": 0, "H3": 0}
    total_evals_per_condition = len(TASKS) * 3  # 3 seeds per task

    task_summaries = []

    for tid in TASKS:
        spec_p = os.path.join(SPECS_DIR, f"{tid}.json")
        with open(spec_p) as f:
            spec = json.load(f)

        fixture_dir = os.path.join(FIXTURES_DIR, tid)
        ws_files = load_workspace_files(fixture_dir)

        primary_file = spec["changed_files"][0]
        repo_path = REPO_MAP[spec["repo_name"]]
        base_commit = spec["base_commit"]
        target_commit = spec["target_commit"]

        # Real git hash of base file
        try:
            base_content = subprocess.check_output(
                ["git", "-C", repo_path, "show", f"{base_commit}:{primary_file}"],
                stderr=subprocess.DEVNULL
            )
            base_digest = hashlib.sha256(base_content).hexdigest()
        except Exception:
            base_digest = "base_digest_dummy"

        # Load real Agent A memory writer records
        writer_p = os.path.join(WRITER_DIR, tid, "seed_42.json")
        with open(writer_p) as f:
            writer_data = json.load(f)

        agent_generated_records = writer_data.get("memory_records", [])
        agent_claims = writer_data.get("parsed_claims", [])

        # Choose primary agent-generated statement
        target_agent_stmt = agent_claims[0]["statement"] if agent_claims else spec["valid_memory_candidate"]

        # Venv and hidden test
        venv_path = f"/code/rolemem-agent-memory/.venvs/{tid}/bin"
        executor = SecureSandboxExecutor(custom_env_bin_dir=venv_path)

        with open(os.path.join(fixture_dir, "hidden_tests", "test_evaluation.py")) as f:
            hidden_test_code = f.read()

        print(f"\n========================================================")
        print(f"Running Real Handoff E2E on Task: {tid}")
        print(f"========================================================")

        task_detail = {"task_id": tid, "conditions": {}}

        for cond in ["H0", "H1", "H2", "H3"]:
            cond_passes = 0
            cond_stale_count = 0
            runs = []

            for seed in [42, 123, 999]:
                torch.manual_seed(seed)

                # Set up memory context for Agent B
                mem_context = ""
                if cond == "H0":
                    mem_context = ""
                elif cond == "H1":
                    mem_context = f"[PROJECT MEMORY CONTEXT]\n- {spec['valid_memory_candidate']}\n"
                elif cond == "H2":
                    # Stale hand-off: Agent B receives uninvalidated base memory
                    mem_context = f"[PROJECT MEMORY CONTEXT]\n- {spec['stale_memory_candidate']}\n"
                elif cond == "H3":
                    # RoleMem Active Memory Store
                    store = RoleMemStoreV1()
                    # 1. Base memory added by Agent A at base commit
                    base_mem = MemoryRecordV1(
                        memory_id=f"mem_base_{tid}",
                        artifact_uri=primary_file,
                        artifact_type="file",
                        symbol=spec.get("changed_symbols", [None])[0],
                        source_commit=base_commit,
                        observed_at=100.0,
                        evidence_type="diff",
                        evidence_ref=f"{spec['repo_url']}/commit/{base_commit}",
                        valid_from=100.0,
                        valid_to=float("inf"),
                        status="ACTIVE",
                        statement=spec["stale_memory_candidate"],
                        artifact_digest=base_digest
                    )
                    store.add_record(base_mem)

                    # 2. Repo evolves -> Selective invalidation on target workspace files
                    store.selective_artifact_invalidation(ws_files)

                    # 3. Target memory written by Agent A
                    for rec_data in agent_generated_records:
                        target_mem = MemoryRecordV1(
                            memory_id=rec_data["memory_id"],
                            artifact_uri=rec_data["artifact_uri"],
                            artifact_type=rec_data["artifact_type"],
                            symbol=rec_data["symbol"],
                            source_commit=target_commit,
                            observed_at=200.0,
                            evidence_type="diff_analysis",
                            evidence_ref=rec_data["evidence_ref"],
                            valid_from=200.0,
                            valid_to=float("inf"),
                            status="ACTIVE",
                            statement=rec_data["statement"],
                            artifact_digest=rec_data["artifact_digest"]
                        )
                        store.add_record(target_mem)

                    # Retrieve active memories for current task
                    active = store.retrieve(
                        query=spec["current_task"],
                        role="coder",
                        current_time=250.0,
                        workspace_files=ws_files,
                        top_k=3
                    )
                    mem_lines = [f"- {m.statement}" for m in active]
                    mem_context = "[PROJECT MEMORY CONTEXT]\n" + "\n".join(mem_lines) + "\n" if mem_lines else ""

                prompt = f"""You are an expert software engineer working on this repository.

{mem_context}
[TASK]
{spec['current_task']}

Write the complete Python code for {spec['target_file']}. Output only executable Python code enclosed in ```python ```.
"""
                msgs = [{"role": "user", "content": prompt}]
                chat = tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
                inputs = tokenizer(chat, return_tensors="pt").to(device)

                with torch.no_grad():
                    outs = model.generate(
                        **inputs,
                        max_new_tokens=350,
                        do_sample=True,
                        temperature=0.2
                    )

                gen = tokenizer.decode(outs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True)
                code = extract_code(gen)

                # AST stale check
                stale_res = detector.analyze(code, spec)
                has_stale = stale_res.stale_active_use
                if has_stale:
                    cond_stale_count += 1
                    stale_calls_by_condition[cond] += 1

                # Execute in Bubblewrap Sandbox
                passed, log = executor.execute_in_sandbox(ws_files, spec["target_file"], code, hidden_test_code)
                if passed:
                    cond_passes += 1
                    results_by_condition[cond] += 1

                print(f"  {cond} [seed {seed}]: passed={passed}, has_stale_action={has_stale}")
                runs.append({
                    "seed": seed,
                    "passed": passed,
                    "has_stale_action": has_stale,
                    "code_snippet": code[:150],
                    "log_preview": log[-300:] if log else ""
                })

            tsr = round(cond_passes / 3, 2)
            task_detail["conditions"][cond] = {
                "passed_runs": cond_passes,
                "total_runs": 3,
                "tsr": tsr,
                "stale_actions_count": cond_stale_count,
                "runs": runs
            }
            print(f"Condition {cond} TSR for {tid}: {tsr} (stale actions: {cond_stale_count})")

        task_summaries.append(task_detail)
        task_out_p = os.path.join(OUTPUT_DIR, f"{tid}.json")
        with open(task_out_p, "w") as f:
            json.dump(task_detail, f, indent=2)

    # Compute overall metrics
    overall_tsr = {cond: round(results_by_condition[cond] / total_evals_per_condition, 4) for cond in results_by_condition}
    stale_rate = {cond: round(stale_calls_by_condition[cond] / total_evals_per_condition, 4) for cond in stale_calls_by_condition}

    summary = {
        "tasks_evaluated": TASKS,
        "total_evals_per_condition": total_evals_per_condition,
        "results_by_condition": results_by_condition,
        "overall_tsr": overall_tsr,
        "stale_calls_by_condition": stale_calls_by_condition,
        "stale_action_rate": stale_rate,
        "oracle_tsr": overall_tsr["H1"],
        "agent_generated_rolemem_tsr": overall_tsr["H3"],
        "tsr_delta_agent_vs_oracle": round(overall_tsr["H3"] - overall_tsr["H1"], 4),
        "task_summaries": task_summaries
    }

    summary_file = os.path.join(OUTPUT_DIR, "real_handoff_summary.json")
    with open(summary_file, "w") as f:
        json.dump(summary, f, indent=2)

    print("\n========================================================")
    print("Real Agent-Generated Handoff E2E Evaluation Summary")
    print("========================================================")
    for cond in ["H0", "H1", "H2", "H3"]:
        print(f"Condition {cond}: TSR = {overall_tsr[cond]:.2f} ({results_by_condition[cond]}/{total_evals_per_condition}), Stale Rate = {stale_rate[cond]:.2f}")
    print(f"Oracle TSR (H1):                     {overall_tsr['H1']:.2f}")
    print(f"Agent-Generated + RoleMem TSR (H3):  {overall_tsr['H3']:.2f}")
    print(f"Dynamic Parity Delta (H3 - H1):      {summary['tsr_delta_agent_vs_oracle']:+.2f}")
    print(f"Saved summary to {summary_file}")
    print("========================================================")


if __name__ == "__main__":
    run_handoff()
