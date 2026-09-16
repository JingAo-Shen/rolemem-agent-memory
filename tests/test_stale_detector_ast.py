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
