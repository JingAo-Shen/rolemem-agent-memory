"""
tests/test_stale_detector_ast_v2.py
Regression tests for ASTStaleActionDetectorV2.
Verifies provenance-aware qualified symbol tracking, local shadowing, and passive mentions.
"""

import pytest
import sys
sys.path.insert(0, "/code/rolemem-agent-memory")
from src.stale_detector_ast_v2 import ASTStaleActionDetectorV2


@pytest.fixture
def werkzeug_spec():
    return {
        "deprecated_symbols": ["werkzeug.wsgi.environ_property"],
        "stale_action_patterns": []
    }


def test_qualified_import_use(werkzeug_spec):
    code = """
from werkzeug.wsgi import environ_property

class Request:
    host = environ_property("HTTP_HOST")
"""
    res = ASTStaleActionDetectorV2.analyze(code, werkzeug_spec)
    assert res.stale_active_use is True
    assert any("ImportFrom" in n["type"] or "NameStaleImported" in n["type"] for n in res.active_nodes)


def test_qualified_attribute_use(werkzeug_spec):
    code = """
import werkzeug.wsgi

class Request:
    host = werkzeug.wsgi.environ_property("HTTP_HOST")
"""
    res = ASTStaleActionDetectorV2.analyze(code, werkzeug_spec)
    assert res.stale_active_use is True
    assert any(n["type"] == "Attribute" for n in res.active_nodes)


def test_keyword_stale_api():
    spec = {
        "deprecated_symbols": [],
        "stale_action_patterns": [
            {
                "node_type": "keyword",
                "name": "legacy_noself",
                "value": True
            }
        ]
    }
    code = """
def my_hook():
    varnames(fn, legacy_noself=True)
"""
    res = ASTStaleActionDetectorV2.analyze(code, spec)
    assert res.stale_active_use is True
    assert any(n["type"] == "KeywordArgPattern" for n in res.active_nodes)

    # Now verify legacy_noself=False is clean
    clean_code = """
def my_hook():
    varnames(fn, legacy_noself=False)
"""
    res_clean = ASTStaleActionDetectorV2.analyze(clean_code, spec)
    assert res_clean.stale_active_use is False


def test_getattr_stale_access(werkzeug_spec):
    code = """
import werkzeug.wsgi

def get_prop(key):
    cls = getattr(werkzeug.wsgi, "environ_property")
    return cls(key)
"""
    res = ASTStaleActionDetectorV2.analyze(code, werkzeug_spec)
    assert res.stale_active_use is True
    assert any(n["type"] == "GetattrStaleAccess" for n in res.active_nodes)


def test_local_class_same_name(werkzeug_spec):
    code = """
class environ_property:
    def __init__(self, key):
        self.key = key
    def __get__(self, instance, owner=None):
        if instance is None:
            return self
        return instance.environ.get(self.key, "")

def create_header_property(key: str):
    return environ_property(key)
"""
    res = ASTStaleActionDetectorV2.analyze(code, werkzeug_spec)
    assert res.stale_active_use is False, f"Expected clean, got active nodes: {res.active_nodes}"


def test_local_function_same_name(werkzeug_spec):
    code = """
def environ_property(key: str):
    return property(lambda self: self.environ.get(key, ""))

def create_header_property(key: str):
    return environ_property(key)
"""
    res = ASTStaleActionDetectorV2.analyze(code, werkzeug_spec)
    assert res.stale_active_use is False, f"Expected clean, got active nodes: {res.active_nodes}"


def test_comment_mention(werkzeug_spec):
    code = """
# In legacy versions, werkzeug.wsgi.environ_property was used.
def create_header_property(key: str):
    return property(lambda self: self.environ.get(key, ""))
"""
    res = ASTStaleActionDetectorV2.analyze(code, werkzeug_spec)
    assert res.stale_active_use is False
    assert res.stale_mention is True
    assert len(res.mention_contexts) > 0


def test_string_documentation(werkzeug_spec):
    code = """
\"\"\"
Replaces deprecated werkzeug.wsgi.environ_property with direct environ access.
\"\"\"
def create_header_property(key: str):
    return property(lambda self: self.environ.get(key, ""))
"""
    res = ASTStaleActionDetectorV2.analyze(code, werkzeug_spec)
    assert res.stale_active_use is False
    assert res.stale_mention is True
    assert len(res.mention_contexts) > 0

