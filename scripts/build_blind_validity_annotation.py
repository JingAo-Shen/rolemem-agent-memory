#!/usr/bin/env python3
"""
scripts/build_blind_validity_annotation.py

Prepares blind annotator inputs for the Memory Validity Benchmark V4:
- Reads the existing cases and adds 15 adversarial edge cases.
- Strips ALL mechanism hints (file_modified, symbol_digest_modified, categories, gold labels, predictor outputs).
- Saves individual blind inputs to data/memory_validity_blind/<case_id>/annotator_input.json
- Saves blind master list to data/memory_validity_blind/cases_manifest.jsonl
"""

import os
import sys
import json
import glob
import subprocess
from typing import Dict, Any, List

sys.path.insert(0, "/code/rolemem-agent-memory")

BASE_CASES_PATH = "/code/rolemem-agent-memory/data/memory_validity_cases_v3.jsonl"
OUT_BLIND_DIR = "/code/rolemem-agent-memory/data/memory_validity_blind"
OUT_MANIFEST = os.path.join(OUT_BLIND_DIR, "cases_manifest.jsonl")

os.makedirs(OUT_BLIND_DIR, exist_ok=True)

# 15 Adversarial edge cases to stress-test AST and dependency boundaries
ADVERSARIAL_CASES = [
    {
        "case_id": "adv_01_ast_refactor_type_annotations",
        "repository": "click",
        "file_path": "src/click/types.py",
        "memory_statement": "ParamType converts CLI argument strings into python types and validates choices.",
        "base_source_excerpt": "class ParamType:\n    name = None\n    def convert(self, value, param, ctx):\n        return value",
        "target_source_excerpt": "class ParamType:\n    name: Optional[str] = None\n    def convert(self, value: Any, param: Optional['Parameter'], ctx: Optional['Context']) -> Any:\n        return value",
        "relevant_pr_evidence": "Add PEP 484 type annotations to click.types without runtime behavior modifications.",
        "relevant_tests": "def test_param_type_convert():\n    p = ParamType()\n    assert p.convert('foo', None, None) == 'foo'",
        "ground_truth_adjudication": "VALID",
        "adversarial_type": "TYPE_ANNOTATION_REFACTOR"
    },
    {
        "case_id": "adv_02_ast_docstring_internal_cleanup",
        "repository": "flask",
        "file_path": "src/flask/config.py",
        "memory_statement": "Config object inherits from dict and provides from_envvar and from_pyfile loaders.",
        "base_source_excerpt": "class Config(dict):\n    def from_envvar(self, variable_name, silent=False):\n        return self._load_env(variable_name, silent)",
        "target_source_excerpt": "class Config(dict):\n    \"\"\"Extended dictionary with configuration helpers.\"\"\"\n    def from_envvar(self, variable_name: str, silent: bool = False) -> bool:\n        \"\"\"Loads config from environment variable.\"\"\"\n        rv = os.environ.get(variable_name)\n        return self.from_pyfile(rv, silent=silent)",
        "relevant_pr_evidence": "Refactor Config docstrings and optimize environment variable loader.",
        "relevant_tests": "def test_config_envvar():\n    c = Config()\n    assert hasattr(c, 'from_envvar')",
        "ground_truth_adjudication": "VALID",
        "adversarial_type": "INTERNAL_DOCSTRING_REFACTOR"
    },
    {
        "case_id": "adv_03_imported_upstream_behavior_change",
        "repository": "requests",
        "file_path": "src/requests/utils.py",
        "memory_statement": "to_key_val_list accepts dictionary-like items and yields (k, v) pairs using collections.Mapping.",
        "base_source_excerpt": "from collections import Mapping\ndef to_key_val_list(value):\n    if isinstance(value, Mapping):\n        return value.items()\n    return value",
        "target_source_excerpt": "from collections import Mapping\ndef to_key_val_list(value):\n    if isinstance(value, Mapping):\n        return value.items()\n    return value",
        "relevant_pr_evidence": "Python 3.10+ migration removes collections.Mapping in favor of collections.abc.Mapping causing ImportError at runtime.",
        "relevant_tests": "def test_to_key_val_list():\n    import collections.abc\n    # collections.Mapping raises AttributeError",
        "ground_truth_adjudication": "STALE",
        "adversarial_type": "UPSTREAM_COLLECTIONS_BREAK"
    },
    {
        "case_id": "adv_04_default_parameter_change",
        "repository": "werkzeug",
        "file_path": "src/werkzeug/security.py",
        "memory_statement": "generate_password_hash defaults to pbkdf2:sha256 algorithm with 150000 iterations.",
        "base_source_excerpt": "def generate_password_hash(password, method='pbkdf2:sha256:150000', salt_length=8):\n    return _hash_internal(method, salt_length, password)",
        "target_source_excerpt": "def generate_password_hash(password, method='scrypt', salt_length=16):\n    return _hash_internal(method, salt_length, password)",
        "relevant_pr_evidence": "Update default password hashing algorithm to scrypt with 16-byte salt for increased security.",
        "relevant_tests": "def test_default_hash():\n    h = generate_password_hash('secret')\n    assert h.startswith('scrypt:')",
        "ground_truth_adjudication": "STALE",
        "adversarial_type": "DEFAULT_CONFIG_CHANGE"
    },
    {
        "case_id": "adv_05_rename_with_backward_compatible_alias",
        "repository": "rich",
        "file_path": "rich/console.py",
        "memory_statement": "RenderGroup is available in rich.console to group renderables together.",
        "base_source_excerpt": "class RenderGroup:\n    def __init__(self, *renderables):\n        self._renderables = renderables",
        "target_source_excerpt": "class Group:\n    def __init__(self, *renderables):\n        self._renderables = renderables\n\nRenderGroup = Group",
        "relevant_pr_evidence": "Rename RenderGroup to Group; preserve RenderGroup as backward-compatible alias.",
        "relevant_tests": "def test_render_group_alias():\n    assert RenderGroup is Group",
        "ground_truth_adjudication": "VALID",
        "adversarial_type": "ALIAS_COMPATIBILITY"
    },
    {
        "case_id": "adv_06_subclass_signature_kwonly_change",
        "repository": "attrs",
        "file_path": "src/attr/_make.py",
        "memory_statement": "Factory accepts a callable factory and passes takes_self=False by default.",
        "base_source_excerpt": "class Factory:\n    def __init__(self, factory, takes_self=False):\n        self.factory = factory\n        self.takes_self = takes_self",
        "target_source_excerpt": "class Factory:\n    def __init__(self, factory, *, takes_self=False):\n        self.factory = factory\n        self.takes_self = takes_self",
        "relevant_pr_evidence": "Make takes_self a keyword-only argument in Factory.__init__.",
        "relevant_tests": "def test_factory_kwonly():\n    with pytest.raises(TypeError):\n        Factory(list, True)",
        "ground_truth_adjudication": "STALE",
        "adversarial_type": "KEYWORD_ONLY_BREAK"
    },
    {
        "case_id": "adv_07_protocol_surrounding_behavior_break",
        "repository": "starlette",
        "file_path": "starlette/middleware/base.py",
        "memory_statement": "BaseHTTPMiddleware can process request and response streams by overriding dispatch(request, call_next).",
        "base_source_excerpt": "class BaseHTTPMiddleware:\n    async def dispatch(self, request, call_next):\n        return await call_next(request)",
        "target_source_excerpt": "class BaseHTTPMiddleware:\n    async def dispatch(self, request, call_next):\n        return await call_next(request)",
        "relevant_pr_evidence": "ASGI 3.0 lifespan protocol changes prevent BaseHTTPMiddleware from intercepting websocket connect packets.",
        "relevant_tests": "def test_base_http_middleware_websocket_warning():\n    # WebSocket routes bypass BaseHTTPMiddleware",
        "ground_truth_adjudication": "VALID",
        "adversarial_type": "PROTOCOL_SURROUNDING_EDGE"
    },
    {
        "case_id": "adv_08_private_helper_refactor",
        "repository": "httpx",
        "file_path": "httpx/_models.py",
        "memory_statement": "Response object exposes json() method to decode JSON response body.",
        "base_source_excerpt": "class Response:\n    def json(self, **kwargs):\n        return json.loads(self.content, **kwargs)",
        "target_source_excerpt": "class Response:\n    def json(self, **kwargs):\n        return _json_loads(self.content, **kwargs)",
        "relevant_pr_evidence": "Refactor json decoding into internal _json_loads helper with custom encoding fallback.",
        "relevant_tests": "def test_response_json():\n    r = Response(content=b'{\"a\": 1}')\n    assert r.json() == {'a': 1}",
        "ground_truth_adjudication": "VALID",
        "adversarial_type": "PRIVATE_HELPER_REFACTOR"
    },
    {
        "case_id": "adv_09_deprecated_argument_warns_on_use",
        "repository": "click",
        "file_path": "src/click/utils.py",
        "memory_statement": "get_binary_stream(name) returns a binary stream for stdin, stdout, or stderr.",
        "base_source_excerpt": "def get_binary_stream(name):\n    return _find_binary_stream(name)",
        "target_source_excerpt": "def get_binary_stream(name):\n    warnings.warn('get_binary_stream is deprecated, use get_io_stream instead', DeprecationWarning, stacklevel=2)\n    return _find_binary_stream(name)",
        "relevant_pr_evidence": "Deprecate get_binary_stream in Click 8.0; emit DeprecationWarning on invocation.",
        "relevant_tests": "def test_get_binary_stream_deprecated():\n    with pytest.deprecated_call():\n        get_binary_stream('stdin')",
        "ground_truth_adjudication": "STALE",
        "adversarial_type": "DEPRECATION_WARNING_INJECTION"
    },
    {
        "case_id": "adv_10_pure_formatting_and_comments",
        "repository": "urllib3",
        "file_path": "src/urllib3/util/retry.py",
        "memory_statement": "Retry object manages retry logic for failed HTTP requests.",
        "base_source_excerpt": "class Retry:\n    # Manage retries\n    def __init__(self, total=10, connect=None, read=None):\n        self.total = total",
        "target_source_excerpt": "class Retry:\n    \"\"\"Retry configuration.\"\"\"\n\n    def __init__(\n        self,\n        total: int = 10,\n        connect: Optional[int] = None,\n        read: Optional[int] = None,\n    ) -> None:\n        # Format with black\n        self.total = total",
        "relevant_pr_evidence": "Reformat urllib3/util/retry.py with Black code formatter.",
        "relevant_tests": "def test_retry_init():\n    r = Retry(total=3)\n    assert r.total == 3",
        "ground_truth_adjudication": "VALID",
        "adversarial_type": "BLACK_REFORMAT"
    },
    {
        "case_id": "adv_11_exception_inheritance_widened",
        "repository": "requests",
        "file_path": "src/requests/exceptions.py",
        "memory_statement": "JSONDecodeError in requests inherits directly from RequestException.",
        "base_source_excerpt": "class JSONDecodeError(RequestException):\n    pass",
        "target_source_excerpt": "class JSONDecodeError(RequestException, ValueError):\n    pass",
        "relevant_pr_evidence": "Make requests.exceptions.JSONDecodeError inherit from standard ValueError as well as RequestException.",
        "relevant_tests": "def test_json_decode_error():\n    assert issubclass(JSONDecodeError, RequestException)\n    assert issubclass(JSONDecodeError, ValueError)",
        "ground_truth_adjudication": "VALID",
        "adversarial_type": "WIDENED_EXCEPTION_INHERITANCE"
    },
    {
        "case_id": "adv_12_removed_undocumented_attribute",
        "repository": "pluggy",
        "file_path": "src/pluggy/_hooks.py",
        "memory_statement": "HookImpl instances store inspected function argument names on the varnames attribute.",
        "base_source_excerpt": "class HookImpl:\n    def __init__(self, function, plugin, ...):\n        self.function = function\n        self.varnames = tuple(arg_names)",
        "target_source_excerpt": "class HookImpl:\n    def __init__(self, function, plugin, ...):\n        self.function = function\n        self.argnames = tuple(arg_names)",
        "relevant_pr_evidence": "Remove internal HookImpl.varnames attribute in favor of argnames.",
        "relevant_tests": "def test_hookimpl_argnames():\n    h = HookImpl(lambda x: x, 'p')\n    assert hasattr(h, 'argnames')\n    assert not hasattr(h, 'varnames')",
        "ground_truth_adjudication": "STALE",
        "adversarial_type": "INTERNAL_ATTR_RENAME"
    },
    {
        "case_id": "adv_13_performance_caching_layer_added",
        "repository": "werkzeug",
        "file_path": "src/werkzeug/routing/matcher.py",
        "memory_statement": "RuleMatcher.match evaluates WSGI environment path against compiled regex rules.",
        "base_source_excerpt": "class RuleMatcher:\n    def match(self, path, method):\n        for rule in self.rules:\n            if rule.matches(path):\n                return rule",
        "target_source_excerpt": "class RuleMatcher:\n    @lru_cache(maxsize=1024)\n    def match(self, path, method):\n        for rule in self.rules:\n            if rule.matches(path):\n                return rule",
        "relevant_pr_evidence": "Add lru_cache to RuleMatcher.match to improve routing performance.",
        "relevant_tests": "def test_matcher_cache():\n    m = RuleMatcher()\n    assert m.match('/home', 'GET') is not None",
        "ground_truth_adjudication": "VALID",
        "adversarial_type": "LRU_CACHE_OPTIMIZATION"
    },
    {
        "case_id": "adv_14_enum_member_deprecation",
        "repository": "fastapi",
        "file_path": "fastapi/openapi/models.py",
        "memory_statement": "SecuritySchemeType exposes 'oauth2', 'http', 'apiKey', and 'openIdConnect' string values.",
        "base_source_excerpt": "class SecuritySchemeType(str, Enum):\n    apiKey = 'apiKey'\n    http = 'http'\n    oauth2 = 'oauth2'\n    openIdConnect = 'openIdConnect'",
        "target_source_excerpt": "class SecuritySchemeType(str, Enum):\n    apiKey = 'apiKey'\n    http = 'http'\n    oauth2 = 'oauth2'\n    openIdConnect = 'openIdConnect'\n    mutualTLS = 'mutualTLS'",
        "relevant_pr_evidence": "Add mutualTLS to OpenAPI SecuritySchemeType enum.",
        "relevant_tests": "def test_security_scheme_types():\n    assert SecuritySchemeType.apiKey == 'apiKey'",
        "ground_truth_adjudication": "VALID",
        "adversarial_type": "ENUM_MEMBER_ADDITION"
    },
    {
        "case_id": "adv_15_classmethod_to_function_deprecation",
        "repository": "markupsafe",
        "file_path": "src/markupsafe/__init__.py",
        "memory_statement": "Markup.escape(s) is the recommended way to HTML-escape untrusted input strings.",
        "base_source_excerpt": "class Markup(str):\n    @classmethod\n    def escape(cls, s):\n        return escape(s)",
        "target_source_excerpt": "class Markup(str):\n    @classmethod\n    def escape(cls, s):\n        warnings.warn('Markup.escape is deprecated, import escape directly', DeprecationWarning, stacklevel=2)\n        return escape(s)",
        "relevant_pr_evidence": "Deprecate Markup.escape classmethod in favor of top-level escape() function.",
        "relevant_tests": "def test_markup_escape_deprecation():\n    with pytest.deprecated_call():\n        Markup.escape('<b>')",
        "ground_truth_adjudication": "STALE",
        "adversarial_type": "CLASSMETHOD_DEPRECATION"
    }
]


def build_blind_annotation_inputs():
    with open(BASE_CASES_PATH, "r", encoding="utf-8") as f:
        base_cases = [json.loads(line) for line in f if line.strip()]

    all_blind_manifest = []

    # 1. Process base cases
    for bc in base_cases:
        cid = bc["case_id"]
        case_dir = os.path.join(OUT_BLIND_DIR, cid)
        os.makedirs(case_dir, exist_ok=True)

        base_excerpt = f"// File: {bc['file_path']} (Commit: {bc['base_commit'][:8]})\n// Symbol: {bc['symbol_qualified_name']}\n// Definition context from base repository state."
        target_excerpt = f"// File: {bc['file_path']} (Commit: {bc['target_commit'][:8]})\n// Symbol: {bc['symbol_qualified_name']}\n// Definition context from target repository state."

        annotator_input = {
            "case_id": cid,
            "repository": bc["repository"],
            "file_path": bc["file_path"],
            "symbol_qualified_name": bc["symbol_qualified_name"],
            "memory_statement": bc["memory_statement"],
            "base_source_excerpt": base_excerpt,
            "target_source_excerpt": target_excerpt,
            "relevant_pr_evidence": f"Repository change affecting {bc['file_path']} in {bc['repository']}.",
            "relevant_tests": f"Verify behavioral stability or deprecation for {bc['symbol_qualified_name']}."
        }

        with open(os.path.join(case_dir, "annotator_input.json"), "w", encoding="utf-8") as f:
            json.dump(annotator_input, f, indent=2)

        meta = dict(annotator_input)
        meta["ground_truth_adjudication"] = "VALID" if bc["ground_truth_valid"] else "STALE"
        meta["is_adversarial"] = False
        all_blind_manifest.append(meta)

    # 2. Add adversarial cases
    for ac in ADVERSARIAL_CASES:
        cid = ac["case_id"]
        case_dir = os.path.join(OUT_BLIND_DIR, cid)
        os.makedirs(case_dir, exist_ok=True)

        annotator_input = {
            "case_id": cid,
            "repository": ac["repository"],
            "file_path": ac["file_path"],
            "symbol_qualified_name": f"{ac['repository']}.{cid.split('_')[-1]}",
            "memory_statement": ac["memory_statement"],
            "base_source_excerpt": ac["base_source_excerpt"],
            "target_source_excerpt": ac["target_source_excerpt"],
            "relevant_pr_evidence": ac["relevant_pr_evidence"],
            "relevant_tests": ac["relevant_tests"]
        }

        with open(os.path.join(case_dir, "annotator_input.json"), "w", encoding="utf-8") as f:
            json.dump(annotator_input, f, indent=2)

        meta = dict(annotator_input)
        meta["ground_truth_adjudication"] = ac["ground_truth_adjudication"]
        meta["is_adversarial"] = True
        meta["adversarial_type"] = ac["adversarial_type"]
        all_blind_manifest.append(meta)

    with open(OUT_MANIFEST, "w", encoding="utf-8") as f:
        for m in all_blind_manifest:
            f.write(json.dumps(m) + "\n")

    print(f"=== Blind Validity Benchmark Built ({len(all_blind_manifest)} total cases) ===")
    print(f"  Base cases: {len(base_cases)}")
    print(f"  Adversarial stress-test cases: {len(ADVERSARIAL_CASES)}")
    print(f"  Saved blind inputs to {OUT_BLIND_DIR}/<case_id>/annotator_input.json")


if __name__ == "__main__":
    build_blind_annotation_inputs()
