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


def _load_deepseek_api_client() -> Tuple[OpenAI, str]:
    auth_file = "/root/.local/share/opencode/auth.json"
    if os.path.exists(auth_file):
        try:
            with open(auth_file, "r") as f:
                data = json.load(f)
                key = data.get("deepseek", {}).get("key") or data.get("deepseek", {}).get("apiKey")
                if key:
                    return OpenAI(api_key=key, base_url="https://api.deepseek.com"), "deepseek-chat"
        except Exception:
            pass

    key = os.getenv("DEEPSEEK_API_KEY", "")
    return OpenAI(api_key=key, base_url="https://api.deepseek.com"), "deepseek-chat"



class SandboxEvaluatorV1:
    """Executes generated code in an isolated directory with domain-specific pytest suites."""

    @staticmethod
    def evaluate_in_sandbox(
        workspace_files: Dict[str, str],
        target_file: str,
        generated_code: str,
        test_code: str
    ) -> Tuple[bool, str]:
        with tempfile.TemporaryDirectory() as tmpdir:
            # 1. Write workspace files
            for rel_path, content in workspace_files.items():
                full_path = os.path.join(tmpdir, rel_path)
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                with open(full_path, "w", encoding="utf-8") as f:
                    f.write(content)

            # 2. Write generated target file
            target_full_path = os.path.join(tmpdir, target_file)
            os.makedirs(os.path.dirname(target_full_path), exist_ok=True)
            with open(target_full_path, "w", encoding="utf-8") as f:
                f.write(generated_code)

            # 3. Create __init__.py files in all directories to enable importing
            for root, dirs, _ in os.walk(tmpdir):
                init_file = os.path.join(root, "__init__.py")
                if not os.path.exists(init_file):
                    with open(init_file, "w") as f:
                        f.write("")

            # 4. Write test file
            test_path = os.path.join(tmpdir, "test_hidden_verification.py")
            with open(test_path, "w", encoding="utf-8") as f:
                f.write(test_code)

            # 5. Run pytest in isolated sandbox
            env = os.environ.copy()
            env["PYTHONPATH"] = tmpdir
            try:
                res = subprocess.run(
                    ["pytest", "test_hidden_verification.py", "-v"],
                    cwd=tmpdir,
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=15
                )
                passed = (res.returncode == 0)
                output = res.stdout if passed else f"STDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"
                return passed, output
            except subprocess.TimeoutExpired:
                return False, "TIMEOUT: Pytest execution exceeded 15s limit."
            except Exception as e:
                return False, f"EXECUTION_ERROR: {str(e)}"


class RealLLMRunnerV1:
    """Invokes LLM with strict fair information budgeting and records full evaluation telemetry."""

    def __init__(self):
        self.client, self.model_name = _load_deepseek_api_client()
        self.evaluator = SandboxEvaluatorV1()

    def _extract_code(self, response_text: str) -> str:
        """Extract clean python code block from LLM markdown response."""
        pattern = r"```python\s*(.*?)\s*```"
        matches = re.findall(pattern, response_text, re.DOTALL)
        if matches:
            # Return the longest python code block
            return max(matches, key=len).strip()
        
        # If backticks without python
        pattern_generic = r"```\s*(.*?)\s*```"
        generic_matches = re.findall(pattern_generic, response_text, re.DOTALL)
        if generic_matches:
            return max(generic_matches, key=len).strip()
        
        return response_text.strip()

    def _check_stale_patterns(self, code: str, patterns: list) -> bool:
        """Check if generated code actively utilizes deprecated/stale symbols."""
        code_lines = [l for l in code.split("\n") if not l.strip().startswith("#")]
        clean_code = "\n".join(code_lines)
        for pat in patterns:
            try:
                if re.search(pat, clean_code):
                    return True
            except Exception:
                pass
            if pat in clean_code:
                return True
        return False


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
                "error": f"API_CALL_ERROR: {str(e)}",
                "latency": latency,
                "tokens": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                "generated_code": "",
                "raw_output": ""
            }

        generated_code = self._extract_code(raw_output)
        stale_used = self._check_stale_patterns(generated_code, task.stale_patterns)

        # Run in isolated sandbox
        passed, test_log = self.evaluator.evaluate_in_sandbox(
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
            "stale_used": stale_used,
            "latency": latency,
            "tokens": tokens,
            "generated_code": generated_code,
            "test_log": test_log
        }
