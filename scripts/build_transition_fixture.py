"""
DEPRECATED — UNIT TEST ONLY.
DO NOT USE FOR BENCHMARK CONSTRUCTION.
Official benchmark fixtures are built by scripts/build_real_repo_fixture.py directly from Git checkout.
"""
import warnings
warnings.warn(
    "build_transition_fixture.py uses synthetic templates and is DEPRECATED for benchmark construction. "
    "Use scripts/build_real_repo_fixture.py instead.",
    UserWarning,
    stacklevel=2
)

import os
import sys
import json
import shutil
import argparse
from typing import Dict, Any, List

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


FIXTURE_TEMPLATES = {
    "trans_gold_werkzeug_01_cached_property": {
        "before_files": {
            "src/werkzeug/__init__.py": "# Werkzeug package",
            "src/werkzeug/utils.py": """# Legacy Werkzeug utils
def invalidate_cached_property(obj, name):
    \"\"\"Legacy property invalidation helper.\"\"\"
    obj.__dict__.pop(name, None)
""",
            "src/werkzeug/urls.py": """# Legacy Werkzeug URLs
class Href:
    def __init__(self, base):
        self.base = base
"""
        },
        "after_files": {
            "src/werkzeug/__init__.py": "# Werkzeug package",
            "src/werkzeug/utils.py": """# Modern Werkzeug utils (post PR #2085)
import warnings

def invalidate_cached_property(obj, name):
    warnings.warn(
        "'invalidate_cached_property' is deprecated and will be removed in Werkzeug 2.1. "
        "Use 'del obj.name' or 'delattr(obj, name)' instead.",
        DeprecationWarning,
        stacklevel=2
    )
    obj.__dict__.pop(name, None)
""",
            "src/werkzeug/urls.py": """# Modern Werkzeug URLs (post PR #2085)
import warnings

class Href:
    def __init__(self, base):
        warnings.warn(
            "'Href' is deprecated and will be removed in Werkzeug 2.1. Use 'werkzeug.routing' instead.",
            DeprecationWarning,
            stacklevel=2
        )
        self.base = base
"""
        },
        "hidden_test": """import pytest
import warnings
from property_helper import reset_cached_attribute

class MockResource:
    def __init__(self):
        self._computed = 0

    @property
    def data(self):
        self._computed += 1
        return 42

def test_reset_cached_attribute_success():
    res = MockResource()
    # Cache a value
    res.__dict__["data"] = 999
    assert res.__dict__["data"] == 999

    with warnings.catch_warnings(record=True) as recorded:
        warnings.simplefilter("always")
        reset_cached_attribute(res, "data")
        assert "data" not in res.__dict__

        # Assert no DeprecationWarning from legacy invalidate_cached_property
        dep_warnings = [w for w in recorded if issubclass(w.category, DeprecationWarning)]
        assert len(dep_warnings) == 0, f"Encountered deprecated call: {dep_warnings}"
"""
    },
    "trans_gold_werkzeug_02_environ_properties": {
        "before_files": {
            "src/werkzeug/__init__.py": "# Werkzeug package",
            "src/werkzeug/sansio/__init__.py": "",
            "src/werkzeug/sansio/utils.py": """# Legacy sansio utils
class environ_property:
    def __init__(self, name, default=None):
        self.name = name
        self.default = default
    def __get__(self, obj, type=None):
        if obj is None:
            return self
        return obj.environ.get(self.name, self.default)
"""
        },
        "after_files": {
            "src/werkzeug/__init__.py": "# Werkzeug package",
            "src/werkzeug/sansio/__init__.py": "",
            "src/werkzeug/sansio/utils.py": """# Modern sansio utils (post PR #3276)
import warnings

class environ_property:
    def __init__(self, name, default=None):
        warnings.warn(
            "'environ_property' is deprecated and will be removed in Werkzeug 3.2. Access environ directly.",
            DeprecationWarning,
            stacklevel=2
        )
        self.name = name
        self.default = default
    def __get__(self, obj, type=None):
        return obj.environ.get(self.name, self.default)
"""
        },
        "hidden_test": """import pytest
import warnings
from wsgi_helper import extract_wsgi_header

def test_extract_wsgi_header():
    environ = {
        "HTTP_HOST": "example.com:8080",
        "HTTP_ACCEPT": "application/json",
        "PATH_INFO": "/api/v1"
    }
    with warnings.catch_warnings(record=True) as recorded:
        warnings.simplefilter("always")
        host = extract_wsgi_header(environ, "host")
        assert host == "example.com:8080"
        accept = extract_wsgi_header(environ, "accept")
        assert accept == "application/json"
        
        dep_warnings = [w for w in recorded if issubclass(w.category, DeprecationWarning)]
        assert len(dep_warnings) == 0, f"Encountered deprecated call: {dep_warnings}"
"""
    },
    "trans_gold_flask_01_context_stack_removal": {
        "before_files": {
            "src/flask/__init__.py": "from .globals import _app_ctx_stack\nfrom .app import Flask",
            "src/flask/globals.py": """class _ContextStack:
    def __init__(self):
        self._stack = []
    def push(self, obj):
        self._stack.append(obj)
    def pop(self):
        return self._stack.pop() if self._stack else None
    @property
    def top(self):
        return self._stack[-1] if self._stack else None

_app_ctx_stack = _ContextStack()
""",
            "src/flask/app.py": """from .globals import _app_ctx_stack

class AppContext:
    def __init__(self, app):
        self.app = app
    def push(self):
        _app_ctx_stack.push(self)
    def pop(self):
        _app_ctx_stack.pop()

class Flask:
    def __init__(self, name):
        self.name = name
    def app_context(self):
        return AppContext(self)
"""
        },
        "after_files": {
            "src/flask/__init__.py": "from .globals import _app_ctx_stack\nfrom .app import Flask",
            "src/flask/globals.py": """class _ModernContextStack:
    def __init__(self):
        self._stack = []
    @property
    def top(self):
        return self._stack[-1] if self._stack else None
    def push(self, obj):
        raise AttributeError("'_app_ctx_stack.push()' was removed in Flask 2.4 (PR #4995). Call 'ctx.push()' directly.")
    def pop(self):
        raise AttributeError("'_app_ctx_stack.pop()' was removed in Flask 2.4 (PR #4995). Call 'ctx.pop()' directly.")

_app_ctx_stack = _ModernContextStack()
""",
            "src/flask/app.py": """from .globals import _app_ctx_stack

class AppContext:
    def __init__(self, app):
        self.app = app
    def push(self):
        _app_ctx_stack._stack.append(self)
        return self
    def pop(self):
        return _app_ctx_stack._stack.pop() if _app_ctx_stack._stack else None

class Flask:
    def __init__(self, name):
        self.name = name
    def app_context(self):
        return AppContext(self)
"""
        },
        "hidden_test": """import pytest
from flask import Flask
from ctx_manager import activate_application_context

def test_activate_application_context():
    app = Flask("test_isolated_app")
    ctx = activate_application_context(app)
    from flask.globals import _app_ctx_stack
    assert _app_ctx_stack.top is not None
    assert _app_ctx_stack.top.app.name == "test_isolated_app"
    ctx.pop()
"""
    },
    "trans_gold_flask_02_should_ignore_error": {
        "before_files": {
            "src/flask/__init__.py": "from .app import Flask",
            "src/flask/app.py": """class Flask:
    def __init__(self, name):
        self.name = name
        self.ignored_errors = set()
    def should_ignore_error(self, error):
        return type(error) in self.ignored_errors
    def handle_exception(self, e):
        if self.should_ignore_error(e):
            return "IGNORED"
        raise e
"""
        },
        "after_files": {
            "src/flask/__init__.py": "from .app import Flask",
            "src/flask/app.py": """import warnings

class Flask:
    def __init__(self, name):
        self.name = name
        self.error_handlers = {}
    def should_ignore_error(self, error):
        warnings.warn(
            "'should_ignore_error' is deprecated and will be removed in Flask 3.2. Register explicit error handlers instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return False
    def errorhandler(self, exc_class):
        def decorator(fn):
            self.error_handlers[exc_class] = fn
            return fn
        return decorator
    def handle_exception(self, e):
        handler = self.error_handlers.get(type(e))
        if handler:
            return handler(e)
        raise e
"""
        },
        "hidden_test": """import pytest
import warnings
from flask import Flask
from error_policy import configure_error_policy

class CustomTransientError(Exception):
    pass

def test_error_policy():
    app = Flask("err_app")
    with warnings.catch_warnings(record=True) as recorded:
        warnings.simplefilter("always")
        configure_error_policy(app, CustomTransientError)
        res = app.handle_exception(CustomTransientError("db glitch"))
        assert res is not None

        dep_warnings = [w for w in recorded if issubclass(w.category, DeprecationWarning)]
        assert len(dep_warnings) == 0, f"Encountered deprecated call: {dep_warnings}"
"""
    },
    "trans_gold_urllib3_01_retry_allowed_methods": {
        "before_files": {
            "src/urllib3/__init__.py": "",
            "src/urllib3/util/__init__.py": "",
            "src/urllib3/util/retry.py": """class Retry:
    DEFAULT_METHOD_WHITELIST = frozenset(['HEAD', 'GET', 'PUT', 'DELETE', 'OPTIONS', 'TRACE'])
    def __init__(self, total=3, method_whitelist=None):
        self.total = total
        self.method_whitelist = frozenset(method_whitelist) if method_whitelist is not None else self.DEFAULT_METHOD_WHITELIST
"""
        },
        "after_files": {
            "src/urllib3/__init__.py": "",
            "src/urllib3/util/__init__.py": "",
            "src/urllib3/util/retry.py": """import warnings

class Retry:
    DEFAULT_ALLOWED_METHODS = frozenset(['HEAD', 'GET', 'PUT', 'DELETE', 'OPTIONS', 'TRACE'])
    def __init__(self, total=3, allowed_methods=None, method_whitelist=None):
        self.total = total
        if method_whitelist is not None:
            warnings.warn(
                "Using 'method_whitelist' is deprecated and will be removed in urllib3 v2.0. Use 'allowed_methods' instead.",
                DeprecationWarning,
                stacklevel=2
            )
            allowed_methods = method_whitelist
        self.allowed_methods = frozenset(allowed_methods) if allowed_methods is not None else self.DEFAULT_ALLOWED_METHODS
"""
        },
        "hidden_test": """import pytest
import warnings
from retry_factory import build_custom_retry

def test_build_custom_retry():
    with warnings.catch_warnings(record=True) as recorded:
        warnings.simplefilter("always")
        r = build_custom_retry(["GET", "POST"])
        assert r.allowed_methods == frozenset(["GET", "POST"])

        dep_warnings = [w for w in recorded if issubclass(w.category, DeprecationWarning)]
        assert len(dep_warnings) == 0, f"Encountered deprecated call: {dep_warnings}"
"""
    },
    "trans_gold_urllib3_02_empty_allowed_methods": {
        "before_files": {
            "src/urllib3/__init__.py": "",
            "src/urllib3/util/__init__.py": "",
            "src/urllib3/util/retry.py": """class Retry:
    def __init__(self, allowed_methods=None):
        if allowed_methods is not None and len(allowed_methods) == 0:
            self.allowed_methods = False  # Retry all verbs
        else:
            self.allowed_methods = allowed_methods
"""
        },
        "after_files": {
            "src/urllib3/__init__.py": "",
            "src/urllib3/util/__init__.py": "",
            "src/urllib3/util/retry.py": """import warnings

class Retry:
    def __init__(self, allowed_methods=None):
        if allowed_methods is not None and hasattr(allowed_methods, '__len__') and len(allowed_methods) == 0:
            warnings.warn(
                "Passing an empty collection for 'allowed_methods' is deprecated. Pass None or False instead.",
                DeprecationWarning,
                stacklevel=2
            )
            self.allowed_methods = False
        else:
            self.allowed_methods = allowed_methods
"""
        },
        "hidden_test": """import pytest
import warnings
from retry_factory import create_all_verbs_retry

def test_create_all_verbs_retry():
    with warnings.catch_warnings(record=True) as recorded:
        warnings.simplefilter("always")
        r = create_all_verbs_retry()
        assert r.allowed_methods is None or r.allowed_methods is False

        dep_warnings = [w for w in recorded if issubclass(w.category, DeprecationWarning)]
        assert len(dep_warnings) == 0, f"Encountered deprecated call: {dep_warnings}"
"""
    },
    "trans_gold_click_01_option_parser": {
        "before_files": {
            "src/click/__init__.py": "",
            "src/click/parser.py": """class OptionParser:
    def __init__(self):
        self._options = {}
    def add_option(self, opts, dest):
        for o in opts:
            self._options[o] = dest
    def parse_args(self, args):
        res = {}
        i = 0
        while i < len(args):
            if args[i] in self._options:
                res[self._options[args[i]]] = args[i+1]
                i += 2
            else:
                i += 1
        return res
"""
        },
        "after_files": {
            "src/click/__init__.py": "",
            "src/click/parser.py": """import warnings

class OptionParser:
    def __init__(self):
        warnings.warn(
            "'click.parser.OptionParser' is deprecated and will be removed in Click 9.0. Use modern Command parsing.",
            DeprecationWarning,
            stacklevel=2
        )
        self._options = {}
    def add_option(self, opts, dest):
        for o in opts:
            self._options[o] = dest
    def parse_args(self, args):
        res = {}
        i = 0
        while i < len(args):
            if args[i] in self._options:
                res[self._options[args[i]]] = args[i+1]
                i += 2
            else:
                i += 1
        return res
"""
        },
        "hidden_test": """import pytest
import warnings
import click
from cli_helper import parse_command_args

def test_parse_command_args():
    @click.command()
    @click.option("--output", "-o")
    def sample_cmd(output):
        pass

    with warnings.catch_warnings(record=True) as recorded:
        warnings.simplefilter("always")
        res = parse_command_args(sample_cmd, ["--output", "results.csv"])
        assert res.get("output") == "results.csv"

        dep_warnings = [w for w in recorded if issubclass(w.category, DeprecationWarning)]
        assert len(dep_warnings) == 0, f"Encountered deprecated call: {dep_warnings}"
"""
    },
    "trans_gold_click_02_isolated_filesystem": {
        "before_files": {
            "src/click/__init__.py": "",
            "src/click/testing.py": """import tempfile
import contextlib
import os

class CliRunner:
    @contextlib.contextmanager
    def isolated_filesystem(self):
        with tempfile.TemporaryDirectory() as d:
            orig = os.getcwd()
            os.chdir(d)
            try:
                yield d
            finally:
                os.chdir(orig)
"""
        },
        "after_files": {
            "src/click/__init__.py": "",
            "src/click/testing.py": """import tempfile
import contextlib
import os
import warnings

class CliRunner:
    @contextlib.contextmanager
    def isolated_filesystem(self):
        warnings.warn(
            "'CliRunner.isolated_filesystem' is deprecated due to lack of thread safety. Use tempfile.TemporaryDirectory instead.",
            DeprecationWarning,
            stacklevel=2
        )
        with tempfile.TemporaryDirectory() as d:
            orig = os.getcwd()
            os.chdir(d)
            try:
                yield d
            finally:
                os.chdir(orig)
"""
        },
        "hidden_test": """import pytest
import warnings
import os
from test_isolation import run_in_isolated_dir

def test_run_in_isolated_dir():
    orig_dir = os.getcwd()
    with warnings.catch_warnings(record=True) as recorded:
        warnings.simplefilter("always")
        executed_dir = run_in_isolated_dir(lambda: os.getcwd())
        assert executed_dir != orig_dir
        assert os.getcwd() == orig_dir

        dep_warnings = [w for w in recorded if issubclass(w.category, DeprecationWarning)]
        assert len(dep_warnings) == 0, f"Encountered deprecated call: {dep_warnings}"
"""
    },
    "trans_gold_requests_01_tls_context_adapter": {
        "before_files": {
            "src/requests/__init__.py": "",
            "src/requests/adapters.py": """class HTTPAdapter:
    def __init__(self):
        self.connections = {}
    def _get_connection(self, url, proxies=None):
        return f"Conn({url})"
    def send(self, request):
        conn = self._get_connection(request.url)
        return f"Response({conn})"
"""
        },
        "after_files": {
            "src/requests/__init__.py": "",
            "src/requests/adapters.py": """import warnings

class HTTPAdapter:
    def __init__(self):
        self.connections = {}
    def _get_connection(self, url, proxies=None):
        warnings.warn(
            "'_get_connection' is deprecated in requests 2.32.0 (PR #6710). Use 'get_connection_with_tls_context' instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return f"Conn({url})"
    def get_connection_with_tls_context(self, request, verify=True, cert=None):
        return f"ConnTLS({request.url}, verify={verify})"
    def send(self, request, verify=True, cert=None):
        conn = self.get_connection_with_tls_context(request, verify=verify, cert=cert)
        return f"Response({conn})"
"""
        },
        "hidden_test": """import pytest
import warnings
from requests.adapters import HTTPAdapter

class DummyReq:
    def __init__(self, url):
        self.url = url

def test_get_adapter_connection():
    from adapter_helper import get_adapter_connection
    adapter = HTTPAdapter()
    req = DummyReq("https://api.github.com")

    with warnings.catch_warnings(record=True) as recorded:
        warnings.simplefilter("always")
        conn = get_adapter_connection(adapter, req, verify=True)
        assert conn is not None
        assert "ConnTLS" in str(conn)

        dep_warnings = [w for w in recorded if issubclass(w.category, DeprecationWarning)]
        assert len(dep_warnings) == 0, f"Encountered deprecated call: {dep_warnings}"
"""
    },
    "trans_gold_requests_02_pool_key_overrides": {
        "before_files": {
            "src/requests/__init__.py": "",
            "src/requests/adapters.py": """class HTTPAdapter:
    def __init__(self, pool_connections=10, pool_maxsize=10):
        self._pool_connections = pool_connections
        self._pool_maxsize = pool_maxsize
        self.poolmanager = None
        self.init_poolmanager(pool_connections, pool_maxsize)
    def init_poolmanager(self, connections, maxsize, **kwargs):
        # Regressed in #6655: ignored kwargs
        self.poolmanager = {"connections": connections, "maxsize": maxsize}
"""
        },
        "after_files": {
            "src/requests/__init__.py": "",
            "src/requests/adapters.py": """class HTTPAdapter:
    def __init__(self, pool_connections=10, pool_maxsize=10, **kwargs):
        self._pool_connections = pool_connections
        self._pool_maxsize = pool_maxsize
        self.poolmanager = None
        self.init_poolmanager(pool_connections, pool_maxsize, **kwargs)
    def init_poolmanager(self, connections, maxsize, **kwargs):
        # Resolved in #6716: properly incorporates pool key kwargs
        self.poolmanager = {"connections": connections, "maxsize": maxsize, **kwargs}
"""
        },
        "hidden_test": """import pytest
from pool_config import build_custom_adapter_pool

def test_build_custom_adapter_pool():
    adapter = build_custom_adapter_pool(connections=20, maxsize=20, block=True)
    assert adapter.poolmanager["connections"] == 20
    assert adapter.poolmanager["maxsize"] == 20
    assert adapter.poolmanager.get("block") is True
"""
    }
}


def build_fixture(transition_id: str, candidate_metadata: Dict[str, Any], output_root: str = "fixtures") -> str:
    if transition_id not in FIXTURE_TEMPLATES:
        raise ValueError(f"No fixture template defined for: {transition_id}")

    tmpl = FIXTURE_TEMPLATES[transition_id]
    target_dir = os.path.join(output_root, transition_id)
    os.makedirs(target_dir, exist_ok=True)

    # 1. metadata.json
    with open(os.path.join(target_dir, "metadata.json"), "w", encoding="utf-8") as f:
        json.dump(candidate_metadata, f, indent=2)

    # 2. evidence/ copy
    evidence_src = os.path.join("evidence", transition_id)
    evidence_dst = os.path.join(target_dir, "evidence")
    if os.path.exists(evidence_src):
        if os.path.exists(evidence_dst):
            shutil.rmtree(evidence_dst)
        shutil.copytree(evidence_src, evidence_dst)

    # 3. before/
    before_dir = os.path.join(target_dir, "before")
    os.makedirs(before_dir, exist_ok=True)
    for p, content in tmpl["before_files"].items():
        fp = os.path.join(before_dir, p)
        os.makedirs(os.path.dirname(fp), exist_ok=True)
        with open(fp, "w", encoding="utf-8") as f:
            f.write(content)

    # 4. after/
    after_dir = os.path.join(target_dir, "after")
    os.makedirs(after_dir, exist_ok=True)
    for p, content in tmpl["after_files"].items():
        fp = os.path.join(after_dir, p)
        os.makedirs(os.path.dirname(fp), exist_ok=True)
        with open(fp, "w", encoding="utf-8") as f:
            f.write(content)

    # 5. hidden_tests/
    test_dir = os.path.join(target_dir, "hidden_tests")
    os.makedirs(test_dir, exist_ok=True)
    test_file = os.path.join(test_dir, "test_evaluation.py")
    with open(test_file, "w", encoding="utf-8") as f:
        f.write(tmpl["hidden_test"])

    # 6. environment.json
    env_info = {
        "transition_id": transition_id,
        "repo_name": candidate_metadata.get("repo_name"),
        "license": candidate_metadata.get("license"),
        "python_version": ">=3.10",
        "dependency_install_command": "pip install pytest",
        "requirements": ["pytest>=8.0.0"],
        "os_assumptions": "Linux x86_64",
        "setup_command": "export PYTHONPATH=.",
        "test_command": "pytest hidden_tests/test_evaluation.py",
        "timeout": 15,
        "network_requirement": "none",
        "sandbox_type": "bwrap"
    }
    with open(os.path.join(target_dir, "environment.json"), "w", encoding="utf-8") as f:
        json.dump(env_info, f, indent=2)

    print(f"[FIXTURE] Successfully built fixture for {transition_id} at: {target_dir}")
    return target_dir


def main():
    parser = argparse.ArgumentParser(description="Build Ground-Truth Transition Fixtures")
    parser.add_argument("--transition", help="Specific transition ID to build")
    parser.add_argument("--all", action="store_true", help="Build all gold transitions")
    parser.add_argument("--gold-file", default="data/gold/gold_transitions.jsonl", help="Path to gold transitions JSONL")
    args = parser.parse_args()

    if not os.path.exists(args.gold_file):
        print(f"Error: {args.gold_file} does not exist yet. Run scripts/mine_and_verify_gold_transitions.py first.")
        sys.exit(1)

    metadata_map = {}
    with open(args.gold_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                d = json.loads(line)
                metadata_map[d["transition_id"]] = d

    if args.transition:
        if args.transition not in metadata_map:
            raise KeyError(f"Transition {args.transition} not found in {args.gold_file}")
        build_fixture(args.transition, metadata_map[args.transition])
    else:
        # Build all
        for t_id, meta in metadata_map.items():
            build_fixture(t_id, meta)
        print(f"\n[COMPLETE] Successfully built all {len(metadata_map)} fixtures under fixtures/")


if __name__ == "__main__":
    main()
