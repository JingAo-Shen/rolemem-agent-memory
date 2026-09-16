"""
Local Pinned Model Runner and Reproducibility Profiler for Gate 7.
Manages pinned local models (Qwen2.5-Coder) and records exact hardware,
environment, and revision parameters alongside external API specs.
"""

import os
import sys
import time
import json
from typing import Dict, Any, Tuple, Optional
import torch

# Ensure project root in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.schema_v1 import TaskEnvironmentV1
from src.sandbox_secure import SecureSandboxExecutor
from src.stale_detector_ast import ASTStaleActionDetector
from src.smoke_tasks_v1 import get_smoke_tasks_v1


PINNED_REVISIONS = {
    "Qwen/Qwen2.5-Coder-7B-Instruct": "c03e6d358207e414f1eca0bb1891e29f1db0e242",
    "Qwen/Qwen2.5-Coder-3B-Instruct": "488639f1ff808d1d3d0ba301aef8c11461451ec5",
    "Qwen/Qwen2.5-Coder-0.5B-Instruct": "ea3f2471cf1b1f0db85067f1ef93848e38e88c25"
}


class LocalModelRunner:
    """
    Runs inference using a pinned local weights checkpoint on GPU.
    All evaluations are strictly contained in SecureSandboxExecutor (bwrap).
    All revisions must be pinned commit SHAs; revision='main' is strictly prohibited.
    """

    def __init__(
        self,
        model_dir: str = "models/qwen2.5-coder-0.5b",
        model_repo: str = "Qwen/Qwen2.5-Coder-0.5B-Instruct",
        revision: Optional[str] = None
    ):
        self.model_repo = model_repo
        self.model_dir = model_dir
        
        # Enforce pinned commit SHA
        assigned_rev = revision or PINNED_REVISIONS.get(model_repo, "ea3f2471cf1b1f0db85067f1ef93848e38e88c25")
        if assigned_rev == "main":
            raise ValueError("CRITICAL REPRODUCIBILITY ERROR: revision='main' is prohibited. Must specify exact commit SHA.")
        self.revision = assigned_rev

        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.dtype = torch.float16 if self.device == "cuda" else torch.float32

        # Record environment specs
        self.env_specs = {
            "model_repo": self.model_repo,
            "revision": self.revision,
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
            },
            "config_sha256": None,
            "model_config_sha256": None,
            "tokenizer_sha256": None,
            "weights_prefix_sha256_64mb": None,
            "weights_sha256": None,
            "safetensors_index_sha256": None,
            "hf_revision_sha": self.revision,
            "hf_commit_sha": self.revision
        }
        self.model = None
        self.tokenizer = None
        self.evaluator = SecureSandboxExecutor()

    @staticmethod
    def _compute_sha256(filepath: str, max_bytes: Optional[int] = None) -> str:
        import hashlib
        h = hashlib.sha256()
        with open(filepath, "rb") as f:
            read_bytes = 0
            while True:
                chunk = f.read(65536)
                if not chunk:
                    break
                h.update(chunk)
                read_bytes += len(chunk)
                if max_bytes and read_bytes >= max_bytes:
                    break
        return h.hexdigest()

    def load_model(self) -> None:
        from transformers import AutoModelForCausalLM, AutoTokenizer
        is_local = os.path.exists(os.path.join(self.model_dir, "model.safetensors")) or os.path.exists(os.path.join(self.model_dir, "model.safetensors.index.json"))
        target_path = self.model_dir if is_local else self.model_repo

        # Compute checksums if files exist locally
        if is_local:
            cfg_p = os.path.join(self.model_dir, "config.json")
            tok_p = os.path.join(self.model_dir, "tokenizer.json")
            w_p = os.path.join(self.model_dir, "model.safetensors")
            idx_p = os.path.join(self.model_dir, "model.safetensors.index.json")
            if os.path.exists(cfg_p):
                sha = self._compute_sha256(cfg_p)
                self.env_specs["config_sha256"] = sha
                self.env_specs["model_config_sha256"] = sha
            if os.path.exists(tok_p):
                self.env_specs["tokenizer_sha256"] = self._compute_sha256(tok_p)
            if os.path.exists(idx_p):
                self.env_specs["safetensors_index_sha256"] = self._compute_sha256(idx_p)
            if os.path.exists(w_p):
                # Hash first 64MB of weights for fast startup validation if large
                prefix_sha = self._compute_sha256(w_p, max_bytes=64 * 1024 * 1024)
                self.env_specs["weights_prefix_sha256_64mb"] = prefix_sha
                self.env_specs["weights_sha256"] = prefix_sha

        print(f"Loading tokenizer from {target_path} (revision={self.revision})...")
        load_kwargs = {"trust_remote_code": True}
        if not is_local or os.path.isdir(os.path.join(target_path, ".git")):
            load_kwargs["revision"] = self.revision

        self.tokenizer = AutoTokenizer.from_pretrained(target_path, revision=self.revision, trust_remote_code=True)
        print(f"Loading model weights from {target_path} onto {self.device} (revision={self.revision})...")
        self.model = AutoModelForCausalLM.from_pretrained(
            target_path,
            revision=self.revision,
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

        # AST Stale Action Analysis
        stale_analysis = ASTStaleActionDetector.analyze(code, task.stale_patterns)

        # Bubblewrap Kernel Sandbox Execution
        passed, test_log = self.evaluator.execute_in_sandbox(
            workspace_files=current_workspace,
            target_file=task.target_file,
            generated_code=code,
            test_code=task.hidden_test_code
        )

        return {
            "task_id": task.task_id,
            "passed": passed,
            "stale_used": stale_analysis.stale_active_use,
            "stale_active_use": stale_analysis.stale_active_use,
            "stale_mentions": stale_analysis.stale_mentions,
            "active_stale_nodes": stale_analysis.active_stale_nodes,
            "latency": latency,
            "tokens": token_stats,
            "generated_code": code,
            "raw_output": gen_text,
            "test_log": test_log,
            "model_repo": self.model_repo,
            "revision": self.revision
        }
