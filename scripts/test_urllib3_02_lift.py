import os
import sys
import json
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

sys.path.insert(0, "/code/rolemem-agent-memory")
from src.sandbox_secure import SecureSandboxExecutor

MODEL_DIR = "/code/rolemem-agent-memory/models/qwen2.5-coder-7b"
spec_p = "/code/rolemem-agent-memory/data/specs/trans_gold_urllib3_02_empty_allowed_methods.json"
with open(spec_p) as f:
    spec = json.load(f)

tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR, trust_remote_code=True)
model = AutoModelForCausalLM.from_pretrained(MODEL_DIR, torch_dtype=torch.float16, device_map="auto")
model.eval()

after_dir = "/code/rolemem-agent-memory/fixtures_v2/trans_gold_urllib3_02_empty_allowed_methods/after"
ws = {}
for r, _, fns in os.walk(after_dir):
    for fn in fns:
        ap = os.path.join(r, fn)
        ws[os.path.relpath(ap, after_dir)] = open(ap).read()

with open("/code/rolemem-agent-memory/fixtures_v2/trans_gold_urllib3_02_empty_allowed_methods/hidden_tests/test_evaluation.py") as f:
    test_code = f.read()

venv_bin = "/code/rolemem-agent-memory/.venvs/trans_gold_urllib3_02_empty_allowed_methods/bin"
executor = SecureSandboxExecutor(custom_env_bin_dir=venv_bin)

for cond, mem in [("S0", ""), ("S2", "[PROJECT MEMORY CONTEXT]\n- " + spec["valid_memory_candidate"])]:
    passes = 0
    for seed in [42, 123, 999]:
        torch.manual_seed(seed)
        prompt = f"""You are an expert engineer working on {spec['repo_name']}.

{mem}

[TASK]
{spec['current_task']}

Write the complete Python code for {spec['target_file']}. Output only executable Python enclosed in ```python ```.
"""
        msgs = [{"role": "user", "content": prompt}]
        chat_text = tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
        inputs = tokenizer(chat_text, return_tensors="pt").to("cuda")
        with torch.no_grad():
            outs = model.generate(**inputs, max_new_tokens=200, do_sample=True, temperature=0.2)
        gen = tokenizer.decode(outs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True)
        if "```python" in gen:
            code = gen.split("```python")[1].split("```")[0].strip()
        elif "```" in gen:
            code = gen.split("```")[1].split("```")[0].strip()
        else:
            code = gen.strip()
        passed, log = executor.execute_in_sandbox(ws, spec["target_file"], code, test_code)
        print(f"{cond} seed {seed}: passed={passed}")
        if not passed:
            print("  Generated code:\n", code)
            print("  Pytest log:\n", log[:400])
        if passed:
            passes += 1
    print(f"Condition {cond} TSR: {passes}/3 ({round(passes/3, 2)})\n")
