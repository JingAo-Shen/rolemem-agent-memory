"""
Gate 5 Automated Tests: AST-based Stale Action Detection.
"""

import pytest
from src.stale_detector_ast import ASTStaleActionDetector


def test_comment_only_is_mention_not_active_use():
    code = """
# Note: DEFAULT_TTL has been superseded by LRU.
def configure_cache():
    return {"policy": "LRU"}
"""
    res = ASTStaleActionDetector.analyze(code, ["DEFAULT_TTL"])
    assert res.stale_active_use is False, "Benign comment was incorrectly flagged as active stale use!"
    assert res.stale_mention is True, "Comment mention was not detected!"
    assert len(res.active_nodes) == 0


def test_docstring_only_is_mention_not_active_use():
    code = """
def init_payment():
    \"\"\"
    Deprecated header X-Stripe-Token is no longer accepted.
    Use Authorization: Bearer instead.
    \"\"\"
    return {"Authorization": "Bearer tok"}
"""
    res = ASTStaleActionDetector.analyze(code, ["X-Stripe-Token"])
    assert res.stale_active_use is False
    assert res.stale_mention is True


def test_active_import_is_flagged():
    code = """
from src.security import JWT_SECRET

def verify(token):
    return True
"""
    res = ASTStaleActionDetector.analyze(code, ["JWT_SECRET"])
    assert res.stale_active_use is True
    assert any(n["type"] == "ImportFrom" and n["symbol"] == "JWT_SECRET" for n in res.active_nodes)


def test_active_variable_assignment_is_flagged():
    code = """
DEFAULT_TTL = 60

class Cache:
    pass
"""
    res = ASTStaleActionDetector.analyze(code, ["DEFAULT_TTL"])
    assert res.stale_active_use is True
    assert any("DEFAULT_TTL" == n["symbol"] for n in res.active_nodes)


def test_active_attribute_access_is_flagged():
    code = """
def check_policy(config):
    return config.DEFAULT_TTL
"""
    res = ASTStaleActionDetector.analyze(code, ["DEFAULT_TTL"])
    assert res.stale_active_use is True
    assert any(n["type"] == "Attribute" and n["symbol"] == "DEFAULT_TTL" for n in res.active_nodes)


def test_active_keyword_argument_is_flagged():
    code = """
def build_cache():
    return initialize_store(ttl=300)
"""
    res = ASTStaleActionDetector.analyze(code, ["ttl"])
    assert res.stale_active_use is True
    assert any(n["type"] == "KeywordArg" and n["symbol"] == "ttl" for n in res.active_nodes)


def test_active_dict_subscript_and_string_literal_is_flagged():
    code = """
def send_request(token):
    headers = {}
    headers["X-Stripe-Token"] = token
    return headers
"""
    res = ASTStaleActionDetector.analyze(code, ["X-Stripe-Token"])
    assert res.stale_active_use is True
    assert res.stale_mentions is False
    assert any(n["symbol"] == "X-Stripe-Token" for n in res.active_stale_nodes)


def test_active_assignment_string_literal_is_flagged():
    code = """
def get_auth_algo():
    algorithm = "HS256"
    return algorithm
"""
    res = ASTStaleActionDetector.analyze(code, ["HS256"])
    assert res.stale_active_use is True
    assert any(n["symbol"] == "HS256" for n in res.active_stale_nodes)


def test_active_comparison_literal_is_flagged():
    code = """
def verify_cache(policy):
    if policy == "TTL":
        return True
    return False
"""
    res = ASTStaleActionDetector.analyze(code, ["TTL"])
    assert res.stale_active_use is True
    assert any(n["symbol"] == "TTL" for n in res.active_stale_nodes)


def test_urllib3_method_whitelist_keyword_is_flagged_active():
    spec = {
        "deprecated_symbols": ["method_whitelist"],
        "replacement_symbols": ["allowed_methods"],
        "stale_action_patterns": [
            {"node_type": "keyword", "name": "method_whitelist"}
        ]
    }
    # 1. Active usage of deprecated keyword argument
    code_active = """
from urllib3.util.retry import Retry
def build_retry(methods):
    return Retry(total=3, method_whitelist=methods)
"""
    res_active = ASTStaleActionDetector.analyze_spec(code_active, spec)
    assert res_active.stale_active_use is True, "Retry(method_whitelist=...) must be flagged as stale active use!"

    # 2. Clean modern usage with replacement
    code_clean = """
from urllib3.util.retry import Retry
def build_retry(methods):
    return Retry(total=3, allowed_methods=methods)
"""
    res_clean = ASTStaleActionDetector.analyze_spec(code_clean, spec)
    assert res_clean.stale_active_use is False, "Retry(allowed_methods=...) should NOT be flagged as stale!"

    # 3. Mention in comment only
    code_comment = """
from urllib3.util.retry import Retry
# Note: method_whitelist was deprecated in favor of allowed_methods
def build_retry(methods):
    return Retry(total=3, allowed_methods=methods)
"""
    res_comment = ASTStaleActionDetector.analyze_spec(code_comment, spec)
    assert res_comment.stale_active_use is False, "Comment mention must not be flagged as active use!"
    assert res_comment.stale_mention is True, "Comment mention must be detected as stale_mention!"


def test_urllib3_empty_allowed_methods_pattern():
    spec = {
        "deprecated_symbols": ["empty_allowed_methods"],
        "stale_action_patterns": [
            {"node_type": "keyword", "name": "allowed_methods", "value_type": "empty_collection"}
        ]
    }
    # Passing empty list []
    code_empty = """
from urllib3.util.retry import Retry
r = Retry(allowed_methods=[])
"""
    res_empty = ASTStaleActionDetector.analyze_spec(code_empty, spec)
    assert res_empty.stale_active_use is True, "allowed_methods=[] must be flagged by empty_collection pattern!"

    # Passing valid None
    code_valid = """
from urllib3.util.retry import Retry
r = Retry(allowed_methods=None)
"""
    res_valid = ASTStaleActionDetector.analyze_spec(code_valid, spec)
    assert res_valid.stale_active_use is False, "allowed_methods=None should not be flagged!"

