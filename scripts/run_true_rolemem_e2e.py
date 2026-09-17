"""
scripts/run_true_rolemem_e2e.py
Executes the authentic True RoleMem + Qwen2.5-Coder-7B End-to-End Evaluation.
Pipeline:
1. Base commit -> authentic SHA-256 digest of base artifact
2. Construct historical MemoryRecord bound to artifact_uri and authentic base digest
3. Target repository state (after/ workspace)
4. RoleMem selective_artifact_invalidation() detects hash mismatch
5. RoleMem retrieval filters stale memory and returns active memory
6. Formulates prompt with retrieved memory block
7. Qwen2.5-Coder-7B GPU inference (no valid_solution.py shortcuts)
8. Code extraction and AST stale analysis
9. Secure Bubblewrap Sandbox execution of hidden test
10. Writes comprehensive raw run telemetry to runs/true-rolemem-e2e/<task_id>/<condition>/<run>.json
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
RUNS_DIR = "/code/rolemem-agent-memory/runs/true-rolemem-e2e"
REPO_CACHE_ROOT = "/code/repo_cache"

REPO_DIR_MAP = {
    "pallets/werkzeug": os.path.join(REPO_CACHE_ROOT, "werkzeug"),
    "pallets/flask": os.path.join(REPO_CACHE_ROOT, "flask"),
    "pallets/click": os.path.join(REPO_CACHE_ROOT, "click"),
    "urllib3/urllib3": os.path.join(REPO_CACHE_ROOT, "urllib3"),
    "psf/requests": os.path.join(REPO_CACHE_ROOT, "requests"),
}

SEED_TASKS = [
    "trans_gold_werkzeug_01_cached_property",
    "trans_gold_click_01_option_parser",
    "trans_gold_flask_02_should_ignore_error",
    "trans_gold_urllib3_01_retry_allowed_methods"
]


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


def run_true_rolemem_e2e():
    print("=== Loading Qwen2.5-Coder-7B-Instruct on GPU ===")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_DIR,
        dtype=torch.float16,
        device_map="cuda:0"
    )

    results = []

    for tid in SEED_TASKS:
        print(f"\n--- Running True RoleMem E2E: {tid} ---")
        spec_path = os.path.join(SPECS_DIR, f"{tid}.json")
        with open(spec_path, "r", encoding="utf-8") as f:
            spec = json.load(f)

        fixture_dir = os.path.join(FIXTURES_DIR, tid)
        after_dir = os.path.join(fixture_dir, "after")
        git_dir = REPO_DIR_MAP[spec["repo_name"]]
        primary_file = spec["changed_files"][0]

        # 1. Authentic file hashes
        base_hash = compute_git_file_hash(git_dir, spec["base_commit"], primary_file)
        target_hash = compute_git_file_hash(git_dir, spec["target_commit"], primary_file)
        print(f"Base file SHA256: {base_hash[:12]}... | Target file SHA256: {target_hash[:12]}...")

        # 2. Workspace files
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

        # 3. RoleMem Store & authentic MemoryRecords
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
            statement=spec.get("stale_memory_candidate", ""),
            artifact_digest=base_hash
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
            statement=spec.get("valid_memory_candidate", ""),
            artifact_digest=target_hash
        )

        store.add_record(rec_stale)
        store.add_record(rec_valid)

        mem_before = [r.to_dict() for r in store.records.values()]

        # 4. Target repository state invalidation
        store.selective_artifact_invalidation(workspace_files)
        mem_after = [r.to_dict() for r in store.records.values()]

        filtered_ids = [r.memory_id for r in store.records.values() if r.status != "ACTIVE"]
        print(f"Invalidated memory IDs: {filtered_ids}")

        # 5. Retrieval
        task_prompt = spec["current_task"]
        target_file = spec["target_file"]

        retrieved = store.retrieve(
            query=task_prompt,
            role="coder",
            current_time=250.0,
            workspace_files=workspace_files
        )
        retrieved_ids = [r.memory_id for r in retrieved]
        print(f"Retrieved active memory IDs: {retrieved_ids}")

        if retrieved:
            delivered_text = f"Project Context Memory: {retrieved[0].statement}\n"
        else:
            delivered_text = ""

        # 6. LLM Generation
        prompt_text = (
            f"<|im_start|>system\nYou are an expert Python engineer for {spec['repo_name']}. "
            f"Implement the requested solution for {target_file}. "
            f"Provide ONLY executable python code inside ```python code block without extra explanations.<|im_end|>\n"
            f"<|im_start|>user\n"
            f"{delivered_text}"
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
                do_sample=False
            )
        latency = time.time() - t0
        gen_tokens = outputs.shape[1] - prompt_tokens
        gen_text = tokenizer.decode(outputs[0][prompt_tokens:], skip_special_tokens=True)

        parsed_code = extract_code(gen_text)

        # 7. AST Stale Analysis
        ast_res = ASTStaleActionDetector.analyze_spec(parsed_code, spec)

        # 8. Sandbox Execution
        custom_bin = os.path.join("/code/rolemem-agent-memory/.venvs", tid, "bin")
        if os.path.exists(custom_bin):
            executor = SecureSandboxExecutor(custom_env_bin_dir=custom_bin)
        else:
            executor = SecureSandboxExecutor()

        passed, pytest_log = executor.execute_in_sandbox(
            workspace_files=workspace_files,
            target_file=target_file,
            generated_code=parsed_code,
            test_code=test_code
        )

        print(f"Generation: {gen_tokens} tokens, {latency:.2f}s | AST Stale: {ast_res.stale_active_use} | Sandbox Pytest: {passed}")

        run_record = {
            "task_id": tid,
            "track": spec.get("track", "A"),
            "repo_name": spec["repo_name"],
            "model_revision": "c03e6d358207e414f1eca0bb1891e29f1db0e242",
            "prompt": prompt_text,
            "memory_before_validation": mem_before,
            "memory_after_validation": mem_after,
            "retrieved_memory_ids": retrieved_ids,
            "filtered_memory_ids": filtered_ids,
            "memory_text_delivered_to_model": delivered_text,
            "raw_generation": gen_text,
            "parsed_code": parsed_code,
            "artifact_digests": {
                "base_commit_digest": base_hash,
                "target_commit_digest": target_hash
            },
            "pytest_result": passed,
            "pytest_log": pytest_log,
            "ast_result": {
                "stale_active_use": ast_res.stale_active_use,
                "stale_mentions": ast_res.stale_mentions,
                "active_nodes": [n.node_type for n in ast_res.active_nodes]
            },
            "latency": round(latency, 2),
            "token_usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": gen_tokens
            }
        }

        # Save to runs/true-rolemem-e2e/<task_id>/full_e2e/run_0.json
        out_dir = os.path.join(RUNS_DIR, tid, "full_e2e")
        os.makedirs(out_dir, exist_ok=True)
        run_path = os.path.join(out_dir, "run_0.json")
        with open(run_path, "w", encoding="utf-8") as f:
            json.dump(run_record, f, indent=2)

        results.append(run_record)

    summary_path = os.path.join(RUNS_DIR, "true_rolemem_e2e_summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\nWrote all true E2E runs to {RUNS_DIR}")


if __name__ == "__main__":
    run_true_rolemem_e2e()
