"""
Pilot-v1.2 End-to-End Integration Hardening Test.
Validates the complete evaluation pipeline:
Memory Retrieval -> Prompt Assembly -> LLM Generation -> Code Extraction ->
AST Stale Analysis -> Secure Sandbox (bwrap + prlimit) -> Hidden Pytest -> Telemetry Logging.
"""

import os
import json
import pytest
from src.schema_v1 import TaskEnvironmentV1, MemoryRecordV1
from src.budgeter import MemoryBudgeter
from src.rolemem_core_v1 import RoleMemStoreV1
from src.evaluator_v1 import RealLLMRunnerV1
from src.local_model_runner import LocalModelRunner
from src.sandbox_secure import SecureSandboxExecutor
from src.stale_detector_ast import ASTStaleActionDetector


def test_complete_end_to_end_pipeline_integration(monkeypatch, tmp_path):
    """
    Verifies that the complete evaluation loop operates strictly via:
    - SecureSandboxExecutor (bwrap with prlimit resource controls)
    - ASTStaleActionDetector (AST inspection, no regex shortcuts)
    - Zero host secrets leaked into sandbox
    - Comprehensive telemetry logging (raw output, tokens, latency, revision)
    """
    # 1. Setup sample task with historical memory and transition
    mem = MemoryRecordV1(
        memory_id="mem_auth_legacy",
        artifact_uri="src/auth/token.py",
        artifact_type="code",
        symbol="legacy_validate_token",
        source_commit="commit_base",
        observed_at=100.0,
        evidence_type="code_commit",
        evidence_ref="commit_base",
        valid_from=100.0,
        valid_to=200.0,
        status="ACTIVE",
        role_tags=["coder"],
        statement="Use legacy_validate_token(token) for auth."
    )

    task = TaskEnvironmentV1(
        task_id="integration_task_01",
        task_family="auth",
        category="explicit_update",
        title="Auth Token Validator",
        description="Implement modern auth validator.",
        initial_workspace={"src/auth/token.py": "def legacy_validate_token(t): return True"},
        historical_memories=[mem],
        workspace_transition={"src/auth/token.py": "def modern_validate_token(t): return len(t) > 5"},
        current_task_instruction="Implement `verify_credentials(token: str) -> bool` in `src/validator.py`.",
        target_file="src/validator.py",
        target_symbol="verify_credentials",
        hidden_test_code="""
import pytest
from src.validator import verify_credentials

def test_verify_credentials():
    assert verify_credentials("valid_token_123") is True
    assert verify_credentials("bad") is False
""",
        stale_patterns=["legacy_validate_token"]
    )

    # 2. Test Step: Memory Retrieval under budget
    budgeter = MemoryBudgeter(max_memory_tokens=512)
    memory_text, token_count = budgeter.format_and_budget(task.historical_memories)
    assert token_count <= 512

    # 3. Test Step: Mock LLM Generation simulating modern implementation with comment mention
    mock_llm_response = """
Here is the compliant implementation:
```python
# Note: legacy_validate_token is deprecated and superseded by modern_validate_token
from src.auth.token import modern_validate_token

def verify_credentials(token: str) -> bool:
    return modern_validate_token(token)
```
Hope this helps!
"""

    # Set mock host secrets to verify they NEVER enter the sandbox
    monkeypatch.setenv("DEEPSEEK_API_KEY", "secret_deepseek_key_12345")
    monkeypatch.setenv("GITHUB_TOKEN", "secret_gh_token_67890")

    runner = RealLLMRunnerV1()
    assert isinstance(runner.evaluator, SecureSandboxExecutor), "RealLLMRunnerV1 must use SecureSandboxExecutor!"

    # Mock client completion
    class MockChoice:
        def __init__(self, content):
            self.message = type("Msg", (), {"content": content})()
    class MockUsage:
        prompt_tokens = 120
        completion_tokens = 45
        total_tokens = 165
    class MockResponse:
        choices = [MockChoice(mock_llm_response)]
        usage = MockUsage()

    monkeypatch.setattr(runner.client.chat.completions, "create", lambda **kw: MockResponse())

    # 4. Execute evaluation loop
    result = runner.evaluate_task(
        task=task,
        method_name="RoleMemV1",
        memory_block=memory_text,
        role="coder"
    )

    # 5. Verify Metrics Logging
    assert result["task_id"] == "integration_task_01"
    assert result["method"] == "RoleMemV1"
    assert result["passed"] is True, f"Hidden pytest failed: {result.get('test_log')}"
    assert result["stale_active_use"] is False, "Docstring/comment mention was falsely flagged as active stale use!"
    assert result["stale_mentions"] is True, "Passive comment mention was not detected in telemetry!"
    assert result["active_stale_nodes"] == []
    assert result["latency"] > 0
    assert result["tokens"]["total_tokens"] == 165
    assert "def verify_credentials" in result["generated_code"]
    assert mock_llm_response in result["raw_output"]
    assert "test_verify_credentials PASSED" in result["test_log"]

    # 6. Verify Sandbox Isolation against host secrets
    secret_probe_code = """
import os
import pytest

def test_no_host_secrets():
    assert os.getenv("DEEPSEEK_API_KEY") is None, "Host DEEPSEEK_API_KEY leaked into sandbox!"
    assert os.getenv("GITHUB_TOKEN") is None, "Host GITHUB_TOKEN leaked into sandbox!"
"""
    passed_sec, out_sec = runner.evaluator.execute_in_sandbox(
        workspace_files={},
        target_file="src/probe.py",
        generated_code="x = 1",
        test_code=secret_probe_code
    )
    assert passed_sec is True, f"Sandbox credential leak detected: {out_sec}"


def test_stale_action_is_strictly_caught_by_ast(monkeypatch):
    """Verifies that if generated code actively invokes a stale symbol, AST detector catches it."""
    stale_code_response = """
```python
from src.auth.token import legacy_validate_token

def verify_credentials(token: str) -> bool:
    return legacy_validate_token(token)
```
"""
    runner = RealLLMRunnerV1()
    task = TaskEnvironmentV1(
        task_id="stale_probe_task",
        task_family="auth",
        category="stale_evidence",
        title="Stale Probe",
        description="Probe",
        initial_workspace={"src/auth/token.py": "def legacy_validate_token(t): return True"},
        historical_memories=[],
        workspace_transition={},
        current_task_instruction="Do auth",
        target_file="src/validator.py",
        target_symbol="verify_credentials",
        hidden_test_code="def test_dummy(): pass",
        stale_patterns=["legacy_validate_token"]
    )

    class MockChoice:
        message = type("Msg", (), {"content": stale_code_response})()
    class MockResponse:
        choices = [MockChoice()]
        usage = type("Usage", (), {"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20})()

    monkeypatch.setattr(runner.client.chat.completions, "create", lambda **kw: MockResponse())

    res = runner.evaluate_task(task, "TestRunner", "")
    assert res["stale_active_use"] is True
    assert len(res["active_stale_nodes"]) > 0
    assert res["active_stale_nodes"][0]["symbol"] == "legacy_validate_token"
