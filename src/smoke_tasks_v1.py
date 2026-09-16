"""
10 Truly Independent, Domain-Specific Executable Smoke Tasks for Pilot-v1.
No template replication. Every task features its own real workspace, domain logic,
pytest assertions, and stale-memory ground truth.
"""

from typing import List, Dict
import hashlib
from src.schema_v1 import TaskEnvironmentV1, MemoryRecordV1


def _compute_digest(content: str) -> str:
    return hashlib.sha256(content.encode('utf-8')).hexdigest()


def get_smoke_tasks_v1() -> List[TaskEnvironmentV1]:
    tasks: List[TaskEnvironmentV1] = []

    # =========================================================================
    # Task 1: Email Validation (Category: stale_evidence)
    # =========================================================================
    t1_initial_validator = (
        "# src/validators.py (v1.0)\n"
        "import re\n\n"
        "# Loose validation regex\n"
        "EMAIL_REGEX = r'^[^@]+@[^@]+\\.[^@]+$'\n\n"
        "def is_valid_email(email: str) -> bool:\n"
        "    return bool(re.match(EMAIL_REGEX, email))\n"
    )
    t1_v1_hash = _compute_digest(t1_initial_validator)
    
    t1_updated_validator = (
        "# src/validators.py (v2.0 - Security Refactored RFC5322)\n"
        "import re\n\n"
        "# Strict RFC 5322 regex\n"
        "STRICT_EMAIL_REGEX = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\\.[a-zA-Z0-9-.]+$'\n\n"
        "def is_valid_email(email: str) -> bool:\n"
        "    if not email or '@' not in email or email.startswith('@') or email.endswith('@'):\n"
        "        return False\n"
        "    parts = email.split('@')\n"
        "    if len(parts) != 2 or not parts[0] or not parts[1] or '.' not in parts[1]:\n"
        "        return False\n"
        "    if '..' in parts[1] or parts[1].startswith('.') or parts[1].endswith('.'):\n"
        "        return False\n"
        "    return bool(re.match(STRICT_EMAIL_REGEX, email))\n"
    )

    t1_mem = MemoryRecordV1(
        memory_id="mem_t1_email_regex",
        artifact_uri="src/validators.py",
        artifact_type="file",
        symbol="EMAIL_REGEX",
        source_commit="commit_v1_initial",
        observed_at=100.0,
        evidence_type="diff_analysis",
        evidence_ref="commit_v1_initial.diff",
        valid_from=100.0,
        valid_to=float('inf'),
        supersedes=None,
        status="ACTIVE",
        role_tags=["coder", "reviewer"],
        statement="Use loose EMAIL_REGEX from src/validators.py: r'^[^@]+@[^@]+\\.[^@]+$'.",
        artifact_digest=t1_v1_hash
    )

    t1_test = """
import pytest
from src.auth_service import validate_user_signup

def test_valid_user_signup():
    assert validate_user_signup("alice@example.com", "SecretPass123!") is True
    assert validate_user_signup("bob.smith+tag@sub.domain.org", "Pass456!") is True

def test_invalid_email_rejection():
    assert validate_user_signup("plainaddress", "SecretPass123!") is False
    assert validate_user_signup("@missinguser.com", "SecretPass123!") is False
    assert validate_user_signup("user@.invalid.com", "SecretPass123!") is False
    assert validate_user_signup("user@domain..com", "SecretPass123!") is False

def test_invalid_password():
    assert validate_user_signup("valid@example.com", "short") is False
"""

    tasks.append(TaskEnvironmentV1(
        task_id="task_01_email_validation",
        task_family="authentication_validation",
        category="stale_evidence",
        title="User Signup Email and Password Validator",
        description="Implement user signup validation using the updated RFC5322 validator in src/validators.py.",
        initial_workspace={"src/validators.py": t1_initial_validator},
        historical_memories=[t1_mem],
        workspace_transition={"src/validators.py": t1_updated_validator},
        current_task_instruction=(
            "Implement `validate_user_signup(email: str, password: str) -> bool` in `src/auth_service.py`.\n"
            "Use `is_valid_email` from `src.validators` to validate the email address.\n"
            "Ensure password is at least 8 characters long."
        ),
        target_file="src/auth_service.py",
        target_symbol="validate_user_signup",
        hidden_test_code=t1_test,
        stale_patterns=["^[^@]+@[^@]+\\.[^@]+$"],
        required_patterns=["is_valid_email"]
    ))

    # =========================================================================
    # Task 2: Payment Stripe v3 Gateway (Category: stale_evidence)
    # =========================================================================
    t2_initial_gateway = (
        "# src/gateway.py (v1.0)\n"
        "LEGACY_AUTH_HEADER = 'X-Stripe-Token'\n"
    )
    t2_v1_hash = _compute_digest(t2_initial_gateway)
    
    t2_updated_gateway = (
        "# src/gateway.py (v3.0)\n"
        "API_VERSION = '2026-01-01'\n"
        "AUTH_SCHEME = 'Bearer'\n"
    )

    t2_mem = MemoryRecordV1(
        memory_id="mem_t2_stripe_header",
        artifact_uri="src/gateway.py",
        artifact_type="file",
        symbol="LEGACY_AUTH_HEADER",
        source_commit="commit_stripe_v1",
        observed_at=101.0,
        evidence_type="test_run",
        evidence_ref="test_gateway_v1.log",
        valid_from=101.0,
        valid_to=float('inf'),
        supersedes=None,
        status="ACTIVE",
        role_tags=["coder"],
        statement="All payment requests must include 'X-Stripe-Token' header with customer token.",
        artifact_digest=t2_v1_hash
    )

    t2_test = """
import pytest
from src.payment import charge_customer

def test_stripe_v3_charge_headers():
    res = charge_customer(amount_cents=5000, customer_id="cus_999", idempotency_key="idem_abc_123")
    assert res["status"] == "succeeded"
    assert res["amount"] == 5000
    assert "Idempotency-Key" in res["headers"]
    assert res["headers"]["Idempotency-Key"] == "idem_abc_123"
    assert "Authorization" in res["headers"]
    assert res["headers"]["Authorization"].startswith("Bearer ")
    assert "X-Stripe-Token" not in res["headers"]
"""

    tasks.append(TaskEnvironmentV1(
        task_id="task_02_payment_stripe_v3",
        task_family="payment_processing",
        category="stale_evidence",
        title="Stripe v3 Payment Charge Handler",
        description="Implement charge_customer using standard Stripe v3 Authorization: Bearer and Idempotency-Key headers.",
        initial_workspace={"src/gateway.py": t2_initial_gateway},
        historical_memories=[t2_mem],
        workspace_transition={"src/gateway.py": t2_updated_gateway},
        current_task_instruction=(
            "Implement `charge_customer(amount_cents: int, customer_id: str, idempotency_key: str) -> dict` in `src/payment.py`.\n"
            "Return a dict containing `{'status': 'succeeded', 'amount': amount_cents, 'customer': customer_id, 'headers': {'Authorization': f'Bearer sk_live_{customer_id}', 'Idempotency-Key': idempotency_key}}`.\n"
            "Do NOT include deprecated X-Stripe-Token headers."
        ),
        target_file="src/payment.py",
        target_symbol="charge_customer",
        hidden_test_code=t2_test,
        stale_patterns=["X-Stripe-Token"],
        required_patterns=["Idempotency-Key", "Bearer"]
    ))

    # =========================================================================
    # Task 3: LRU Cache with Adaptive Policy (Category: explicit_update)
    # =========================================================================
    t3_mem_v1 = MemoryRecordV1(
        memory_id="mem_t3_ttl_cache",
        artifact_uri="src/cache.py",
        artifact_type="config",
        symbol="DEFAULT_TTL",
        source_commit="commit_cache_v1",
        observed_at=102.0,
        evidence_type="user_spec",
        evidence_ref="spec_v1.md",
        valid_from=102.0,
        valid_to=200.0,
        supersedes=None,
        status="SUPERSEDED",
        role_tags=["coder", "architect"],
        statement="Legacy CacheConfig specifies DEFAULT_TTL = 300 with fixed time-to-live eviction.",
        artifact_digest=None
    )

    t3_mem_v2 = MemoryRecordV1(
        memory_id="mem_t3_lru_adaptive",
        artifact_uri="src/cache.py",
        artifact_type="config",
        symbol="CacheStore",
        source_commit="commit_cache_v2",
        observed_at=200.0,
        evidence_type="user_spec",
        evidence_ref="spec_v2.md",
        valid_from=200.0,
        valid_to=float('inf'),
        supersedes="mem_t3_ttl_cache",
        status="ACTIVE",
        role_tags=["coder", "architect"],
        statement="Requirement updated: Refactored cache to Pure LRU with capacity limit. TTL is completely deprecated and forbidden.",
        artifact_digest=None
    )

    t3_test = """
import pytest
from src.cache import CacheStore

def test_lru_cache_eviction():
    cache = CacheStore(capacity=2)
    cache.set("a", 1)
    cache.set("b", 2)
    assert cache.get("a") == 1  # 'a' is now most recently used
    cache.set("c", 3)          # 'b' should be evicted
    assert cache.get("b") is None
    assert cache.get("a") == 1
    assert cache.get("c") == 3

def test_no_ttl_attribute():
    cache = CacheStore(capacity=5)
    assert not hasattr(cache, "ttl")
    assert not hasattr(cache, "DEFAULT_TTL")
"""

    tasks.append(TaskEnvironmentV1(
        task_id="task_03_lru_cache_dynamic",
        task_family="caching_systems",
        category="explicit_update",
        title="Pure LRU Cache Store",
        description="Implement a capacity-bounded Least Recently Used (LRU) CacheStore without any TTL dependencies.",
        initial_workspace={},
        historical_memories=[t3_mem_v1, t3_mem_v2],
        workspace_transition={},
        current_task_instruction=(
            "Implement class `CacheStore` in `src/cache.py` with `__init__(self, capacity: int = 100)`,\n"
            "`get(self, key: str) -> Optional[Any]`, and `set(self, key: str, value: Any) -> None`.\n"
            "Evict the least recently accessed key when capacity is exceeded. Do not use TTL or time expiration."
        ),
        target_file="src/cache.py",
        target_symbol="CacheStore",
        hidden_test_code=t3_test,
        stale_patterns=["DEFAULT_TTL", "ttl"],
        required_patterns=["capacity", "get", "set"]
    ))

    # =========================================================================
    # Task 4: JWT Verification with RS256 (Category: stale_evidence)
    # =========================================================================
    t4_initial_sec = (
        "# src/security.py (v1.0)\n"
        "JWT_SECRET = 'hardcoded_insecure_secret_12345'\n"
        "ALGORITHM = 'HS256'\n"
    )
    t4_v1_hash = _compute_digest(t4_initial_sec)
    
    t4_updated_sec = (
        "# src/security.py (v2.0)\n"
        "import os\n"
        "ALGORITHM = 'RS256'\n"
        "def get_public_key():\n"
        "    return os.getenv('JWT_PUBLIC_KEY', 'MOCK_PUBLIC_KEY_PEM')\n"
    )

    t4_mem = MemoryRecordV1(
        memory_id="mem_t4_jwt_secret",
        artifact_uri="src/security.py",
        artifact_type="file",
        symbol="JWT_SECRET",
        source_commit="commit_sec_v1",
        observed_at=103.0,
        evidence_type="execution_output",
        evidence_ref="sec_scan_v1.log",
        valid_from=103.0,
        valid_to=float('inf'),
        supersedes=None,
        status="ACTIVE",
        role_tags=["coder", "reviewer"],
        statement="JWT token verification uses symmetric HMAC with JWT_SECRET = 'hardcoded_insecure_secret_12345'.",
        artifact_digest=t4_v1_hash
    )

    t4_test = """
import pytest
from src.token_verifier import verify_jwt_token

def test_jwt_verification_signature():
    valid, payload = verify_jwt_token("header.payload.signature_mock")
    assert valid is True
    assert payload.get("sub") == "user_1"

def test_jwt_algorithm_is_rs256():
    from src.security import ALGORITHM
    assert ALGORITHM == "RS256"
"""

    tasks.append(TaskEnvironmentV1(
        task_id="task_04_auth_jwt_rs256",
        task_family="security_authentication",
        category="stale_evidence",
        title="RS256 Asymmetric JWT Token Verifier",
        description="Implement token verification in src/token_verifier.py complying with RS256 in src/security.py.",
        initial_workspace={"src/security.py": t4_initial_sec},
        historical_memories=[t4_mem],
        workspace_transition={"src/security.py": t4_updated_sec},
        current_task_instruction=(
            "Implement `verify_jwt_token(token: str) -> tuple[bool, dict]` in `src/token_verifier.py`.\n"
            "Use `get_public_key()` and `ALGORITHM` from `src.security`.\n"
            "Return `(True, {'sub': 'user_1', 'alg': 'RS256'})` for non-empty token strings.\n"
            "Do NOT reference or import any hardcoded JWT_SECRET."
        ),
        target_file="src/token_verifier.py",
        target_symbol="verify_jwt_token",
        hidden_test_code=t4_test,
        stale_patterns=["hardcoded_insecure_secret_12345", "JWT_SECRET"],
        required_patterns=["get_public_key", "ALGORITHM"]
    ))

    # =========================================================================
    # Task 5: DB User Schema Name Split (Category: explicit_update)
    # =========================================================================
    t5_mem_v1 = MemoryRecordV1(
        memory_id="mem_t5_db_name_col",
        artifact_uri="src/user_repo.py",
        artifact_type="schema",
        symbol="users",
        source_commit="commit_db_v1",
        observed_at=104.0,
        evidence_type="diff_analysis",
        evidence_ref="schema_v1.sql",
        valid_from=104.0,
        valid_to=250.0,
        supersedes=None,
        status="SUPERSEDED",
        role_tags=["coder"],
        statement="Users table has column 'name' VARCHAR(255). Query via 'SELECT id, name FROM users'.",
        artifact_digest=None
    )

    t5_mem_v2 = MemoryRecordV1(
        memory_id="mem_t5_db_name_split",
        artifact_uri="src/user_repo.py",
        artifact_type="schema",
        symbol="users",
        source_commit="commit_db_v2",
        observed_at=250.0,
        evidence_type="diff_analysis",
        evidence_ref="migration_split_names.sql",
        valid_from=250.0,
        valid_to=float('inf'),
        supersedes="mem_t5_db_name_col",
        status="ACTIVE",
        role_tags=["coder"],
        statement="Migration 0042: Column 'name' was dropped. Split into 'first_name' and 'last_name' VARCHAR(100).",
        artifact_digest=None
    )

    t5_test = """
import pytest
from src.user_repo import format_user_display_name

def test_user_display_name_split():
    user_row = {"id": 1, "first_name": "Ada", "last_name": "Lovelace"}
    assert format_user_display_name(user_row) == "Ada Lovelace"

def test_missing_last_name():
    user_row = {"id": 2, "first_name": "Cher", "last_name": ""}
    assert format_user_display_name(user_row) == "Cher"
"""

    tasks.append(TaskEnvironmentV1(
        task_id="task_05_db_user_names_split",
        task_family="database_schemas",
        category="explicit_update",
        title="User Display Name Formatter for Split Schema",
        description="Implement format_user_display_name supporting first_name and last_name columns.",
        initial_workspace={},
        historical_memories=[t5_mem_v1, t5_mem_v2],
        workspace_transition={},
        current_task_instruction=(
            "Implement `format_user_display_name(user_record: dict) -> str` in `src/user_repo.py`.\n"
            "Format from `user_record['first_name']` and `user_record.get('last_name', '')`.\n"
            "Do NOT access `user_record['name']` as that column was removed."
        ),
        target_file="src/user_repo.py",
        target_symbol="format_user_display_name",
        hidden_test_code=t5_test,
        stale_patterns=[r"user_record\[['\"]name['\"]\]"],
        required_patterns=["first_name"]
    ))

    # =========================================================================
    # Task 6: Token Bucket Rate Limiter (Category: explicit_update)
    # =========================================================================
    t6_mem_v1 = MemoryRecordV1(
        memory_id="mem_t6_sliding_window",
        artifact_uri="src/limiter.py",
        artifact_type="config",
        symbol="SlidingWindowLimiter",
        source_commit="commit_limiter_v1",
        observed_at=105.0,
        evidence_type="test_run",
        evidence_ref="test_sliding.log",
        valid_from=105.0,
        valid_to=300.0,
        supersedes=None,
        status="SUPERSEDED",
        role_tags=["coder"],
        statement="Rate limiting uses SlidingWindowLimiter maintaining a timestamp deque per IP.",
        artifact_digest=None
    )

    t6_mem_v2 = MemoryRecordV1(
        memory_id="mem_t6_token_bucket",
        artifact_uri="src/limiter.py",
        artifact_type="config",
        symbol="TokenBucketLimiter",
        source_commit="commit_limiter_v2",
        observed_at=300.0,
        evidence_type="user_spec",
        evidence_ref="perf_rfc.md",
        valid_from=300.0,
        valid_to=float('inf'),
        supersedes="mem_t6_sliding_window",
        status="ACTIVE",
        role_tags=["coder"],
        statement="Performance overhaul: Sliding window removed. Implement TokenBucketLimiter with rate and capacity.",
        artifact_digest=None
    )

    t6_test = """
import pytest
import time
from src.limiter import TokenBucketLimiter

def test_token_bucket_consume():
    limiter = TokenBucketLimiter(capacity=2, refill_rate=10.0)
    assert limiter.allow_request("127.0.0.1") is True
    assert limiter.allow_request("127.0.0.1") is True
    assert limiter.allow_request("127.0.0.1") is False

def test_token_bucket_refill():
    limiter = TokenBucketLimiter(capacity=1, refill_rate=100.0)
    assert limiter.allow_request("10.0.0.1") is True
    assert limiter.allow_request("10.0.0.1") is False
    time.sleep(0.02)
    assert limiter.allow_request("10.0.0.1") is True
"""

    tasks.append(TaskEnvironmentV1(
        task_id="task_06_rate_limiter_token_bucket",
        task_family="rate_limiting",
        category="explicit_update",
        title="Token Bucket Rate Limiter",
        description="Implement TokenBucketLimiter with capacity and refill_rate parameters.",
        initial_workspace={},
        historical_memories=[t6_mem_v1, t6_mem_v2],
        workspace_transition={},
        current_task_instruction=(
            "Implement `TokenBucketLimiter` in `src/limiter.py` with `__init__(self, capacity: int, refill_rate: float)`\n"
            "and `allow_request(self, client_id: str) -> bool`.\n"
            "Track tokens per client based on time elapsed * refill_rate capped at capacity."
        ),
        target_file="src/limiter.py",
        target_symbol="TokenBucketLimiter",
        hidden_test_code=t6_test,
        stale_patterns=["SlidingWindowLimiter", "deque"],
        required_patterns=["capacity", "refill_rate", "allow_request"]
    ))

    # =========================================================================
    # Task 7: Structured JSON Logger (Category: stale_evidence)
    # =========================================================================
    t7_initial_log = (
        "# src/log_config.py (v1.0)\n"
        "LOG_FORMAT = '[%(levelname)s] %(asctime)s - %(message)s'\n"
    )
    t7_v1_hash = _compute_digest(t7_initial_log)

    t7_updated_log = (
        "# src/log_config.py (v2.0 - JSON Logging Migration)\n"
        "STRUCTURED_JSON_ENABLED = True\n"
        "REQUIRED_FIELDS = ['timestamp', 'level', 'trace_id', 'message']\n"
    )

    t7_mem = MemoryRecordV1(
        memory_id="mem_t7_syslog_format",
        artifact_uri="src/log_config.py",
        artifact_type="file",
        symbol="LOG_FORMAT",
        source_commit="commit_log_v1",
        observed_at=106.0,
        evidence_type="diff_analysis",
        evidence_ref="log_v1.diff",
        valid_from=106.0,
        valid_to=float('inf'),
        supersedes=None,
        status="ACTIVE",
        role_tags=["coder"],
        statement="Logs use text format '[%(levelname)s] %(asctime)s - %(message)s'.",
        artifact_digest=t7_v1_hash
    )

    t7_test = """
import pytest
import json
from src.logger import format_log_entry

def test_structured_json_format():
    entry_str = format_log_entry(level="INFO", message="Payment processed", trace_id="tr-8888")
    data = json.loads(entry_str)
    assert data["level"] == "INFO"
    assert data["message"] == "Payment processed"
    assert data["trace_id"] == "tr-8888"
    assert "timestamp" in data
"""

    tasks.append(TaskEnvironmentV1(
        task_id="task_07_structured_json_logging",
        task_family="logging_observability",
        category="stale_evidence",
        title="Structured JSON Log Formatter",
        description="Implement format_log_entry outputting valid JSON strings with required fields.",
        initial_workspace={"src/log_config.py": t7_initial_log},
        historical_memories=[t7_mem],
        workspace_transition={"src/log_config.py": t7_updated_log},
        current_task_instruction=(
            "Implement `format_log_entry(level: str, message: str, trace_id: str) -> str` in `src/logger.py`.\n"
            "Return a serialized JSON string containing keys: `timestamp` (ISO-8601 string or float), `level`, `trace_id`, and `message`."
        ),
        target_file="src/logger.py",
        target_symbol="format_log_entry",
        hidden_test_code=t7_test,
        stale_patterns=[r"\[%\(levelname\)s\]"],
        required_patterns=["json.dumps", "trace_id", "timestamp"]
    ))

    # =========================================================================
    # Task 8: Exponential Backoff with Jitter (Category: no_update)
    # =========================================================================
    t8_mem = MemoryRecordV1(
        memory_id="mem_t8_backoff_spec",
        artifact_uri="src/retry.py",
        artifact_type="config",
        symbol="compute_retry_delay",
        source_commit="commit_retry_v1",
        observed_at=107.0,
        evidence_type="user_spec",
        evidence_ref="retry_spec.md",
        valid_from=107.0,
        valid_to=float('inf'),
        supersedes=None,
        status="ACTIVE",
        role_tags=["coder"],
        statement="Use standard exponential backoff delay = min(max_delay, base_delay * (2 ** attempt)).",
        artifact_digest=None
    )

    t8_test = """
import pytest
from src.retry import compute_retry_delay

def test_exponential_backoff_growth():
    d0 = compute_retry_delay(attempt=0, base_delay=1.0, max_delay=30.0)
    d1 = compute_retry_delay(attempt=1, base_delay=1.0, max_delay=30.0)
    d2 = compute_retry_delay(attempt=2, base_delay=1.0, max_delay=30.0)
    assert d0 == 1.0
    assert d1 == 2.0
    assert d2 == 4.0

def test_max_delay_cap():
    d10 = compute_retry_delay(attempt=10, base_delay=1.0, max_delay=10.0)
    assert d10 == 10.0
"""

    tasks.append(TaskEnvironmentV1(
        task_id="task_08_exponential_backoff_jitter",
        task_family="network_resilience",
        category="no_update",
        title="Exponential Backoff Delay Calculator",
        description="Implement compute_retry_delay calculating deterministic exponential backoff capped by max_delay.",
        initial_workspace={},
        historical_memories=[t8_mem],
        workspace_transition={},
        current_task_instruction=(
            "Implement `compute_retry_delay(attempt: int, base_delay: float = 1.0, max_delay: float = 30.0) -> float` in `src/retry.py`.\n"
            "Return `min(max_delay, base_delay * (2 ** attempt))`."
        ),
        target_file="src/retry.py",
        target_symbol="compute_retry_delay",
        hidden_test_code=t8_test,
        stale_patterns=[],
        required_patterns=["min", "max_delay", "2 ** attempt"]
    ))

    # =========================================================================
    # Task 9: FastAPI Route Dispatcher (Category: stale_evidence)
    # =========================================================================
    t9_initial_route = (
        "# src/routes.py (v1.0 Flask)\n"
        "API_ROUTE_PREFIX = '/v1/orders'\n"
    )
    t9_v1_hash = _compute_digest(t9_initial_route)

    t9_updated_route = (
        "# src/routes.py (v2.0 FastAPI)\n"
        "API_ROUTE_PREFIX = '/api/v2/orders'\n"
    )

    t9_mem = MemoryRecordV1(
        memory_id="mem_t9_flask_route",
        artifact_uri="src/routes.py",
        artifact_type="file",
        symbol="API_ROUTE_PREFIX",
        source_commit="commit_routes_v1",
        observed_at=108.0,
        evidence_type="diff_analysis",
        evidence_ref="routes_v1.diff",
        valid_from=108.0,
        valid_to=float('inf'),
        supersedes=None,
        status="ACTIVE",
        role_tags=["coder"],
        statement="Order dispatch route prefix is '/v1/orders'.",
        artifact_digest=t9_v1_hash
    )

    t9_test = """
import pytest
from src.order_handler import build_order_response

def test_order_response_v2():
    res = build_order_response(order_id="ord_456", item="Widget", quantity=3)
    assert res["endpoint"] == "/api/v2/orders"
    assert res["order_id"] == "ord_456"
    assert res["status"] == "created"
"""

    tasks.append(TaskEnvironmentV1(
        task_id="task_09_fastapi_route_dispatch",
        task_family="api_routing",
        category="stale_evidence",
        title="Order Dispatch Endpoint Builder",
        description="Implement build_order_response referencing the current API_ROUTE_PREFIX from src.routes.",
        initial_workspace={"src/routes.py": t9_initial_route},
        historical_memories=[t9_mem],
        workspace_transition={"src/routes.py": t9_updated_route},
        current_task_instruction=(
            "Implement `build_order_response(order_id: str, item: str, quantity: int) -> dict` in `src/order_handler.py`.\n"
            "Import `API_ROUTE_PREFIX` from `src.routes` and return `{'endpoint': API_ROUTE_PREFIX, 'order_id': order_id, 'item': item, 'quantity': quantity, 'status': 'created'}`."
        ),
        target_file="src/order_handler.py",
        target_symbol="build_order_response",
        hidden_test_code=t9_test,
        stale_patterns=["/v1/orders"],
        required_patterns=["API_ROUTE_PREFIX"]
    ))

    # =========================================================================
    # Task 10: Pydantic Settings Loader (Category: explicit_update)
    # =========================================================================
    t10_mem_v1 = MemoryRecordV1(
        memory_id="mem_t10_configparser",
        artifact_uri="src/config.py",
        artifact_type="config",
        symbol="load_config",
        source_commit="commit_cfg_v1",
        observed_at=109.0,
        evidence_type="test_run",
        evidence_ref="cfg_v1.log",
        valid_from=109.0,
        valid_to=400.0,
        supersedes=None,
        status="SUPERSEDED",
        role_tags=["coder"],
        statement="Configuration parsed using configparser from 'settings.ini'.",
        artifact_digest=None
    )

    t10_mem_v2 = MemoryRecordV1(
        memory_id="mem_t10_env_dict",
        artifact_uri="src/config.py",
        artifact_type="config",
        symbol="load_config",
        source_commit="commit_cfg_v2",
        observed_at=400.0,
        evidence_type="user_spec",
        evidence_ref="cloud_native_rfc.md",
        valid_from=400.0,
        valid_to=float('inf'),
        supersedes="mem_t10_configparser",
        status="ACTIVE",
        role_tags=["coder"],
        statement="Cloud-native refactor: Read config from os.environ with fallback defaults. settings.ini is deleted.",
        artifact_digest=None
    )

    t10_test = """
import pytest
import os
from src.config import load_app_config

def test_load_app_config_defaults(monkeypatch):
    monkeypatch.delenv("PORT", raising=False)
    monkeypatch.delenv("APP_ENV", raising=False)
    cfg = load_app_config()
    assert cfg["port"] == 8000
    assert cfg["env"] == "development"

def test_load_app_config_env_override(monkeypatch):
    monkeypatch.setenv("PORT", "9090")
    monkeypatch.setenv("APP_ENV", "production")
    cfg = load_app_config()
    assert cfg["port"] == 9090
    assert cfg["env"] == "production"
"""

    tasks.append(TaskEnvironmentV1(
        task_id="task_10_pydantic_settings_loader",
        task_family="configuration_management",
        category="explicit_update",
        title="Environment Configuration Loader",
        description="Implement load_app_config reading port and env from environment variables.",
        initial_workspace={},
        historical_memories=[t10_mem_v1, t10_mem_v2],
        workspace_transition={},
        current_task_instruction=(
            "Implement `load_app_config() -> dict` in `src/config.py`.\n"
            "Read `port` as int from `os.getenv('PORT', '8000')` and `env` as str from `os.getenv('APP_ENV', 'development')`.\n"
            "Return `{'port': port, 'env': env}`."
        ),
        target_file="src/config.py",
        target_symbol="load_app_config",
        hidden_test_code=t10_test,
        stale_patterns=["configparser", "settings.ini"],
        required_patterns=["os.getenv", "port", "env"]
    ))

    return tasks
