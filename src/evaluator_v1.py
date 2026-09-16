"""
Evaluator v1: Scientific Evaluation Engine for Dynamic Cross-Model Task Handoffs.
Executes genuine LLM inference, isolated sandbox pytest suites, AST stale-pattern detection,
and full telemetry logging without category-level proxy shortcuts.
"""

import os
import re
import json
import time
import tempfile
import subprocess
from typing import Dict, Any, Tuple, Optional
from openai import OpenAI
from src.schema_v1 import TaskEnvironmentV1
from src.sandbox_secure import SecureSandboxExecutor
from src.stale_detector_ast import ASTStaleActionDetector


def _load_deepseek_api_client() -> Tuple[OpenAI, str]:
    model_override = os.getenv("DEEPSEEK_MODEL", "")
    auth_file = "/root/.local/share/opencode/auth.json"
    key = ""
    if os.path.exists(auth_file):
        try:
            with open(auth_file, "r") as f:
                data = json.load(f)
                key = data.get("deepseek", {}).get("key") or data.get("deepseek", {}).get("apiKey") or ""
        except Exception:
            pass

    if not key:
        key = os.getenv("DEEPSEEK_API_KEY", "")

    client = OpenAI(api_key=key, base_url="https://api.deepseek.com")
    # Default to verified endpoint deepseek-flash corresponding to DeepSeek-V4.1-Flash
    selected_model = model_override or "deepseek-flash"
    return client, selected_model


class SandboxEvaluatorV1:
    """
    Deprecated legacy evaluator. Replaced by SecureSandboxExecutor in Pilot-v1.2.
    Redirects calls to SecureSandboxExecutor to ensure bubblewrap containment.
    """

    def __init__(self):
        self.executor = SecureSandboxExecutor()

    def evaluate_in_sandbox(
        self,
        workspace_files: Dict[str, str],
        target_file: str,
        generated_code: str,
        test_code: str
    ) -> Tuple[bool, str]:
        return self.executor.execute_in_sandbox(
            workspace_files=workspace_files,
            target_file=target_file,
            generated_code=generated_code,
            test_code=test_code
        )


class RealLLMRunnerV1:
    """
    Invokes LLM with strict fair information budgeting and records full evaluation telemetry.
    All executions are strictly contained within SecureSandboxExecutor (bwrap).
    All stale metrics are computed via ASTStaleActionDetector.
    """

    def __init__(self, model_name: Optional[str] = None):
        client, default_model = _load_deepseek_api_client()
        self.client = client
        self.model_name = model_name or default_model
        self.evaluator = SecureSandboxExecutor()

    def _extract_code(self, response_text: str) -> str:
        """Extract clean python code block from LLM markdown response."""
        pattern = r"```python\s*(.*?)\s*```"
        matches = re.findall(pattern, response_text, re.DOTALL)
        if matches:
            return max(matches, key=len).strip()
        
        pattern_generic = r"```\s*(.*?)\s*```"
        generic_matches = re.findall(pattern_generic, response_text, re.DOTALL)
        if generic_matches:
            return max(generic_matches, key=len).strip()
        
        return response_text.strip()

    def evaluate_task(
        self,
        task: TaskEnvironmentV1,
        method_name: str,
        memory_block: str,
        role: str = "coder"
    ) -> Dict[str, Any]:
        """
        Evaluate single task under fair information budget.
        All methods receive identical workspace, current task instruction, and role prompt.
        """
        current_workspace = task.get_current_workspace()
        
        # Format workspace view
        ws_view_lines = ["### Current Repository Files:"]
        if not current_workspace:
            ws_view_lines.append("(Repository root is empty)")
        for path, content in current_workspace.items():
            ws_view_lines.append(f"\n--- File: {path} ---")
            ws_view_lines.append(content)
        workspace_view = "\n".join(ws_view_lines)

        # Assemble prompt
        prompt_sections = [
            f"You are a specialized {role.upper()} agent in a software development workflow.",
            "You must write complete, production-ready Python code to satisfy the task.",
            "\n" + workspace_view,
        ]

        if memory_block:
            prompt_sections.append("\n" + memory_block)

        prompt_sections.append(f"\n### Task Instruction:\n{task.current_task_instruction}")
        prompt_sections.append(
            f"\nWrite the complete implementation for `{task.target_file}`. "
            f"Enclose your implementation in a single ```python ... ``` code block."
        )

        full_prompt = "\n\n".join(prompt_sections)

        start_time = time.time()
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": f"You are an expert Python {role} agent. Generate strictly compliant code."},
                    {"role": "user", "content": full_prompt}
                ],
                temperature=0.0,
                max_tokens=1500
            )
            latency = time.time() - start_time
            raw_output = response.choices[0].message.content or ""
            tokens = {
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                "total_tokens": response.usage.total_tokens if response.usage else 0
            }
        except Exception as e:
            latency = time.time() - start_time
            return {
                "task_id": task.task_id,
                "method": method_name,
                "passed": False,
                "stale_used": False,
                "stale_active_use": False,
                "stale_mentions": False,
                "active_stale_nodes": [],
                "error": f"API_CALL_ERROR: {str(e)}",
                "latency": latency,
                "tokens": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                "generated_code": "",
                "raw_output": "",
                "test_log": "",
                "model_name": self.model_name
            }

        generated_code = self._extract_code(raw_output)

        # Scientific AST Stale Action Analysis (replaces regex heuristics)
        stale_analysis = ASTStaleActionDetector.analyze(generated_code, task.stale_patterns)

        # Run in kernel-isolated secure sandbox (Bubblewrap bwrap)
        passed, test_log = self.evaluator.execute_in_sandbox(
            workspace_files=current_workspace,
            target_file=task.target_file,
            generated_code=generated_code,
            test_code=task.hidden_test_code
        )

        return {
            "task_id": task.task_id,
            "task_family": task.task_family,
            "category": task.category,
            "method": method_name,
            "passed": passed,
            "stale_used": stale_analysis.stale_active_use,
            "stale_active_use": stale_analysis.stale_active_use,
            "stale_mentions": stale_analysis.stale_mentions,
            "active_stale_nodes": stale_analysis.active_stale_nodes,
            "latency": latency,
            "tokens": tokens,
            "generated_code": generated_code,
            "raw_output": raw_output,
            "test_log": test_log,
            "model_name": self.model_name
        }
