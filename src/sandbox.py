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
        """Prepares initial files based on task initial_state."""
        family = self.task_spec.get("family")
        tid = self.task_spec.get("id")

        if "db_config.py" in str(self.task_spec):
            with open(os.path.join(self.work_dir, "db_config.py"), "w") as f:
                f.write("TIMEOUT_SEC = 5\n")
        elif "user_api.py" in str(self.task_spec):
            with open(os.path.join(self.work_dir, "user_api.py"), "w") as f:
                f.write("def register(email):\n    return (200, 'Success')\n")
        elif "logger.py" in str(self.task_spec):
            with open(os.path.join(self.work_dir, "logger.py"), "w") as f:
                f.write("def format_log(msg):\n    return {'msg': msg, 'timestamp': '2026-09-15 12:00:00'}\n")
        elif "cache_config.py" in str(self.task_spec):
            with open(os.path.join(self.work_dir, "cache_config.py"), "w") as f:
                f.write("DEFAULT_TTL = 60\n")
        elif "payment_service.py" in str(self.task_spec):
            with open(os.path.join(self.work_dir, "payment_service.py"), "w") as f:
                f.write("def process_payment(amount):\n    return {'status': 'SUCCESS', 'tx_id': 12345}\n")
        elif "billing.py" in str(self.task_spec):
            with open(os.path.join(self.work_dir, "billing.py"), "w") as f:
                f.write("def calculate_fee(amount):\n    return round(amount * 1.0, 2)\n")
        elif "auth.py" in str(self.task_spec):
            with open(os.path.join(self.work_dir, "auth.py"), "w") as f:
                f.write("SALT = 'legacy_salt_value'\ndef get_salt_from_env():\n    return 'vault_salt'\n")
        elif "orders.py" in str(self.task_spec):
            with open(os.path.join(self.work_dir, "orders.py"), "w") as f:
                f.write("OrderStatus = ['PENDING', 'PAID', 'SHIPPED']\n")
        elif "policy.py" in str(self.task_spec):
            with open(os.path.join(self.work_dir, "policy.py"), "w") as f:
                f.write("def has_role(user, role):\n    return role == 'admin'\n")

    def execute_mock_action(self, method: str, retrieved_memories: list) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Executes mock deterministic behavior based on retrieved memories to verify
        whether stale memories mislead the coder/reviewer vs whether valid memories result in correct code.
        """
        tid = self.task_spec["id"]
        cat = self.task_spec["category"]

        # Check if retrieved memories contain stale/superseded statements
        retrieved_texts = " ".join([m["statement"] for m in retrieved_memories])

        stale_used = False
        if cat == "explicit_update":
            # For fixture 4 (cache_config), if TTL 60 is retrieved instead of LRU
            if "DEFAULT_TTL = 60" in retrieved_texts and "ADAPTIVE_LRU" not in retrieved_texts:
                stale_used = True
                with open(os.path.join(self.work_dir, "cache_config.py"), "w") as f:
                    f.write("DEFAULT_TTL = 60\n")
            else:
                with open(os.path.join(self.work_dir, "cache_config.py"), "w") as f:
                    f.write("POLICY = 'ADAPTIVE_LRU'\nMAX_KEYS = 10000\n")

            # For fixture 5 (payment_service), if flat status retrieved
            if "flat status" in retrieved_texts and "standard wrapper" not in retrieved_texts:
                stale_used = True
                with open(os.path.join(self.work_dir, "payment_service.py"), "w") as f:
                    f.write("def process_payment(amount):\n    return {'status': 'SUCCESS', 'tx_id': 12345}\n")
            else:
                with open(os.path.join(self.work_dir, "payment_service.py"), "w") as f:
                    f.write("def process_payment(amount):\n    return {'code': 200, 'data': {'status': 'SUCCESS', 'tx_id': 12345}}\n")

            # For fixture 6 (billing), if float 2 decimal places retrieved
            if "float with 2 decimal" in retrieved_texts and "integer micro-units" not in retrieved_texts:
                stale_used = True
                with open(os.path.join(self.work_dir, "billing.py"), "w") as f:
                    f.write("def calculate_fee(amount):\n    return round(amount * 1.0, 2)\n")
            else:
                with open(os.path.join(self.work_dir, "billing.py"), "w") as f:
                    f.write("def calculate_fee(amount):\n    return int(amount * 1000000)\n")

        elif cat == "no_update":
            # Direct correct implementation for no-update
            if "db_config.py" in str(self.task_spec):
                with open(os.path.join(self.work_dir, "db_config.py"), "w") as f:
                    f.write("TIMEOUT_MS = 5000\n")
            elif "user_api.py" in str(self.task_spec):
                with open(os.path.join(self.work_dir, "user_api.py"), "w") as f:
                    f.write("import re\ndef register(email):\n    if '..' in email or not re.match(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\\.[a-zA-Z0-9-.]+$', email):\n        return (400, 'Invalid email format')\n    return (200, 'Success')\n")
            elif "logger.py" in str(self.task_spec):
                with open(os.path.join(self.work_dir, "logger.py"), "w") as f:
                    f.write("def format_log(msg):\n    return {'msg': msg, 'timestamp': '2026-09-15T12:00:00Z'}\n")

        elif cat == "stale_evidence":
            if "legacy_salt_value" in retrieved_texts and "Refactor auth.py" not in retrieved_texts:
                stale_used = True
                with open(os.path.join(self.work_dir, "auth.py"), "w") as f:
                    f.write("SALT = 'legacy_salt_value'\ndef get_salt_from_env():\n    return 'vault_salt'\n")
            else:
                with open(os.path.join(self.work_dir, "auth.py"), "w") as f:
                    f.write("def get_salt_from_env():\n    return 'vault_salt'\n")

            if "PENDING" in retrieved_texts and "CREATED" not in retrieved_texts:
                stale_used = True
                with open(os.path.join(self.work_dir, "orders.py"), "w") as f:
                    f.write("OrderStatus = ['PENDING', 'PAID', 'SHIPPED']\n")
            else:
                with open(os.path.join(self.work_dir, "orders.py"), "w") as f:
                    f.write("OrderStatus = ['CREATED', 'AUTHORIZED', 'FULFILLED', 'CANCELLED']\n")

            if "has_role" in retrieved_texts and "check_attribute_policy" not in retrieved_texts:
                stale_used = True
                with open(os.path.join(self.work_dir, "policy.py"), "w") as f:
                    f.write("def has_role(user, role):\n    return role == 'admin'\n")
            else:
                with open(os.path.join(self.work_dir, "policy.py"), "w") as f:
                    f.write("def check_attribute_policy(user, resource, action):\n    return True\n")

        # Evaluate hidden verification
        passed, error_msg = self.evaluate_hidden()
        return passed, error_msg, {"stale_used": stale_used}

    def evaluate_hidden(self) -> Tuple[bool, str]:
        """Runs the hidden verification assertions in an isolated namespace."""
        sys_path_orig = list(sys.path)
        sys.path.insert(0, self.work_dir)

        # Mock review report object for conflict fixtures
        class ReviewReport:
            has_conflict_flag = True
            is_escalated = True
            status = 'NEEDS_CLARIFICATION'
            conflicting_evidences = [1, 2]

        local_ns = {
            "review_report": ReviewReport()
        }

        # Dynamically import any python files in the work_dir
        for f in os.listdir(self.work_dir):
            if f.endswith(".py"):
                mod_name = f[:-3]
                try:
                    spec = importlib.util.spec_from_file_location(mod_name, os.path.join(self.work_dir, f))
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)
                    local_ns[mod_name] = mod
                except Exception as e:
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
