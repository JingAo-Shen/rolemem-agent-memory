"""
tests/test_dependency_repo_context_v2_1.py

Unit test verifying repository-context awareness for dependency checking:
- Target symbol in bar.py has identical AST digest between base and target commits.
- Local dependency in foo.py removes old_api in target commit.
- SymbolValidityChecker returns VALID.
- DependencyValidityChecker resolves foo.py in target commit and returns STALE.
- RoleMemValidityEngine synthesizes the dependency failure and returns STALE.
"""

import os
import subprocess
import tempfile
import pytest

from src.validity import (
    SymbolValidityChecker,
    DependencyValidityChecker,
    RoleMemValidityEngine
)


def test_dependency_repo_context_local_module_break():
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_dir = os.path.join(tmpdir, 'repo')
        os.makedirs(repo_dir)

        subprocess.run(['git', 'init'], cwd=repo_dir, capture_output=True, check=True)
        subprocess.run(['git', 'config', 'user.name', 'Test'], cwd=repo_dir, check=True)
        subprocess.run(['git', 'config', 'user.email', 'test@example.com'], cwd=repo_dir, check=True)

        foo_path = os.path.join(repo_dir, 'foo.py')
        bar_path = os.path.join(repo_dir, 'bar.py')

        foo_base = chr(10).join(['def old_api():', '    return 42', ''])
        bar_content = chr(10).join(['from foo import old_api', '', 'def run():', '    return old_api()', ''])

        with open(foo_path, 'w', encoding='utf-8') as f_out:
            f_out.write(foo_base)

        with open(bar_path, 'w', encoding='utf-8') as f_out:
            f_out.write(bar_content)

        subprocess.run(['git', 'add', '-A'], cwd=repo_dir, check=True)
        subprocess.run(['git', 'commit', '-m', 'base commit'], cwd=repo_dir, check=True)
        base_commit = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=repo_dir, capture_output=True, text=True).stdout.strip()

        foo_target = chr(10).join(['def new_api():', '    return 100', ''])
        with open(foo_path, 'w', encoding='utf-8') as f_out:
            f_out.write(foo_target)

        subprocess.run(['git', 'add', '-A'], cwd=repo_dir, check=True)
        subprocess.run(['git', 'commit', '-m', 'target commit: remove old_api'], cwd=repo_dir, check=True)
        target_commit = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=repo_dir, capture_output=True, text=True).stdout.strip()

        bar_base = bar_content
        bar_target = bar_content

        # 1. Pure symbol checker: sees identical AST digest -> VALID
        sym_checker = SymbolValidityChecker()
        res_sym = sym_checker.evaluate(bar_base, bar_target, 'run')
        assert res_sym.decision == 'VALID'
        assert res_sym.symbol_changed is False

        # 2. Dependency checker with repo context: resolves foo.py in target commit -> STALE
        dep_checker = DependencyValidityChecker()
        res_dep = dep_checker.evaluate(
            base_source=bar_base,
            target_source=bar_target,
            symbol_qualified_name='run',
            repository_root=repo_dir,
            base_commit=base_commit,
            target_commit=target_commit,
            file_path='bar.py'
        )
        assert res_dep.decision == 'STALE'
        assert res_dep.dependency_changed is True
        assert any('local_dependency_symbol_missing' in e.evidence_type for e in res_dep.evidence)

        # 3. RoleMem validity engine: synthesizes symbol + dependency -> STALE
        engine = RoleMemValidityEngine()
        res_engine = engine.evaluate(
            memory_statement='run executes foo.old_api',
            symbol_qualified_name='run',
            base_source=bar_base,
            target_source=bar_target,
            repository_root=repo_dir,
            base_commit=base_commit,
            target_commit=target_commit,
            file_path='bar.py'
        )
        assert res_engine.decision == 'STALE'
        assert res_engine.dependency_changed is True
