import os
import sys
import json
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

sys.path.insert(0, "/code/rolemem-agent-memory")
from src.sandbox_secure import SecureSandboxExecutor

MODEL_DIR = "/code/rolemem-agent-memory/models/qwen2.5-coder-7b"
tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR, trust_remote_code=True)
model = AutoModelForCausalLM.from_pretrained(MODEL_DIR, torch_dtype=torch.float16, device_map="auto")
model.eval()

# Task 1: urllib3 Track B (Project-Specific Custom Retry Policy)
task1 = {
    "tid": "track_b_urllib3_custom_retry",
    "target_file": "custom_retry_policy.py",
    "task": "Implement `get_repository_retry_policy()` in `custom_retry_policy.py` returning a `urllib3.util.Retry` instance for external API integrations.",
    "memory": "Project architectural decision (PR #4102): External service integrations must use `urllib3.util.Retry(total=5, backoff_factor=0.5, status_forcelist=[429, 503])`.",
    "test": """
import pytest
from custom_retry_policy import get_repository_retry_policy

def test_custom_retry_policy():
    r = get_repository_retry_policy()
    assert r.total == 5, f"Expected total=5, got {r.total}"
    assert r.backoff_factor == 0.5, f"Expected backoff_factor=0.5, got {r.backoff_factor}"
    assert set(r.status_forcelist) == {429, 503}, f"Expected status_forcelist=[429, 503], got {r.status_forcelist}"
""",
    "venv": "/code/rolemem-agent-memory/.venvs/trans_gold_urllib3_01_retry_allowed_methods/bin",
    "ws_dir": "/code/rolemem-agent-memory/fixtures_v2/trans_gold_urllib3_01_retry_allowed_methods/after"
}

# Task 2: requests Track B (Internal Microservice Pool Policy)
task2 = {
    "tid": "track_b_requests_service_adapter",
    "target_file": "service_adapter.py",
    "task": "Implement `build_internal_service_adapter()` in `service_adapter.py` returning a `requests.adapters.HTTPAdapter` instance for internal microservice communication.",
    "memory": "Project infrastructure convention (PR #6520): Internal microservice HTTPAdapter must be configured with pool_connections=25, pool_maxsize=50, pool_block=True.",
    "test": """
import pytest
from service_adapter import build_internal_service_adapter

def test_service_adapter():
    a = build_internal_service_adapter()
    assert a._pool_connections == 25, f"Expected pool_connections=25, got {a._pool_connections}"
    assert a._pool_maxsize == 50, f"Expected pool_maxsize=50, got {a._pool_maxsize}"
    assert a._pool_block is True, f"Expected pool_block=True, got {a._pool_block}"
""",
    "venv": "/code/rolemem-agent-memory/.venvs/trans_gold_requests_01_tls_context_adapter/bin",
    "ws_dir": "/code/rolemem-agent-memory/fixtures_v2/trans_gold_requests_01_tls_context_adapter/after"
}

def evaluate_track_b(t_spec):
    print(f"\n==================================================")
    print(f"Evaluating Track B Seed: {t_spec['tid']}")
    print(f"==================================================")

    ws = {}
    for r, _, fns in os.walk(t_spec["ws_dir"]):
        for fn in fns:
            ap = os.path.join(r, fn)
            ws[os.path.relpath(ap, t_spec["ws_dir"])] = open(ap, errors="ignore").read()

    executor = SecureSandboxExecutor(custom_env_bin_dir=t_spec["venv"])

    results = {}
    runs_data = []
    for cond in ["S0", "S2"]:
        passes = 0
        mem_str = f"[PROJECT MEMORY CONTEXT]\n- {t_spec['memory']}\n" if cond == "S2" else ""
        for seed in [42, 123, 999]:
            torch.manual_seed(seed)
            prompt = f"""You are an expert engineer working on this repository.

{mem_str}
[TASK]
{t_spec['task']}

Write the complete Python code for {t_spec['target_file']}. Output only executable Python enclosed in ```python ```.
"""
            msgs = [{"role": "user", "content": prompt}]
            chat = tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
            inputs = tokenizer(chat, return_tensors="pt").to("cuda")
            with torch.no_grad():
                outs = model.generate(**inputs, max_new_tokens=250, do_sample=True, temperature=0.2)
            gen = tokenizer.decode(outs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True)
            code = gen.split("```python")[1].split("```")[0].strip() if "```python" in gen else gen.strip()

            p, log = executor.execute_in_sandbox(ws, t_spec["target_file"], code, t_spec["test"])
            print(f"  {cond} seed {seed}: passed={p}")
            runs_data.append({
                "condition": cond,
                "seed": seed,
                "passed": p,
                "generated_code": code,
                "sandbox_log": log[-500:]
            })
            if p:
                passes += 1
        tsr = round(passes / 3, 2)
        results[cond] = tsr
        print(f"Condition {cond} TSR: {passes}/3 ({tsr})")

    lift = round(results["S2"] - results["S0"], 2)
    print(f"\nResult: S0={results['S0']}, S2={results['S2']} -> Memory Lift = {lift:+.2f}")
    assert lift >= 0.67, f"Memory lift {lift} < 0.67 requirement!"
    print("QUALIFIED TRACK B POSITIVE SEED: PASS (Lift >= 0.67)")
    return {
        "tid": t_spec["tid"],
        "target_file": t_spec["target_file"],
        "task": t_spec["task"],
        "memory": t_spec["memory"],
        "tsr_s0": results["S0"],
        "tsr_s2": results["S2"],
        "lift": lift,
        "qualified": bool(lift >= 0.67),
        "runs": runs_data
    }

res1 = evaluate_track_b(task1)
res2 = evaluate_track_b(task2)

os.makedirs("/code/rolemem-agent-memory/data", exist_ok=True)
with open("/code/rolemem-agent-memory/data/track_b_evaluation.json", "w") as f:
    json.dump({"seeds": [res1, res2]}, f, indent=2)
print("Saved Track B evaluation to data/track_b_evaluation.json")
