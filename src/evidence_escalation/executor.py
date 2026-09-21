"""
src/evidence_escalation/executor.py

Targeted Worktree Executor for Protocol V2.2-V1 Evidence Escalation:
- Creates an ephemeral, isolated git worktree at the exact target commit.
- Executes targeted test candidates with strict timeout and environment isolation.
- Captures execution hashes, runtime provenance, and maps outcomes (PASS, FAIL, ERROR, TIMEOUT, UNAVAILABLE) to AcquiredEvidence.
- Enforces scientific invariant: ERROR / TIMEOUT / UNAVAILABLE are never interpreted as staleness.
"""

from __future__ import annotations
import os
import sys
import time
import shutil
import tempfile
import hashlib
import subprocess
from typing import Dict, Any, List, Optional, Tuple

from .types import (
    EvidenceActionType,
    BindingStrength,
    ExecutionStatus,
    AcquiredEvidence,
    TestCandidate,
    CostBudget
)
from .cost import CostTracker


class TargetedWorktreeExecutor:
    """Executes targeted test candidates in isolated git worktrees."""

    def __init__(self, base_worktree_dir: Optional[str] = None):
        self.base_worktree_dir = base_worktree_dir or "/tmp/rolemem_v1_worktrees"
        os.makedirs(self.base_worktree_dir, exist_ok=True)

    def _create_worktree(self, repo_root: str, target_commit: str) -> str:
        """Creates a temporary isolated git worktree checked out to target_commit."""
        worktree_path = tempfile.mkdtemp(prefix="wt_", dir=self.base_worktree_dir)
        # Force remove empty dir created by mkdtemp so git worktree add can initialize it
        os.rmdir(worktree_path)

        res = subprocess.run(
            ["git", "worktree", "add", "--detach", worktree_path, target_commit],
            cwd=repo_root,
            capture_output=True,
            text=True
        )
        if res.returncode != 0:
            raise RuntimeError(f"Failed to create git worktree: {res.stderr}")

        return worktree_path

    def _cleanup_worktree(self, repo_root: str, worktree_path: str):
        """Removes the temporary worktree and prunes git worktree metadata."""
        try:
            subprocess.run(
                ["git", "worktree", "remove", "--force", worktree_path],
                cwd=repo_root,
                capture_output=True,
                text=True
            )
        except Exception:
            pass
        if os.path.exists(worktree_path):
            try:
                shutil.rmtree(worktree_path, ignore_errors=True)
            except Exception:
                pass
        try:
            subprocess.run(["git", "worktree", "prune"], cwd=repo_root, capture_output=True, text=True)
        except Exception:
            pass

    def run_test_candidate(
        self,
        claim_id: str,
        repo_root: str,
        repository_name: str,
        candidate: TestCandidate,
        cost_tracker: Optional[CostTracker] = None,
        budget: Optional[CostBudget] = None
    ) -> AcquiredEvidence:
        """
        Executes candidate test within an isolated worktree checked out to candidate.target_commit.
        Returns AcquiredEvidence capturing test result and provenance.
        """
        if cost_tracker:
            cost_tracker.add_action(EvidenceActionType.TARGETED_EXECUTION)

        timeout_sec = budget.execution_timeout_sec if budget else 15
        target_commit = candidate.target_commit
        test_file = candidate.test_file
        test_name = candidate.test_name

        worktree_path = ""
        t_start = time.time()
        exec_status = ExecutionStatus.ERROR
        stdout_text = ""
        stderr_text = ""
        cmd_used = []

        try:
            worktree_path = self._create_worktree(repo_root, target_commit)
            target_test_full_path = os.path.join(worktree_path, test_file)

            if not os.path.exists(target_test_full_path):
                exec_status = ExecutionStatus.UNAVAILABLE
                stderr_text = f"Test file {test_file} not found in target commit."
            else:
                # Command construction: run pytest targeting specific file and test
                cmd_used = [
                    sys.executable,
                    "-m", "pytest",
                    f"{test_file}::{test_name}",
                    "-q",
                    "--tb=short"
                ]

                # Run in isolated worktree with pythonpath pointing to worktree
                env = os.environ.copy()
                env["PYTHONPATH"] = f"{worktree_path}:{env.get('PYTHONPATH', '')}"

                res = subprocess.run(
                    cmd_used,
                    cwd=worktree_path,
                    capture_output=True,
                    text=True,
                    timeout=timeout_sec,
                    env=env
                )
                stdout_text = res.stdout
                stderr_text = res.stderr

                if res.returncode == 0:
                    exec_status = ExecutionStatus.PASS
                elif "AssertionError" in stdout_text or "AssertionError" in stderr_text or "FAILED" in stdout_text:
                    exec_status = ExecutionStatus.FAIL
                elif "ImportError" in stdout_text or "ModuleNotFoundError" in stdout_text or "ImportError" in stderr_text or "ModuleNotFoundError" in stderr_text:
                    exec_status = ExecutionStatus.UNAVAILABLE
                else:
                    # Non-assertion failure (e.g. syntax error or env incompatibility)
                    exec_status = ExecutionStatus.ERROR

        except subprocess.TimeoutExpired:
            exec_status = ExecutionStatus.TIMEOUT
            stderr_text = f"Execution timed out after {timeout_sec}s."
        except Exception as ex:
            exec_status = ExecutionStatus.ERROR
            stderr_text = f"Execution error: {str(ex)}"
        finally:
            if worktree_path:
                self._cleanup_worktree(repo_root, worktree_path)

        t_elapsed_ms = (time.time() - t_start) * 1000.0
        if cost_tracker:
            cost_tracker.add_execution(t_elapsed_ms)

        stdout_hash = hashlib.sha256(stdout_text.encode("utf-8")).hexdigest()
        stderr_hash = hashlib.sha256(stderr_text.encode("utf-8")).hexdigest()
        cmd_str = " ".join(cmd_used) if cmd_used else f"pytest {test_file}::{test_name}"
        cmd_hash = hashlib.sha256(cmd_str.encode("utf-8")).hexdigest()

        # Map execution status to support/contradict/inconclusive
        if exec_status == ExecutionStatus.PASS:
            supports_or_contradicts = "SUPPORTS"
            conf = 0.95 if candidate.binding_strength == BindingStrength.STRONG else 0.70
            detail = f"Native test '{test_file}::{test_name}' passed under target commit {target_commit[:8]}."
        elif exec_status == ExecutionStatus.FAIL:
            supports_or_contradicts = "CONTRADICTS"
            conf = 0.95 if candidate.binding_strength == BindingStrength.STRONG else 0.70
            detail = f"Native test '{test_file}::{test_name}' failed under target commit {target_commit[:8]} with assertion failure."
        else:
            supports_or_contradicts = "INCONCLUSIVE"
            conf = 0.0
            detail = f"Native test execution resulted in {exec_status.value} (not interpreted as staleness)."

        ev_id = f"EV-EXEC-{hashlib.sha256(f'{claim_id}:{test_file}:{test_name}:{target_commit}'.encode()).hexdigest()[:8]}"

        return AcquiredEvidence(
            evidence_id=ev_id,
            claim_id=claim_id,
            action_type=EvidenceActionType.TARGETED_EXECUTION,
            source_type="NATIVE_TEST_EXECUTION",
            repository=repository_name,
            commit=target_commit,
            file_path=test_file,
            content_hash=stdout_hash,
            binding_strength=candidate.binding_strength,
            supports_or_contradicts=supports_or_contradicts,
            confidence=conf,
            cost={
                "execution_time_ms": round(t_elapsed_ms, 2),
                "timeout_sec": timeout_sec
            },
            detail=detail,
            extra_metadata={
                "test_name": test_name,
                "execution_status": exec_status.value,
                "command_hash": cmd_hash,
                "stdout_hash": stdout_hash,
                "stderr_hash": stderr_hash,
                "environment_provenance": "CURRENT_RUNTIME_WITH_HISTORICAL_SOURCE",
                "python_version": sys.version.split()[0]
            }
        )
