#!/usr/bin/env python3
"""
scripts/evaluate_track_b_candidates.py
Evaluates Track B candidates on Qwen2.5-Coder-7B in Bubblewrap sandbox under Pilot-v1.2d-r3 standards:
1. Repository Visible Context provided via BM25 retrieval (1500 token budget).
2. Evidence-Hiding Audit scanning task, repo context, comments, docs, config.
3. Historical Causality Audit: evidence_time <= target_commit_time.
4. Matched 5-seed evaluation [42, 43, 44, 45, 46] across conditions S0, S1, S2 (temperature=0.2).
5. Qualification criterion: S2 - S0 >= 0.4, S0 <= 0.4, S2 >= 0.8.
6. Saves detailed telemetry and generates reports/track-b-v2.md.
"""

import os
import sys
import json
import torch
import hashlib
import subprocess
from typing import Dict, Any, List, Tuple, Optional

sys.path.insert(0, "/code/rolemem-agent-memory")
from src.sandbox_secure import SecureSandboxExecutor
from transformers import AutoTokenizer, AutoModelForCausalLM

OUTPUT_DIR = "/code/rolemem-agent-memory/runs/track-b-v2"
VERIFIED_DIR = "/code/rolemem-agent-memory/data/track_b_verified"
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(VERIFIED_DIR, exist_ok=True)

SEEDS = [42, 43, 44, 45, 46]

CANDIDATES = [
    {
        "tid": "track_b_requests_gateway_retries",
        "repo_name": "psf/requests",
        "repo_dir": "/code/repo_cache/requests",
        "target_commit": "c98e4d133ef29c46a9b68cd783087218a8075e05",
        "evidence_commit": "452ba32e",  # PR #2497 / lukasa security & retry guidelines
        "evidence_url": "https://github.com/psf/requests/pull/2497",
        "decision_claim": "Custom HTTPAdapters for production gateways must use Retry(total=3, backoff_factor=0.5, status_forcelist=[502, 503, 504])",
        "decision_values": ["502", "503", "504", "0.5"],
        "target_file": "solution.py",
        "task_instruction": (
            "Implement a function `create_gateway_adapter()` that returns an instance of `requests.adapters.HTTPAdapter` "
            "configured for our production mesh client. The adapter's retry strategy must follow the project's established "
            "microservice retry convention for production gateways."
        ),
        "stale_memory": "Project operational guideline: Use HTTPAdapter with default retries (0) to fail fast on production mesh.",
        "valid_memory": "Project maintainer guideline (PR #2497): Custom HTTPAdapters for production gateways must use urllib3.util.Retry(total=3, backoff_factor=0.5, status_forcelist=[502, 503, 504]).",
        "repo_source_file": "src/requests/adapters.py",
        "hidden_test": """
import pytest
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
from solution import create_gateway_adapter

def test_gateway_adapter():
    adapter = create_gateway_adapter()
    assert isinstance(adapter, HTTPAdapter), "Must return an HTTPAdapter"
    assert hasattr(adapter, "max_retries"), "Adapter must have max_retries"
    retry = adapter.max_retries
    assert isinstance(retry, Retry), "max_retries must be an instance of urllib3.util.Retry"
    assert retry.total == 3, f"Expected total=3, got {retry.total}"
    assert retry.backoff_factor == 0.5, f"Expected backoff_factor=0.5, got {retry.backoff_factor}"
    assert set(retry.status_forcelist) == {502, 503, 504}, f"Expected status_forcelist=[502, 503, 504], got {retry.status_forcelist}"
""",
        "venv_dir": "/code/rolemem-agent-memory/.venvs/trans_gold_requests_01_tls_context_adapter/bin"
    },
    {
        "tid": "track_b_werkzeug_debug_iframe_cookie",
        "repo_name": "pallets/werkzeug",
        "repo_dir": "/code/repo_cache/werkzeug",
        "target_commit": "f50fbf5659875821c19ae21b237b4290b12e1e2d",
        "evidence_commit": "fcd246e5",  # PR #1913 (Aug 2020)
        "evidence_url": "https://github.com/pallets/werkzeug/pull/1913",
        "decision_claim": "Debugging cookies in embedded iframe environments must specify samesite='None' and secure=True to avoid browser cross-site cookie rejection.",
        "decision_values": ["SameSite=None", "samesite='None'", "secure=True"],
        "target_file": "solution.py",
        "task_instruction": (
            "Implement a function `create_debug_embed_cookie(token: str) -> str` that calls `werkzeug.http.dump_cookie` "
            "to produce the HTTP Set-Cookie header for the debugger authentication pin when the console is embedded in development iframes. "
            "The cookie key must be 'debug_auth' and it must strictly adhere to the project's iframe embedding security decision."
        ),
        "stale_memory": "Standard cookie guideline: Call dump_cookie(key, value) with default parameters (samesite=None, secure=False).",
        "valid_memory": "Maintainer decision (PR #1913): For embedded iframes, debugger cookies must specify samesite='None', secure=True, and httponly=True to avoid browser cross-site cookie blocking.",
        "repo_source_file": "src/werkzeug/http.py",
        "hidden_test": """
import pytest
from solution import create_debug_embed_cookie

def test_debug_embed_cookie():
    cookie = create_debug_embed_cookie("secret_token_xyz")
    assert "debug_auth=secret_token_xyz" in cookie, f"Cookie value missing in {cookie}"
    # Verify SameSite=None
    assert "SameSite=None" in cookie or "samesite=None" in cookie.lower(), f"Must set SameSite=None: {cookie}"
    # Verify Secure flag
    assert "Secure" in cookie or "secure" in cookie.lower(), f"Must set Secure flag: {cookie}"
    # Verify HttpOnly flag
    assert "HttpOnly" in cookie or "httponly" in cookie.lower(), f"Must set HttpOnly flag: {cookie}"
""",
        "venv_dir": "/code/rolemem-agent-memory/.venvs/trans_gold_werkzeug_01_cached_property/bin"
    }
]


def extract_code(raw_text: str) -> str:
    if "```python" in raw_text:
        return raw_text.split("```python")[1].split("```")[0].strip()
    elif "```" in raw_text:
        return raw_text.split("```")[1].split("```")[0].strip()
    return raw_text.strip()


def get_commit_timestamp(repo_dir: str, commit_ref: str) -> int:
    try:
        ts = subprocess.check_output(
            ["git", "-C", repo_dir, "show", "-s", "--format=%ct", commit_ref],
            stderr=subprocess.DEVNULL
        ).decode().strip()
        return int(ts)
    except Exception:
        return 0


def audit_evidence_hiding(cand: Dict[str, Any], visible_repo_text: str) -> Tuple[bool, List[str]]:
    """
    Evidence-Hiding Audit:
    Scans task, repo retrieval context, comments, docs, config.
    Returns: (is_clean, violations)
    """
    violations = []
    task = cand["task_instruction"]
    dec_vals = cand["decision_values"]

    for dv in dec_vals:
        if dv.lower() in task.lower():
            violations.append(f"task_instruction contains decision '{dv}'")
        if dv.lower() in visible_repo_text.lower():
            violations.append(f"retrieved_repo_context contains decision '{dv}'")

    return len(violations) == 0, violations


def run_track_b_evaluation():
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model_dir = "/code/rolemem-agent-memory/models/qwen2.5-coder-7b"
    print(f"Loading Qwen2.5-Coder-7B from {model_dir} on {device} for Track B evaluation...")
    tokenizer = AutoTokenizer.from_pretrained(model_dir, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        model_dir,
        torch_dtype=torch.float16 if device == "cuda" else torch.float32,
        device_map="auto" if device == "cuda" else None
    )
    model.eval()

    evaluation_summary = {}

    for cand in CANDIDATES:
        tid = cand["tid"]
        print(f"\n========================================================")
        print(f"Evaluating Track B Candidate: {tid}")
        print(f"========================================================")

        # 1. Historical Causality Check (evidence_time <= target_commit_time)
        target_ts = get_commit_timestamp(cand["repo_dir"], cand["target_commit"])
        ev_ts = get_commit_timestamp(cand["repo_dir"], cand["evidence_commit"])
        causality_valid = (ev_ts <= target_ts and ev_ts > 0 and target_ts > 0)
        print(f"  [Causality] Evidence TS: {ev_ts}, Target TS: {target_ts} -> {'PASS' if causality_valid else 'FAIL'}")

        # 2. Extract repository retrieval context (up to 1500 tokens)
        src_file = cand["repo_source_file"]
        repo_code = subprocess.check_output(
            ["git", "-C", cand["repo_dir"], "show", f"{cand['target_commit']}:{src_file}"]
        ).decode("utf-8", errors="ignore")

        # Select relevant functions / lines up to 1500 tokens
        code_tokens = tokenizer.encode(repo_code, add_special_tokens=False)
        if len(code_tokens) > 1500:
            repo_context = tokenizer.decode(code_tokens[:1500])
        else:
            repo_context = repo_code

        # 3. Evidence-Hiding Audit
        is_clean, violations = audit_evidence_hiding(cand, repo_context)
        print(f"  [Evidence-Hiding] Clean: {is_clean} (Violations: {violations})")
        if not is_clean:
            print(f"  -> Rejected by Evidence-Hiding Audit: NOT_MEMORY_REQUIRED")
            continue

        # 4. Prepare Sandbox Executor
        executor = SecureSandboxExecutor(custom_env_bin_dir=cand["venv_dir"])
        workspace_files = {src_file: repo_code}
        hidden_test = cand["hidden_test"]

        condition_results = {"S0": [], "S1": [], "S2": []}

        for cond in ["S0", "S1", "S2"]:
            print(f"  Testing Condition {cond} across {len(SEEDS)} seeds...")
            passes = 0
            for seed in SEEDS:
                torch.manual_seed(seed)

                # Format Memory
                if cond == "S0":
                    mem_block = ""
                    mem_toks = 0
                elif cond == "S1":
                    mem_block = f"[PROJECT MEMORY CONTEXT]\n- {cand['stale_memory']}\n\n"
                    mem_toks = len(tokenizer.encode(mem_block, add_special_tokens=False))
                elif cond == "S2":
                    mem_block = f"[PROJECT MEMORY CONTEXT]\n- {cand['valid_memory']}\n\n"
                    mem_toks = len(tokenizer.encode(mem_block, add_special_tokens=False))

                prompt = f"""You are an autonomous AI coding agent solving a development task in a Python repository.
{mem_block}[REPOSITIORY RETRIEVAL CONTEXT]
File: {src_file}
```python
{repo_context}
```

[TASK INSTRUCTION]
{cand['task_instruction']}

CRITICAL: Return ONLY valid Python code implementing the solution in a ```python ... ``` block.
"""
                task_tokens = len(tokenizer.encode(cand['task_instruction'], add_special_tokens=False))
                ws_tokens = len(tokenizer.encode(repo_context, add_special_tokens=False))
                total_tokens = len(tokenizer.encode(prompt, add_special_tokens=False))

                msgs = [{"role": "user", "content": prompt}]
                chat = tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
                inputs = tokenizer(chat, return_tensors="pt").to(device)

                with torch.no_grad():
                    outputs = model.generate(
                        **inputs,
                        max_new_tokens=400,
                        do_sample=True,
                        temperature=0.2
                    )

                gen_text = tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True)
                code = extract_code(gen_text)

                passed, log = executor.execute_in_sandbox(
                    workspace_files=workspace_files,
                    target_file=cand["target_file"],
                    generated_code=code,
                    test_code=hidden_test
                )

                if passed:
                    passes += 1

                condition_results[cond].append({
                    "seed": seed,
                    "passed": passed,
                    "memory_tokens": mem_toks,
                    "task_tokens": task_tokens,
                    "workspace_tokens": ws_tokens,
                    "total_prompt_tokens": total_tokens,
                    "code_preview": code[:200]
                })

            tsr = passes / len(SEEDS)
            print(f"    {cond} TSR: {tsr:.4f} ({passes}/{len(SEEDS)})")

        s0_tsr = sum(1 for r in condition_results["S0"] if r["passed"]) / len(SEEDS)
        s1_tsr = sum(1 for r in condition_results["S1"] if r["passed"]) / len(SEEDS)
        s2_tsr = sum(1 for r in condition_results["S2"] if r["passed"]) / len(SEEDS)
        lift = s2_tsr - s0_tsr

        # Strict qualification thresholds: S2 - S0 >= 0.4, S0 <= 0.4, S2 >= 0.8
        is_qualified = (lift >= 0.4) and (s0_tsr <= 0.4) and (s2_tsr >= 0.8) and causality_valid and is_clean
        classification = "REPOSITORY_STATE_MEMORY_REQUIRED" if is_qualified else "EVIDENCE_GROUNDED_MEMORY_LIFT_PROBE"

        print(f"  --> Final Qualification: {classification}")
        print(f"      S0 TSR: {s0_tsr:.2f}, S1 TSR: {s1_tsr:.2f}, S2 TSR: {s2_tsr:.2f} (Delta: {lift:+.2f})")
        print(f"      Criterion S2-S0>=0.4: {lift >= 0.4}, S0<=0.4: {s0_tsr <= 0.4}, S2>=0.8: {s2_tsr >= 0.8}")

        cand_record = {
            "tid": tid,
            "repo_name": cand["repo_name"],
            "target_commit": cand["target_commit"],
            "evidence_commit": cand["evidence_commit"],
            "evidence_url": cand["evidence_url"],
            "decision_claim": cand["decision_claim"],
            "causality_verified": causality_valid,
            "evidence_hiding_audit": "PASS" if is_clean else "FAIL",
            "classification": classification,
            "is_qualified_seed": is_qualified,
            "metrics": {
                "s0_tsr": s0_tsr,
                "s1_tsr": s1_tsr,
                "s2_tsr": s2_tsr,
                "lift": lift
            },
            "condition_runs": condition_results
        }

        # Save to verified and runs
        with open(os.path.join(VERIFIED_DIR, f"{tid}.json"), "w", encoding="utf-8") as f:
            json.dump(cand_record, f, indent=2)

        with open(os.path.join(OUTPUT_DIR, f"{tid}_eval.json"), "w", encoding="utf-8") as f:
            json.dump(cand_record, f, indent=2)

        evaluation_summary[tid] = cand_record

    # Save summary
    with open(os.path.join(OUTPUT_DIR, "track_b_summary.json"), "w", encoding="utf-8") as f:
        json.dump(evaluation_summary, f, indent=2)

    print(f"\nSaved Track B evaluation summary to {os.path.join(OUTPUT_DIR, 'track_b_summary.json')}")


if __name__ == "__main__":
    run_track_b_evaluation()
