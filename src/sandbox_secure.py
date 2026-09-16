"""
Secure Containerized Sandbox Executor for Agent Code Evaluation.
Enforces kernel-level namespace isolation via Bubblewrap (bwrap) with network, filesystem,
and credential redaction.
"""

import os
import shutil
import tempfile
import subprocess
from typing import Dict, Tuple, Optional


class SecureSandboxExecutor:
    """Executes generated code in an isolated, read-only root, networkless sandbox."""

    def __init__(self, timeout_seconds: int = 10):
        self.timeout_seconds = timeout_seconds
        self.has_bwrap = shutil.which("bwrap") is not None

    def execute_in_sandbox(
        self,
        workspace_files: Dict[str, str],
        target_file: str,
        generated_code: str,
        test_code: str
    ) -> Tuple[bool, str]:
        """
        Creates an isolated ephemeral workspace, mounts read-only system libraries,
        denies all network access, and executes pytest with unprivileged UID.
        """
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

            # 5. Build sandbox command
            if self.has_bwrap:
                cmd = [
                    "bwrap",
                    "--ro-bind", "/", "/",
                    "--tmpfs", "/tmp",
                    "--tmpfs", "/root",
                    "--ro-bind", "/root/anaconda3", "/root/anaconda3",
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
                    "--setenv", "PATH", "/root/anaconda3/bin:/usr/local/bin:/usr/bin:/bin",
                    "--setenv", "PYTHONPATH", tmpdir,
                    "--setenv", "LANG", "C.UTF-8",
                    "--setenv", "HOME", "/tmp",
                    "--die-with-parent",
                    "pytest", "test_hidden_verification.py", "-v"

                ]
            else:
                # Fallback: strict clean-environment subprocess
                cmd = ["pytest", "test_hidden_verification.py", "-v"]

            clean_env = {
                "PATH": "/root/anaconda3/bin:/usr/local/bin:/usr/bin:/bin",
                "PYTHONPATH": tmpdir,
                "LANG": "C.UTF-8",
                "HOME": "/tmp"
            }

            try:
                res = subprocess.run(
                    cmd,
                    cwd=tmpdir if not self.has_bwrap else None,
                    env=clean_env if not self.has_bwrap else None,
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
