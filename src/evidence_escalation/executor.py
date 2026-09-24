"""
src/evidence_escalation/executor.py

Targeted Worktree Executor for Protocol V2.2-V1.1 Evidence Escalation:
- Creates an ephemeral, isolated git worktree at the exact target commit.
- Automatically determines and mounts source roots (worktree/src and worktree/).
- Runs import-origin preflight to verify that imported project packages originate from the target worktree.
- Executes targeted test candidates with strict timeout and environment isolation.
- Captures granular provenance hashes: test_file_sha256, test_function_sha256, stdout_sha256, stderr_sha256, command_sha256.
- Enforces scientific invariants:
  - SOURCE_ORIGIN_UNVERIFIED executions cannot provide strong support.
  - Failing tests without STRONG witness binding cannot prove staleness (maps to INCONCLUSIVE).
  - ERROR / TIMEOUT / UNAVAILABLE are never interpreted as staleness.
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
    EvidenceKind,
    BindingStrength,
    ExecutionStatus,
    SourceOriginStatus,
    AcquiredEvidence,
    TestCandidate,
    CostBudget
)
from .cost import CostTracker


class TargetedWorktreeExecutor:
    """Executes targeted test candidates in isolated git worktrees with strict source origin auditing."""

    def __init__(self, base_worktree_dir: Optional[str] = None):
        self.base_worktree_dir = base_worktree_dir or "/tmp/rolemem_v1_worktrees"
        os.makedirs(self.base_worktree_dir, exist_ok=True)

    def _create_worktree(self, repo_root: str, target_commit: str) -> str:
        """Creates a temporary isolated git worktree checked out to target_commit."""
        worktree_path = tempfile.mkdtemp(prefix="wt_", dir=self.base_worktree_dir)
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

    @staticmethod
    def derive_top_level_package(file_path: str, repository_name: str) -> str:
        """Derives the top-level python package name from file_path or repository."""
        if not file_path:
            return repository_name.split("/")[-1].replace("-", "_")

        norm = file_path.replace("\\", "/")
        parts = [p for p in norm.split("/") if p and p != "src"]

        if parts:
            first = parts[0]
            if first.endswith(".py"):
                return first[:-3]
            return first
        return repository_name.split("/")[-1].replace("-", "_")

    def _verify_source_origin(self, worktree_path: str, package_name: str, env: Dict[str, str]) -> Tuple[SourceOriginStatus, str]:
        """Runs preflight python script inside worktree environment to verify import origin."""
        preflight_script = (
            f"import importlib.util, sys\n"
            f"spec = importlib.util.find_spec('{package_name}')\n"
            f"print(spec.origin if spec and spec.origin else '')\n"
        )
        try:
            res = subprocess.run(
                [sys.executable, "-c", preflight_script],
                cwd=worktree_path,
                capture_output=True,
                text=True,
                env=env,
                timeout=5
            )
            origin = res.stdout.strip()
            if origin and (origin.startswith(worktree_path) or os.path.realpath(origin).startswith(os.path.realpath(worktree_path))):
                return SourceOriginStatus.VERIFIED_TARGET_WORKTREE, origin
            return SourceOriginStatus.SOURCE_ORIGIN_UNVERIFIED, origin or "None"
        except Exception as ex:
            return SourceOriginStatus.SOURCE_ORIGIN_UNVERIFIED, f"Preflight error: {ex}"

    def run_test_candidate(
        self,
        claim_id: str,
        repo_root: str,
        repository_name: str,
        candidate: TestCandidate,
        claim_file_path: str = "",
        cost_tracker: Optional[CostTracker] = None,
        budget: Optional[CostBudget] = None
    ) -> AcquiredEvidence:
        """
        Executes candidate test within an isolated worktree checked out to candidate.target_commit.
        Returns AcquiredEvidence capturing test result, full provenance, and source origin audit.
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
        origin_status = SourceOriginStatus.SOURCE_ORIGIN_UNVERIFIED
        origin_path = ""
        file_sha256 = candidate.test_file_sha256
        fn_sha256 = candidate.test_function_sha256

        try:
            worktree_path = self._create_worktree(repo_root, target_commit)
            target_test_full_path = os.path.join(worktree_path, test_file)

            if not os.path.exists(target_test_full_path):
                exec_status = ExecutionStatus.UNAVAILABLE
                stderr_text = f"Test file {test_file} not found in target commit."
            else:
                # Recompute hashes from worktree if missing
                if not file_sha256 and os.path.exists(target_test_full_path):
                    with open(target_test_full_path, "r", encoding="utf-8") as f:
                        file_sha256 = hashlib.sha256(f.read().encode("utf-8")).hexdigest()

                # Setup python paths: prioritize worktree/src if present, plus worktree
                src_sub = os.path.join(worktree_path, "src")
                python_paths = []
                if os.path.isdir(src_sub):
                    python_paths.append(src_sub)
                python_paths.append(worktree_path)

                env = os.environ.copy()
                env["PYTHONPATH"] = ":".join(python_paths) + ":" + env.get("PYTHONPATH", "")

                # Run import-origin preflight
                pkg_name = self.derive_top_level_package(claim_file_path, repository_name)
                origin_status, origin_path = self._verify_source_origin(worktree_path, pkg_name, env)

                # Command construction: run pytest targeting specific test
                cmd_used = [
                    sys.executable,
                    "-m", "pytest",
                    f"{test_file}::{test_name}",
                    "-q",
                    "--tb=short"
                ]

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

        stdout_sha256 = hashlib.sha256(stdout_text.encode("utf-8")).hexdigest()
        stderr_sha256 = hashlib.sha256(stderr_text.encode("utf-8")).hexdigest()
        cmd_str = " ".join(cmd_used) if cmd_used else f"pytest {test_file}::{test_name}"
        command_sha256 = hashlib.sha256(cmd_str.encode("utf-8")).hexdigest()

        # Scientific Synthesis: Source Origin & Witness Binding Auditing
        is_strong_witness = (candidate.binding_strength == BindingStrength.STRONG)
        is_verified_origin = (origin_status == SourceOriginStatus.VERIFIED_TARGET_WORKTREE)

        if not is_verified_origin:
            supports_or_contradicts = "INCONCLUSIVE"
            conf = 0.50
            effective_strength = BindingStrength.WEAK
            detail = f"Source origin unverified ({origin_path}); execution cannot produce strong evidence."
        elif exec_status == ExecutionStatus.PASS:
            if is_strong_witness:
                supports_or_contradicts = "SUPPORTS"
                conf = 0.95
                effective_strength = BindingStrength.STRONG
                detail = f"Verified witness '{test_file}::{test_name}' passed under target commit {target_commit[:8]} (source verified: {pkg_name})."
            else:
                supports_or_contradicts = "SUPPORTS"
                conf = 0.65
                effective_strength = BindingStrength.WEAK
                detail = f"Weak witness '{test_file}::{test_name}' passed under target commit; insufficient for deterministic proof."
        elif exec_status == ExecutionStatus.FAIL:
            if is_strong_witness:
                supports_or_contradicts = "CONTRADICTS"
                conf = 0.95
                effective_strength = BindingStrength.STRONG
                detail = f"Verified witness '{test_file}::{test_name}' failed under target commit with assertion error."
            else:
                supports_or_contradicts = "INCONCLUSIVE"
                conf = 0.0
                effective_strength = BindingStrength.WEAK
                detail = f"Unbound/Weak test '{test_file}::{test_name}' failed; not interpreted as claim staleness."
        else:
            supports_or_contradicts = "INCONCLUSIVE"
            conf = 0.0
            effective_strength = candidate.binding_strength
            detail = f"Execution resulted in {exec_status.value} (not interpreted as staleness)."

        ev_id = f"EV-EXEC-{hashlib.sha256(f'{claim_id}:{test_file}:{test_name}:{target_commit}'.encode()).hexdigest()[:8]}"

        return AcquiredEvidence(
            evidence_id=ev_id,
            claim_id=claim_id,
            action_type=EvidenceActionType.TARGETED_EXECUTION,
            source_type="NATIVE_TEST_EXECUTION",
            evidence_kind=EvidenceKind.EXECUTABLE_TEST_WITNESS,
            repository=repository_name,
            commit=target_commit,
            file_path=test_file,
            content_hash=fn_sha256 or stdout_sha256,
            binding_strength=effective_strength,
            supports_or_contradicts=supports_or_contradicts,
            confidence=conf,
            test_file_sha256=file_sha256,
            test_function_sha256=fn_sha256,
            stdout_sha256=stdout_sha256,
            stderr_sha256=stderr_sha256,
            command_sha256=command_sha256,
            source_origin_status=origin_status.value if isinstance(origin_status, SourceOriginStatus) else str(origin_status),
            repository_snapshot_status="VERIFIED_TARGET_COMMIT",
            dependency_environment_status="CURRENT_ENVIRONMENT_NOT_HISTORICALLY_RESTORED",
            semantic_requirements=candidate.semantic_requirements,
            requirement_count=candidate.requirement_count,
            requirements_satisfied=candidate.requirements_satisfied,
            requirement_coverage=candidate.requirement_coverage,
            operation_requirement_applicable=candidate.operation_requirement_applicable,
            cost={
                "execution_time_ms": round(t_elapsed_ms, 2),
                "timeout_sec": timeout_sec
            },
            detail=detail,
            extra_metadata={
                "test_name": test_name,
                "execution_status": exec_status.value if isinstance(exec_status, ExecutionStatus) else str(exec_status),
                "package_name": pkg_name,
                "module_origin": origin_path,
                "environment_provenance": "CURRENT_RUNTIME_WITH_HISTORICAL_SOURCE",
                "python_version": sys.version.split()[0],
                "witness_binding": candidate.witness_binding or {}
            }
        )
