#!/usr/bin/env python3
"""
Real Repository Grounded Fixture Builder (Pilot-v1.2b).
Constructs 100% genuine repository fixtures directly from local Git checkouts in /code/repo_cache/.
NO FIXTURE_TEMPLATES or synthetic micro-mock code is allowed.

Each fixture is written to:
fixtures_v2/{transition_id}/
    metadata.json
    environment.json
    before/ (genuine package files extracted from base_commit)
    after/  (genuine package files extracted from target_commit)
    hidden_tests/test_evaluation.py
    controls/
        stale_solution.py
        valid_solution.py
"""

import os
import sys
import json
import shutil
import subprocess
import argparse
from typing import Dict, Any, Optional

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.transition_verifier_v2 import REPO_CACHE_DIR, get_repo_dir


TASK_SPECS = {
    "trans_gold_werkzeug_01_cached_property": {
        "pkg_path": "src/werkzeug",
        "target_file": "property_helper.py",
        "target_symbol": "reset_cached_attribute",
        "stale_solution": '''from werkzeug.utils import invalidate_cached_property

def reset_cached_attribute(instance, attr_name):
    # Stale pattern: invokes deprecated invalidate_cached_property (PR #2084)
    invalidate_cached_property(instance, attr_name)
''',
        "valid_solution": '''def reset_cached_attribute(instance, attr_name):
    # Valid pattern: standard Python descriptor deletion del obj.prop / delattr
    try:
        delattr(instance, attr_name)
    except AttributeError:
        pass
''',
        "hidden_test": '''import pytest
import warnings
import sys
import os

sys.path.insert(0, os.path.abspath("src"))
from werkzeug.utils import cached_property
from property_helper import reset_cached_attribute

class DummyTarget:
    def __init__(self):
        self.computations = 0

    @cached_property
    def value(self):
        self.computations += 1
        return 42

def test_reset_cached_attribute():
    target = DummyTarget()
    assert target.value == 42
    assert target.computations == 1

    with warnings.catch_warnings(record=True) as recorded:
        warnings.simplefilter("always")
        reset_cached_attribute(target, "value")
        dep_warnings = [w for w in recorded if issubclass(w.category, DeprecationWarning)]
        assert len(dep_warnings) == 0, f"Encountered deprecated call: {[str(w.message) for w in dep_warnings]}"

    assert "value" not in target.__dict__
    assert target.value == 42
    assert target.computations == 2
'''
    },
    "trans_gold_werkzeug_02_environ_properties": {
        "pkg_path": "src/werkzeug",
        "target_file": "wsgi_helper.py",
        "target_symbol": "extract_wsgi_header",
        "stale_solution": '''from werkzeug.utils import environ_property

class HeaderHolder:
    host = environ_property("HTTP_HOST")
    def __init__(self, environ):
        self.environ = environ

def extract_wsgi_header(environ: dict, header_name: str) -> str:
    # Stale pattern: accesses deprecated environ_property descriptor (PR #3276)
    if header_name.lower() == "host":
        return HeaderHolder(environ).host or ""
    key = "HTTP_" + header_name.upper().replace("-", "_")
    return environ.get(key, "")
''',
        "valid_solution": '''def extract_wsgi_header(environ: dict, header_name: str) -> str:
    # Valid pattern: direct dictionary access on WSGI environ mapping
    key = "HTTP_" + header_name.upper().replace("-", "_")
    return environ.get(key, environ.get(header_name, ""))
''',
        "hidden_test": '''import pytest
import warnings
import sys
import os

sys.path.insert(0, os.path.abspath("src"))

def test_extract_wsgi_header():
    environ = {
        "HTTP_HOST": "localhost:8080",
        "HTTP_USER_AGENT": "RoleMemBot/1.0"
    }
    with warnings.catch_warnings(record=True) as recorded:
        warnings.simplefilter("always")
        from wsgi_helper import extract_wsgi_header
        host = extract_wsgi_header(environ, "host")
        assert host == "localhost:8080"
        dep_warnings = [w for w in recorded if issubclass(w.category, (DeprecationWarning, UserWarning))]
        assert len(dep_warnings) == 0, f"Encountered deprecated call: {[str(w.message) for w in dep_warnings]}"
'''
    },
    "trans_gold_flask_01_context_stack_removal": {
        "pkg_path": "src/flask",
        "target_file": "ctx_manager.py",
        "target_symbol": "activate_application_context",
        "stale_solution": '''from flask.globals import _app_ctx_stack

def activate_application_context(app):
    # Stale pattern: calls removed _app_ctx_stack.push() (PR #4995)
    ctx = app.app_context()
    _app_ctx_stack.push(ctx)
    return ctx
''',
        "valid_solution": '''def activate_application_context(app):
    # Valid pattern: calls ctx.push() directly
    ctx = app.app_context()
    ctx.push()
    return ctx
''',
        "hidden_test": '''import pytest
import sys
import os

sys.path.insert(0, os.path.abspath("src"))
from flask import Flask, current_app
from ctx_manager import activate_application_context

def test_activate_ctx():
    app = Flask("test_isolated_app")
    ctx = activate_application_context(app)
    assert current_app.name == "test_isolated_app"
    ctx.pop()
'''
    },
    "trans_gold_flask_02_should_ignore_error": {
        "pkg_path": "src/flask",
        "target_file": "error_policy.py",
        "target_symbol": "configure_error_policy",
        "stale_solution": '''def configure_error_policy(app, exc_class):
    # Stale pattern: overrides should_ignore_error on Flask instance (PR #5899)
    app.should_ignore_error = lambda err: isinstance(err, exc_class)
''',
        "valid_solution": '''def configure_error_policy(app, exc_class):
    # Valid pattern: registers teardown handler or errorhandler
    @app.teardown_request
    def handle_teardown(exc):
        pass
''',
        "hidden_test": '''import pytest
import warnings
import sys
import os

sys.path.insert(0, os.path.abspath("src"))
from flask import Flask
from error_policy import configure_error_policy

class TransientGlitch(Exception):
    pass

def test_error_policy():
    app = Flask("policy_app")
    @app.route("/")
    def index():
        return "OK"

    configure_error_policy(app, TransientGlitch)

    with warnings.catch_warnings(record=True) as recorded:
        warnings.simplefilter("always")
        client = app.test_client()
        res = client.get("/")
        assert res.status_code == 200
        dep_warnings = [w for w in recorded if issubclass(w.category, DeprecationWarning)]
        assert len(dep_warnings) == 0, f"should_ignore_error deprecated warning: {[str(w.message) for w in dep_warnings]}"
'''
    },
    "trans_gold_urllib3_01_retry_allowed_methods": {
        "pkg_path": "src/urllib3",
        "target_file": "retry_factory.py",
        "target_symbol": "build_custom_retry",
        "stale_solution": '''from urllib3.util.retry import Retry

def build_custom_retry(methods: list):
    # Stale pattern: method_whitelist is deprecated in favor of allowed_methods (PR #2000)
    return Retry(method_whitelist=methods)
''',
        "valid_solution": '''from urllib3.util.retry import Retry

def build_custom_retry(methods: list):
    # Valid pattern: allowed_methods
    return Retry(allowed_methods=methods)
''',
        "hidden_test": '''import pytest
import warnings
import sys
import os

sys.path.insert(0, os.path.abspath("src"))
from retry_factory import build_custom_retry

def test_build_custom_retry():
    with warnings.catch_warnings(record=True) as recorded:
        warnings.simplefilter("always")
        r = build_custom_retry(["GET", "POST"])
        assert r.allowed_methods == frozenset(["GET", "POST"])
        dep_warnings = [w for w in recorded if issubclass(w.category, DeprecationWarning)]
        assert len(dep_warnings) == 0, f"method_whitelist deprecated: {[str(w.message) for w in dep_warnings]}"
'''
    },
    "trans_gold_urllib3_02_empty_allowed_methods": {
        "pkg_path": "src/urllib3",
        "target_file": "retry_factory.py",
        "target_symbol": "create_all_verbs_retry",
        "stale_solution": '''from urllib3.util.retry import Retry

def create_all_verbs_retry():
    # Stale pattern: empty collection allowed_methods=[] emits warning (PR #5223)
    return Retry(allowed_methods=[])
''',
        "valid_solution": '''from urllib3.util.retry import Retry

def create_all_verbs_retry():
    # Valid pattern: allowed_methods=None
    return Retry(allowed_methods=None)
''',
        "hidden_test": '''import pytest
import warnings
import sys
import os

sys.path.insert(0, os.path.abspath("src"))
from retry_factory import create_all_verbs_retry

def test_create_all_verbs_retry():
    with warnings.catch_warnings(record=True) as recorded:
        warnings.simplefilter("always")
        r = create_all_verbs_retry()
        assert r.allowed_methods is None or r.allowed_methods is False
        fut_warnings = [w for w in recorded if issubclass(w.category, (FutureWarning, DeprecationWarning))]
        assert len(fut_warnings) == 0, f"empty collection allowed_methods warning: {[str(w.message) for w in fut_warnings]}"
'''
    },
    "trans_gold_click_01_option_parser": {
        "pkg_path": "src/click",
        "target_file": "cli_helper.py",
        "target_symbol": "parse_command_args",
        "stale_solution": '''from click.parser import OptionParser

def parse_command_args(cmd, args_list):
    # Stale pattern: imports deprecated click.parser.OptionParser (PR #2592)
    parser = OptionParser()
    for param in cmd.params:
        param.add_to_parser(parser, cmd)
    opts, args, order = parser.parse_args(args=list(args_list))
    return opts
''',
        "valid_solution": '''import click

def parse_command_args(cmd, args_list):
    # Valid pattern: uses cmd.make_context params
    ctx = cmd.make_context(cmd.name, list(args_list))
    return ctx.params
''',
        "hidden_test": '''import pytest
import warnings
import sys
import os

sys.path.insert(0, os.path.abspath("src"))
import click

def test_parse_args():
    @click.command()
    @click.option("--name", default="World")
    def hello(name):
        pass

    with warnings.catch_warnings(record=True) as recorded:
        warnings.simplefilter("always")
        from cli_helper import parse_command_args
        res = parse_command_args(hello, ["--name", "Antigravity"])
        assert res.get("name") == "Antigravity"
        dep_warnings = [w for w in recorded if issubclass(w.category, (DeprecationWarning, UserWarning))]
        assert len(dep_warnings) == 0, f"OptionParser deprecated: {[str(w.message) for w in dep_warnings]}"
'''
    },
    "trans_gold_click_02_isolated_filesystem": {
        "pkg_path": "src/click",
        "target_file": "test_isolation.py",
        "target_symbol": "run_in_isolated_dir",
        "stale_solution": '''from click.testing import CliRunner

def run_in_isolated_dir(task_fn):
    # Stale pattern: CliRunner.isolated_filesystem is deprecated (PR #3704)
    runner = CliRunner()
    with runner.isolated_filesystem():
        return task_fn()
''',
        "valid_solution": '''import tempfile
import os

def run_in_isolated_dir(task_fn):
    # Valid pattern: tempfile.TemporaryDirectory
    with tempfile.TemporaryDirectory() as tmp_dir:
        orig = os.getcwd()
        try:
            os.chdir(tmp_dir)
            return task_fn()
        finally:
            os.chdir(orig)
''',
        "hidden_test": '''import pytest
import warnings
import os
import sys

sys.path.insert(0, os.path.abspath("src"))
from test_isolation import run_in_isolated_dir

def test_run_in_isolated_dir():
    orig_cwd = os.getcwd()
    with warnings.catch_warnings(record=True) as recorded:
        warnings.simplefilter("always")
        res_cwd = run_in_isolated_dir(lambda: os.getcwd())
        assert res_cwd != orig_cwd
        assert os.getcwd() == orig_cwd
        dep_warnings = [w for w in recorded if issubclass(w.category, DeprecationWarning)]
        assert len(dep_warnings) == 0, f"isolated_filesystem deprecated: {[str(w.message) for w in dep_warnings]}"
'''
    },
    "trans_gold_requests_01_tls_context_adapter": {
        "pkg_path": "src/requests",
        "target_file": "adapter_helper.py",
        "target_symbol": "get_adapter_connection",
        "stale_solution": '''def get_adapter_connection(adapter, request, verify=True):
    # Stale pattern: calls deprecated get_connection(url) (PR #6710)
    return adapter.get_connection(request.url)
''',
        "valid_solution": '''def get_adapter_connection(adapter, request, verify=True):
    # Valid pattern: calls get_connection_with_tls_context(request, verify=verify)
    return adapter.get_connection_with_tls_context(request, verify=verify)
''',
        "hidden_test": '''import pytest
import warnings
import sys
import os

sys.path.insert(0, os.path.abspath("src"))
from requests.adapters import HTTPAdapter
from requests.models import PreparedRequest
from adapter_helper import get_adapter_connection

def test_get_conn():
    adapter = HTTPAdapter()
    req = PreparedRequest()
    req.prepare_url("https://httpbin.org/get", {})
    with warnings.catch_warnings(record=True) as recorded:
        warnings.simplefilter("always")
        conn = get_adapter_connection(adapter, req, verify=True)
        assert conn is not None
        dep_warnings = [w for w in recorded if issubclass(w.category, DeprecationWarning)]
        assert len(dep_warnings) == 0, f"get_connection deprecated: {[str(w.message) for w in dep_warnings]}"
'''
    },
    "trans_gold_requests_02_pool_key_overrides": {
        "pkg_path": "src/requests",
        "target_file": "pool_config.py",
        "target_symbol": "get_pool_key_attributes",
        "stale_solution": '''def get_pool_key_attributes(adapter, request, verify=True):
    # Stale pattern: does not use build_connection_pool_key_attributes (PR #6716)
    return {"url": request.url, "verify": verify}
''',
        "valid_solution": '''def get_pool_key_attributes(adapter, request, verify=True):
    # Valid pattern: uses build_connection_pool_key_attributes
    return adapter.build_connection_pool_key_attributes(request, verify=verify)
''',
        "hidden_test": '''import pytest
import sys
import os

sys.path.insert(0, os.path.abspath("src"))
from requests.adapters import HTTPAdapter
from requests.models import PreparedRequest
from pool_config import get_pool_key_attributes

def test_pool_keys():
    adapter = HTTPAdapter()
    req = PreparedRequest()
    req.prepare_url("https://httpbin.org/get", {})
    attrs = get_pool_key_attributes(adapter, req, verify=True)
    assert isinstance(attrs, tuple) and len(attrs) == 2, "Must return (host_params, pool_kwargs) tuple"
    host_params, pool_kwargs = attrs
    assert "ssl_context" in pool_kwargs
'''
    }
}


def extract_git_snapshot(repo_dir: str, commit_sha: str, pkg_path: str, dest_dir: str) -> None:
    """Extract pristine files directly from Git commit using git archive."""
    os.makedirs(dest_dir, exist_ok=True)
    p1 = subprocess.Popen(
        ["git", "-C", repo_dir, "archive", commit_sha, pkg_path],
        stdout=subprocess.PIPE
    )
    p2 = subprocess.Popen(
        ["tar", "-x", "-C", dest_dir],
        stdin=p1.stdout
    )
    p1.stdout.close()
    p2.communicate()
    if p2.returncode != 0:
        raise RuntimeError(f"Failed to extract {pkg_path} at {commit_sha} from {repo_dir}")

    # For packages using setuptools_scm/hatch_vcs where _version.py is generated dynamically
    u3_dir = os.path.join(dest_dir, "src", "urllib3")
    if os.path.isdir(u3_dir) and not os.path.exists(os.path.join(u3_dir, "_version.py")):
        with open(os.path.join(u3_dir, "_version.py"), "w", encoding="utf-8") as f:
            f.write('__version__ = "2.1.0"\n')


def build_real_fixture(
    transition_id: str,
    candidate_metadata: Dict[str, Any],
    output_root: str = "fixtures_v2"
) -> str:
    if transition_id not in TASK_SPECS:
        raise ValueError(f"No task specification for: {transition_id}")

    spec = TASK_SPECS[transition_id]
    repo_name = candidate_metadata["repo_name"]
    repo_dir = get_repo_dir(repo_name)
    if not repo_dir:
        raise FileNotFoundError(f"Local repo cache for {repo_name} not found in {REPO_CACHE_DIR}")

    target_dir = os.path.join(output_root, transition_id)
    os.makedirs(target_dir, exist_ok=True)

    # 1. metadata.json
    with open(os.path.join(target_dir, "metadata.json"), "w", encoding="utf-8") as f:
        json.dump(candidate_metadata, f, indent=2)

    # 2. environment.json
    env_info = {
        "transition_id": transition_id,
        "repo_name": repo_name,
        "license": candidate_metadata.get("license"),
        "base_commit": candidate_metadata.get("base_commit"),
        "target_commit": candidate_metadata.get("target_commit"),
        "python_version": ">=3.10",
        "dependency_install_command": "pip install pytest",
        "requirements": ["pytest>=8.0.0"],
        "os_assumptions": "Linux x86_64",
        "setup_command": "export PYTHONPATH=.:src",
        "test_command": "pytest hidden_tests/test_evaluation.py",
        "timeout": 15,
        "network_requirement": "none",
        "sandbox_type": "bwrap"
    }
    with open(os.path.join(target_dir, "environment.json"), "w", encoding="utf-8") as f:
        json.dump(env_info, f, indent=2)

    # 3. before/ (genuine commit extraction)
    before_dir = os.path.join(target_dir, "before")
    if os.path.exists(before_dir):
        shutil.rmtree(before_dir)
    extract_git_snapshot(repo_dir, candidate_metadata["base_commit"], spec["pkg_path"], before_dir)

    # 4. after/ (genuine commit extraction)
    after_dir = os.path.join(target_dir, "after")
    if os.path.exists(after_dir):
        shutil.rmtree(after_dir)
    extract_git_snapshot(repo_dir, candidate_metadata["target_commit"], spec["pkg_path"], after_dir)

    # 5. hidden_tests/
    test_dir = os.path.join(target_dir, "hidden_tests")
    os.makedirs(test_dir, exist_ok=True)
    with open(os.path.join(test_dir, "test_evaluation.py"), "w", encoding="utf-8") as f:
        f.write(spec["hidden_test"])

    # 6. controls/
    controls_dir = os.path.join(target_dir, "controls")
    os.makedirs(controls_dir, exist_ok=True)
    with open(os.path.join(controls_dir, "stale_solution.py"), "w", encoding="utf-8") as f:
        f.write(spec["stale_solution"])
    with open(os.path.join(controls_dir, "valid_solution.py"), "w", encoding="utf-8") as f:
        f.write(spec["valid_solution"])

    print(f"[FIXTURE_V2] Successfully built git-grounded fixture for {transition_id} at {target_dir}")
    return target_dir


def main():
    parser = argparse.ArgumentParser(description="Build Genuine Git-Grounded Transition Fixtures")
    parser.add_argument("--transition", help="Specific transition ID to build")
    parser.add_argument("--all", action="store_true", help="Build all gold transitions")
    parser.add_argument("--gold-file", default="data/gold/gold_transitions.jsonl", help="Path to gold transitions JSONL")
    parser.add_argument("--output-root", default="fixtures_v2", help="Output fixtures directory")
    args = parser.parse_args()

    with open(args.gold_file, "r", encoding="utf-8") as f:
        records = [json.loads(line) for line in f if line.strip()]

    target_records = records
    if args.transition:
        target_records = [r for r in records if r["transition_id"] == args.transition]
        if not target_records:
            raise KeyError(f"Transition {args.transition} not found in {args.gold_file}")

    for r in target_records:
        build_real_fixture(r["transition_id"], r, output_root=args.output_root)

    print(f"\n[COMPLETE] Successfully built {len(target_records)} real git fixtures under {args.output_root}/")


if __name__ == "__main__":
    main()
