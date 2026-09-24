"""
src/evidence_escalation/test_discovery.py

Native Test Discovery Engine for Protocol V2.2-V1 Evidence Escalation:
- Discovers test candidates from the repository's native test suite at target commit.
- Inspects test functions and methods for references to claim subject, object operations, dependencies, and assertions.
- Operates deterministically without reading gold labels, benchmark case IDs, or V2.1 oracle artifacts.
"""

from __future__ import annotations
import os
import re
import ast
import hashlib
import subprocess
from typing import Dict, Any, List, Optional, Tuple, Set

from .types import (
    EvidenceActionType,
    BindingStrength,
    TestCandidate,
    CostBudget
)
from .cost import CostTracker


class NativeTestDiscoveryEngine:
    """Discovers claim-relevant tests in the target repository snapshot."""

    def __init__(self):
        pass

    def _list_test_files(self, repo_root: str, target_commit: str) -> List[str]:
        """Lists test files present in the repository at target_commit."""
        if not repo_root or not target_commit:
            return []
        res = subprocess.run(
            ["git", "ls-tree", "-r", "--name-only", target_commit],
            cwd=repo_root,
            capture_output=True,
            text=True
        )
        if res.returncode != 0:
            return []

        all_files = [line.strip() for line in res.stdout.splitlines() if line.strip()]
        test_files = []
        for f in all_files:
            if not f.endswith(".py"):
                continue
            f_lower = f.lower()
            if (
                f_lower.startswith("tests/") or
                f_lower.startswith("test/") or
                "/tests/" in f_lower or
                "/test/" in f_lower or
                os.path.basename(f_lower).startswith("test_") or
                os.path.basename(f_lower).endswith("_test.py")
            ):
                test_files.append(f)

        return test_files

    def _get_file_content(self, repo_root: str, target_commit: str, file_path: str) -> Optional[str]:
        res = subprocess.run(
            ["git", "show", f"{target_commit}:{file_path}"],
            cwd=repo_root,
            capture_output=True,
            text=True
        )
        if res.returncode == 0:
            return res.stdout
        return None

    def discover_tests_for_claim(
        self,
        repo_root: str,
        repository_name: str,
        target_commit: str,
        subject: str,
        object_tokens: Optional[List[str]] = None,
        dependency_symbol: Optional[str] = None,
        cost_tracker: Optional[CostTracker] = None,
        budget: Optional[CostBudget] = None
    ) -> List[TestCandidate]:
        """
        Scans test files in repository at target_commit to find candidate tests relevant to (subject, object_tokens, dependency).
        """
        candidates: List[TestCandidate] = []
        test_files = self._list_test_files(repo_root, target_commit)

        if cost_tracker and budget:
            from .cost import BudgetGuard
            ok, reason = BudgetGuard.reserve(cost_tracker, budget, actions=1, action_type=EvidenceActionType.TEST_DISCOVERY)
            if not ok:
                return candidates
        elif cost_tracker:
            cost_tracker.add_action(EvidenceActionType.TEST_DISCOVERY)

        # Prioritize test files whose name mentions subject or core modules
        subject_clean = subject.split(".")[-1] if subject else ""
        obj_toks = set(t.lower() for t in (object_tokens or []) if len(t) > 2)

        def file_priority(fpath: str) -> int:
            p = 0
            if subject_clean and subject_clean.lower() in fpath.lower():
                p += 10
            if dependency_symbol and dependency_symbol.lower() in fpath.lower():
                p += 8
            for ot in obj_toks:
                if ot in fpath.lower():
                    p += 3
            return p

        sorted_test_files = sorted(test_files, key=file_priority, reverse=True)

        for tf in sorted_test_files:
            if cost_tracker and budget:
                from .cost import BudgetGuard
                ok, reason = BudgetGuard.reserve(cost_tracker, budget, files=1)
                if not ok:
                    break
            elif cost_tracker:
                cost_tracker.add_file_scan(1)

            src = self._get_file_content(repo_root, target_commit, tf)
            if not src:
                continue

            # Quick check if subject, object, or dependency appears in the test file
            src_lower = src.lower()
            has_subject = (subject_clean.lower() in src_lower) if subject_clean else False
            has_dep = (dependency_symbol.lower() in src_lower) if dependency_symbol else False
            has_any_obj = any(ot in src_lower for ot in obj_toks) if obj_toks else False

            if not (has_subject or has_dep or has_any_obj):
                continue

            # Parse AST to find test functions
            try:
                tree = ast.parse(src)
            except Exception:
                continue

            test_file_sha256 = hashlib.sha256(src.encode("utf-8")).hexdigest()

            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    fn_name = node.name
                    if not fn_name.startswith("test_") and not fn_name.startswith("test"):
                        continue

                    if cost_tracker and budget:
                        from .cost import BudgetGuard
                        ok, reason = BudgetGuard.reserve(cost_tracker, budget, tests=1)
                        if not ok:
                            break
                    elif cost_tracker:
                        cost_tracker.add_test_inspection(1)


                    # Inspect AST body of test function (excluding docstrings)
                    fn_src = ast.get_source_segment(src, node) or ""
                    test_fn_sha256 = hashlib.sha256(fn_src.encode("utf-8")).hexdigest()

                    # Count AST identifier mentions (Name, Attribute, Call)
                    subj_mentions = 0
                    dep_mentions = 0
                    obj_mentions = 0

                    for inner in ast.walk(node):
                        # Skip Expr containing solely a docstring Constant
                        if isinstance(inner, ast.Expr) and isinstance(inner.value, ast.Constant) and isinstance(inner.value.value, str):
                            continue

                        if isinstance(inner, ast.Name):
                            if subject_clean and inner.id == subject_clean:
                                subj_mentions += 1
                            if dependency_symbol and inner.id == dependency_symbol.split(".")[-1]:
                                dep_mentions += 1
                            if obj_toks and inner.id.lower() in obj_toks:
                                obj_mentions += 1
                        elif isinstance(inner, ast.Attribute):
                            if subject_clean and inner.attr == subject_clean:
                                subj_mentions += 1
                            if dependency_symbol and inner.attr == dependency_symbol.split(".")[-1]:
                                dep_mentions += 1
                            if obj_toks and inner.attr.lower() in obj_toks:
                                obj_mentions += 1
                        elif isinstance(inner, ast.Call):
                            if isinstance(inner.func, ast.Name):
                                if obj_toks and inner.func.id.lower() in obj_toks:
                                    obj_mentions += 1

                    # Count assertions
                    assertion_count = 0
                    for inner in ast.walk(node):
                        if isinstance(inner, ast.Assert):
                            assertion_count += 1
                        elif isinstance(inner, ast.Call):
                            # unittest assert methods (e.g. self.assertEqual, self.assertTrue)
                            if isinstance(inner.func, ast.Attribute) and inner.func.attr.startswith("assert"):
                                assertion_count += 1

                    if subj_mentions > 0 or dep_mentions > 0 or (subj_mentions > 0 and obj_mentions > 0):
                        cand = TestCandidate(
                            test_file=tf,
                            test_name=fn_name,
                            subject_mentions=subj_mentions,
                            object_mentions=obj_mentions,
                            dependency_mentions=dep_mentions,
                            assertion_count=assertion_count,
                            target_commit=target_commit,
                            source_hash=test_fn_sha256,
                            test_file_sha256=test_file_sha256,
                            test_function_sha256=test_fn_sha256,
                            binding_strength=BindingStrength.UNBOUND,  # will be computed by WitnessBindingAnalyzer
                            discovery_reason=f"Found in {tf}:{fn_name} with {subj_mentions} subject and {dep_mentions} dep mentions",
                            test_source=fn_src,
                            line_start=getattr(node, "lineno", 1),
                            line_end=getattr(node, "end_lineno", 1)
                        )
                        candidates.append(cand)

        return candidates
