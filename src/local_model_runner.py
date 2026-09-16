"""
Local Pinned Model Runner and Reproducibility Profiler for Gate 7.
Manages pinned local models (Qwen2.5-Coder) and records exact hardware,
environment, and revision parameters alongside external API specs.
"""

import os
import sys
import time
import json
from typing import Dict, Any, Tuple
import torch

# Ensure project root in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.schema_v1 import TaskEnvironmentV1
from src.evaluator_v1 import SandboxEvaluatorV1
from src.smoke_tasks_v1 import get_smoke_tasks_v1


class LocalModelRunner:
    """Runs inference using a pinned local weights checkpoint on GPU."""

    def __init__(self, model_dir: str = "models/qwen2.5-coder-0.5b", model_repo: str = "Qwen/Qwen2.5-Coder-0.5B-Instruct"):
        self.model_repo = model_repo
        self.model_dir = model_dir
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.dtype = torch.float16 if self.device == "cuda" else torch.float32

        # Record environment specs
        self.env_specs = {
            "model_repo": self.model_repo,
            "revision": "main",
            "device": self.device,
            "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "None",
            "vram_allocated_gb": torch.cuda.get_device_properties(0).total_memory / (1024**3) if torch.cuda.is_available() else 0,
            "torch_version": torch.__version__,
            "cuda_version": torch.version.cuda if torch.cuda.is_available() else "None",
            "dtype": str(self.dtype),
            "generation_config": {
                "temperature": 0.0,
                "max_new_tokens": 1024,
                "do_sample": False
            }
        }
        self.model = None
        self.tokenizer = None
        self.evaluator = SandboxEvaluatorV1()

    def load_model(self) -> None:
        from transformers import AutoModelForCausalLM, AutoTokenizer
        target_path = self.model_dir if os.path.exists(os.path.join(self.model_dir, "model.safetensors")) else self.model_repo
        print(f"Loading tokenizer from {target_path}...")
        self.tokenizer = AutoTokenizer.from_pretrained(target_path, trust_remote_code=True)
        print(f"Loading model weights from {target_path} onto {self.device}...")
        self.model = AutoModelForCausalLM.from_pretrained(
            target_path,
            torch_dtype=self.dtype,
            device_map="auto" if self.device == "cuda" else None,
            trust_remote_code=True
        )
        print("Model loaded successfully!")

    def generate(self, prompt: str) -> Tuple[str, float, Dict[str, int]]:
        if self.model is None or self.tokenizer is None:
            self.load_model()

        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.device)
        prompt_tokens = inputs.input_ids.shape[1]

        start_time = time.time()
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=1024,
                do_sample=False,
                pad_token_id=self.tokenizer.eos_token_id
            )
        latency = time.time() - start_time

        new_tokens = outputs[0][prompt_tokens:]
        completion_tokens = len(new_tokens)
        generated_text = self.tokenizer.decode(new_tokens, skip_special_tokens=True)

        token_stats = {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens
        }
        return generated_text, latency, token_stats

    def evaluate_task(self, task: TaskEnvironmentV1, role: str = "coder") -> Dict[str, Any]:
        current_workspace = task.get_current_workspace()
        ws_lines = ["### Current Repository Files:"]
        for p, c in current_workspace.items():
            ws_lines.append(f"\n--- {p} ---\n{c}")
        ws_view = "\n".join(ws_lines)

        prompt = (
            f"You are a Python {role.upper()} agent.\n\n"
            f"{ws_view}\n\n"
            f"### Task:\n{task.current_task_instruction}\n\n"
            f"Implement `{task.target_file}` inside a ```python ... ``` block."
        )

        gen_text, latency, token_stats = self.generate(prompt)
        # Extract code block
        import re
        matches = re.findall(r"```python\s*(.*?)\s*```", gen_text, re.DOTALL)
        code = matches[0].strip() if matches else gen_text.strip()

        passed, test_log = self.evaluator.evaluate_in_sandbox(
            workspace_files=current_workspace,
            target_file=task.target_file,
            generated_code=code,
            test_code=task.hidden_test_code
        )

        return {
            "task_id": task.task_id,
            "passed": passed,
            "latency": latency,
            "tokens": token_stats,
            "test_log": test_log[:300]
        }
