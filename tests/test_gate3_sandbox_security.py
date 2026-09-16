"""
Gate 3 Automated Tests: Security Sandbox Adversarial Penetration Tests.
Verifies that malicious payloads attempting network access, file leakage,
host environment inspection, and infinite loops are blocked.
"""

import pytest
from src.sandbox_secure import SecureSandboxExecutor


@pytest.fixture
def sandbox():
    return SecureSandboxExecutor(timeout_seconds=5)


def test_network_access_is_blocked(sandbox):
    """Malicious test attempting to establish outbound socket connection."""
    malicious_test = """
import socket
import pytest

def test_exfiltrate_data():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(2.0)
    # Attempt connecting to public DNS
    try:
        s.connect(('8.8.8.8', 53))
        assert False, "CRITICAL: Outbound network connection succeeded in sandbox!"
    except OSError as e:
        # Expected network blocked (e.g. Network is unreachable)
        pass
"""
    passed, output = sandbox.execute_in_sandbox(
        workspace_files={},
        target_file="src/dummy.py",
        generated_code="x = 1",
        test_code=malicious_test
    )
    # Pytest runs and passes because the exfiltration was caught and failed as expected
    assert passed is True, f"Sandbox failed to handle network test: {output}"


def test_host_secrets_are_not_exposed_in_env(sandbox):
    """Malicious test attempting to read API keys from environment."""
    malicious_test = """
import os
import pytest

def test_inspect_environment_secrets():
    assert os.getenv('DEEPSEEK_API_KEY') is None
    assert os.getenv('OPENAI_API_KEY') is None
    assert os.getenv('GITHUB_TOKEN') is None
"""
    passed, output = sandbox.execute_in_sandbox(
        workspace_files={},
        target_file="src/dummy.py",
        generated_code="x = 1",
        test_code=malicious_test
    )
    assert passed is True, f"Host environment variable was exposed inside sandbox: {output}"


def test_root_directory_files_are_hidden(sandbox):
    """Malicious test attempting to read /root or opencode auth.json."""
    malicious_test = """
import os
import pytest

def test_inspect_root_dir():
    assert not os.path.exists('/root/.local'), "/root/.local exists in sandbox!"
    assert not os.path.exists('/root/.ssh'), "/root/.ssh exists in sandbox!"
    files = [f for f in os.listdir('/root') if f != 'anaconda3']
    assert len(files) == 0, f"Found sensitive files in /root: {files}"
"""
    passed, output = sandbox.execute_in_sandbox(
        workspace_files={},
        target_file="src/dummy.py",
        generated_code="x = 1",
        test_code=malicious_test
    )
    assert passed is True, f"Sandbox leaked /root filesystem content: {output}"



def test_read_only_root_prevents_system_modification(sandbox):
    """Malicious test attempting to write outside workspace."""
    malicious_test = """
import pytest

def test_write_to_etc():
    with pytest.raises(OSError):
        with open('/etc/malicious_payload.txt', 'w') as f:
            f.write('hacked')
"""
    passed, output = sandbox.execute_in_sandbox(
        workspace_files={},
        target_file="src/dummy.py",
        generated_code="x = 1",
        test_code=malicious_test
    )
    assert passed is True, f"Sandbox permitted writing to root filesystem: {output}"


def test_infinite_loop_timeout(sandbox):
    """Malicious test with an infinite loop is killed within timeout."""
    malicious_test = """
def test_infinite_loop():
    while True:
        pass
"""
    passed, output = sandbox.execute_in_sandbox(
        workspace_files={},
        target_file="src/dummy.py",
        generated_code="x = 1",
        test_code=malicious_test
    )
    assert passed is False
    assert "TIMEOUT" in output


def test_missing_bwrap_hard_fails(monkeypatch):
    """If bwrap is missing, SecureSandboxExecutor must HARD FAIL, never fall back."""
    import shutil
    monkeypatch.setattr(shutil, "which", lambda cmd: None if cmd == "bwrap" else "/usr/bin/" + cmd)
    with pytest.raises(RuntimeError, match="bwrap.*not found"):
        SecureSandboxExecutor()


def test_prlimit_resource_limits_configured(sandbox):
    """Verify resource limit attributes are active."""
    assert sandbox.max_memory_bytes == 4 * 1024 * 1024 * 1024
    assert sandbox.max_procs == 128
    assert sandbox.cpu_limit_seconds == 15

