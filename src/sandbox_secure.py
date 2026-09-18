"""
Secure Containerized Sandbox Executor for Agent Code Evaluation.
Enforces kernel-level namespace isolation via Bubblewrap (bwrap) with network, filesystem,
and credential redaction.
"""

import os
import shutil
import tempfile
import subprocess
from typing import Dict, Tuple, Optional, Any, List


class SecureSandboxExecutor:
    """
    Executes generated code in an isolated, read-only root, networkless sandbox.
    Enforces Bubblewrap kernel containment, resource limits, and environment redaction.
    """

    def __init__(
        self,
        timeout_seconds: int = 15,
        max_memory_bytes: int = 4 * 1024 * 1024 * 1024,  # 4 GB
        max_procs: int = 128,
        cpu_limit_seconds: int = 15,
        custom_env_bin_dir: Optional[str] = None
    ):
        self.timeout_seconds = timeout_seconds
        self.max_memory_bytes = max_memory_bytes
        self.max_procs = max_procs
        self.cpu_limit_seconds = cpu_limit_seconds
        self.custom_env_bin_dir = custom_env_bin_dir
        self.bwrap_path = shutil.which("bwrap")
        self.prlimit_path = shutil.which("prlimit")

        if not self.bwrap_path:
            raise RuntimeError(
                "CRITICAL SECURITY ERROR: /usr/bin/bwrap (Bubblewrap) executable is not found. "
                "Secure containerized sandbox isolation is mandatory for RoleMem evaluation. "
                "Fallback to uncontained execution is strictly prohibited."
            )

    def execute_in_sandbox(
        self,
        workspace_files: Dict[str, str],
        target_file: str,
        generated_code: str,
        test_code: str
    ) -> Tuple[bool, str]:
        """
        Creates an isolated ephemeral workspace, mounts read-only system libraries,
        denies all network access, applies resource limits, and executes pytest with unprivileged UID.
        """
        if not self.bwrap_path or not os.path.exists(self.bwrap_path):
            raise RuntimeError("HARD FAIL: bwrap executable is missing. Evaluation aborted.")

        with tempfile.TemporaryDirectory(prefix="rolemem_sandbox_") as tmpdir:
            # 1. Populate workspace files
            for rel_path, content in workspace_files.items():
                full_path = os.path.join(tmpdir, rel_path)
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                with open(full_path, "w", encoding="utf-8") as f:
                    f.write(content)

            # 2. Write target file
            target_path = os.path.join(tmpdir, target_file)
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            with open(target_path, "w", encoding="utf-8") as f:
                f.write(generated_code)

            # 3. Create __init__.py markers
            for root, dirs, _ in os.walk(tmpdir):
                init_p = os.path.join(root, "__init__.py")
                if not os.path.exists(init_p):
                    with open(init_p, "w") as f:
                        f.write("")

            # 4. Write test file
            test_file_path = os.path.join(tmpdir, "test_hidden_verification.py")
            with open(test_file_path, "w", encoding="utf-8") as f:
                f.write(test_code)

            # 5. Build sandbox command with bwrap
            path_env = "/root/anaconda3/bin:/usr/local/bin:/usr/bin:/bin"
            extra_mounts = []
            if self.custom_env_bin_dir and os.path.isdir(self.custom_env_bin_dir):
                path_env = f"{self.custom_env_bin_dir}:{path_env}"
                venv_root = os.path.dirname(os.path.abspath(self.custom_env_bin_dir))
                extra_mounts = ["--ro-bind", venv_root, venv_root]

            pythonpath = f"{tmpdir}:{os.path.join(tmpdir, 'src')}" if os.path.isdir(os.path.join(tmpdir, "src")) else tmpdir
            bwrap_cmd = [
                self.bwrap_path,
                "--ro-bind", "/", "/",
                "--tmpfs", "/tmp",
                "--tmpfs", "/root",
                "--ro-bind", "/root/anaconda3", "/root/anaconda3",
            ] + extra_mounts + [
                "--tmpfs", "/home",
                "--proc", "/proc",
                "--dev", "/dev",
                "--unshare-net",
                "--unshare-pid",
                "--unshare-user",
                "--uid", "1000",
                "--gid", "1000",
                "--bind", tmpdir, tmpdir,
                "--chdir", tmpdir,
                "--clearenv",
                "--setenv", "PATH", path_env,
                "--setenv", "PYTHONPATH", pythonpath,
                "--setenv", "LANG", "C.UTF-8",
                "--setenv", "HOME", "/tmp",
                "--die-with-parent",
                "pytest", "test_hidden_verification.py", "-v"
            ]

            # 6. Prepend prlimit resource limits if prlimit is available
            if self.prlimit_path:
                cmd = [
                    self.prlimit_path,
                    f"--as={self.max_memory_bytes}",
                    f"--nproc={self.max_procs}",
                    f"--cpu={self.cpu_limit_seconds}"
                ] + bwrap_cmd
            else:
                cmd = bwrap_cmd

            # Clean host environment passed to the runner subprocess
            clean_host_env = {
                "PATH": path_env,
                "HOME": "/tmp",
                "LANG": "C.UTF-8"
            }

            try:
                res = subprocess.run(
                    cmd,
                    env=clean_host_env,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout_seconds
                )
                passed = (res.returncode == 0)
                output = res.stdout if passed else f"STDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"
                return passed, output
            except subprocess.TimeoutExpired:
                return False, f"TIMEOUT: Execution exceeded {self.timeout_seconds}s limit."
            except Exception as e:
                return False, f"SANDBOX_ERROR: {str(e)}"

    def execute_in_sandbox_detailed(
        self,
        workspace_files: Dict[str, str],
        target_file: str,
        generated_code: str,
        test_code: str
    ) -> Dict[str, Any]:
        """Execute with detailed telemetry (stdout, stderr, exit_code)."""
        passed, log = self.execute_in_sandbox(
            workspace_files=workspace_files,
            target_file=target_file,
            generated_code=generated_code,
            test_code=test_code
        )
        # Parse stdout, stderr, exit_code
        stdout = log
        stderr = ""
        exit_code = 0 if passed else 1
        if "STDOUT:\n" in log and "\nSTDERR:\n" in log:
            parts = log.split("\nSTDERR:\n")
            stdout = parts[0].replace("STDOUT:\n", "")
            stderr = parts[1]
        elif "TIMEOUT:" in log:
            stderr = log
            exit_code = 124
        elif "SANDBOX_ERROR:" in log:
            stderr = log
            exit_code = 127

        return {
            "passed": passed,
            "stdout": stdout,
            "stderr": stderr,
            "exit_code": exit_code,
            "log": log
        }

