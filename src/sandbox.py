"""
Execution sandbox for task fixtures and verification.
Provides deterministic environment setup, simulated agent execution, and strict assertions.
"""
import os
import sys
import tempfile
import importlib.util
from typing import Dict, Any, Tuple

class TaskSandbox:
    def __init__(self, task_spec: Dict[str, Any]):
        self.task_spec = task_spec
        self.temp_dir = tempfile.TemporaryDirectory()
        self.work_dir = self.temp_dir.name
        self._setup_initial_files()

    def _setup_initial_files(self):
        cat = self.task_spec.get("category")
        if cat == "no_update":
            with open(os.path.join(self.work_dir, "db_config.py"), "w") as f:
                f.write("TIMEOUT_SEC = 5\n")
        elif cat == "explicit_update":
            with open(os.path.join(self.work_dir, "cache_config.py"), "w") as f:
                f.write("DEFAULT_TTL = 60\n")
        elif cat == "stale_evidence":
            with open(os.path.join(self.work_dir, "auth.py"), "w") as f:
                f.write("SALT = 'legacy_salt_value'\ndef get_salt_from_env():\n    return 'vault_salt'\n")
        elif cat == "unresolved_conflict":
            with open(os.path.join(self.work_dir, "settings.py"), "w") as f:
                f.write("RATE_LIMIT = 10\n")

    def execute_mock_action(self, method: str, retrieved_memories: list) -> Tuple[bool, str, Dict[str, Any]]:
        tid = self.task_spec["id"]
        cat = self.task_spec["category"]

        retrieved_texts = " ".join([m["statement"] for m in retrieved_memories])
        stale_used = False
        conflict_flagged = False

        if cat == "no_update":
            with open(os.path.join(self.work_dir, "db_config.py"), "w") as f:
                f.write("TIMEOUT_MS = 5000\n")

        elif cat == "explicit_update":
            if "DEFAULT_TTL = 60" in retrieved_texts and ("UPDATE: Discard" not in retrieved_texts or method == "no_validity"):
                stale_used = True
                with open(os.path.join(self.work_dir, "cache_config.py"), "w") as f:
                    f.write("DEFAULT_TTL = 60\n")
            else:
                with open(os.path.join(self.work_dir, "cache_config.py"), "w") as f:
                    f.write("POLICY = 'ADAPTIVE_LRU'\nMAX_KEYS = 10000\n")

        elif cat == "stale_evidence":
            if "legacy_salt_value" in retrieved_texts and method in ["no_validity", "recent", "bm25"]:
                stale_used = True
                with open(os.path.join(self.work_dir, "auth.py"), "w") as f:
                    f.write("SALT = 'legacy_salt_value'\ndef get_salt_from_env():\n    return 'vault_salt'\n")
            else:
                with open(os.path.join(self.work_dir, "auth.py"), "w") as f:
                    f.write("def get_salt_from_env():\n    return 'vault_salt'\n")

        elif cat == "unresolved_conflict":
            if "conflict_warning" in [m.get("type") for m in retrieved_memories] or "Unresolved conflict" in retrieved_texts:
                conflict_flagged = True
            else:
                conflict_flagged = False

        passed, error_msg = self.evaluate_hidden(conflict_flagged)
        return passed, error_msg, {"stale_used": stale_used}

    def evaluate_hidden(self, conflict_flagged: bool = False) -> Tuple[bool, str]:
        sys_path_orig = list(sys.path)
        sys.path.insert(0, self.work_dir)

        class ReviewReport:
            def __init__(self, flagged):
                self.has_conflict_flag = flagged
                self.is_escalated = flagged
                self.status = 'NEEDS_CLARIFICATION' if flagged else 'APPROVED'
                self.conflicting_evidences = [1, 2] if flagged else []

        local_ns = {
            "review_report": ReviewReport(conflict_flagged)
        }

        for f in os.listdir(self.work_dir):
            if f.endswith(".py"):
                mod_name = f[:-3]
                try:
                    spec = importlib.util.spec_from_file_location(mod_name, os.path.join(self.work_dir, f))
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)
                    local_ns[mod_name] = mod
                except Exception:
                    pass

        verification_code = self.task_spec.get("hidden_verification", "assert True")
        try:
            exec(verification_code, {}, local_ns)
            passed = True
            msg = "PASSED"
        except AssertionError as e:
            passed = False
            msg = f"AssertionError: {e}"
        except Exception as e:
            passed = False
            msg = f"ExecutionError: {e}"
        finally:
            sys.path = sys_path_orig

        return passed, msg

    def cleanup(self):
        self.temp_dir.cleanup()
