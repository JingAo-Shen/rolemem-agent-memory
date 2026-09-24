"""
src/evidence_escalation/repository_search.py

Repository Search & Git History Inspection Engine for Protocol V2.2-V1 Evidence Escalation:
- Searches repository target snapshot AST and source files for subject symbols, qualified child names, attributes, and dependencies.
- Inspects git diff and commit history for symbol modification or deletion provenance.
- Generates AcquiredEvidence records with strict provenance (commit, file, line ranges, content hash).
"""

from __future__ import annotations
import os
import re
import ast
import json
import hashlib
import subprocess
from typing import Dict, Any, List, Optional, Tuple, Set

from .types import (
    EvidenceActionType,
    EvidenceKind,
    BindingStrength,
    AcquiredEvidence,
    CostBudget
)
from .cost import CostTracker


class RepositorySearchEngine:
    """Executes structured repository search and git history inspection."""

    def __init__(self):
        pass

    def _get_file_content_at_commit(self, repo_root: str, commit: str, file_path: str) -> Optional[str]:
        if not repo_root or not commit or not file_path:
            return None
        res = subprocess.run(
            ["git", "show", f"{commit}:{file_path}"],
            cwd=repo_root,
            capture_output=True,
            text=True
        )
        if res.returncode == 0:
            return res.stdout
        return None

    def _get_git_diff(self, repo_root: str, base_commit: str, target_commit: str, file_path: Optional[str] = None) -> str:
        if not repo_root or not base_commit or not target_commit:
            return ""
        cmd = ["git", "diff", base_commit, target_commit]
        if file_path:
            cmd.extend(["--", file_path])
        res = subprocess.run(cmd, cwd=repo_root, capture_output=True, text=True)
        if res.returncode == 0:
            return res.stdout
        return ""

    def search_qualified_symbol_or_attribute(
        self,
        claim_id: str,
        repo_root: str,
        repository_name: str,
        base_commit: str,
        target_commit: str,
        file_path: str,
        parent_symbol: str,
        child_symbol: str,
        cost_tracker: Optional[CostTracker] = None,
        budget: Optional[CostBudget] = None
    ) -> List[AcquiredEvidence]:
        """
        Searches for a qualified symbol/attribute (parent_symbol.child_symbol) across target and base snapshots.
        If child existed at base_commit within parent_symbol but is absent at target_commit,
        records concrete evidence of symbol removal.
        """
        evidences: List[AcquiredEvidence] = []
        if cost_tracker and budget:
            from .cost import BudgetGuard
            ok, reason = BudgetGuard.reserve(cost_tracker, budget, files=2, actions=1, action_type=EvidenceActionType.REPOSITORY_SEARCH)
            if not ok:
                return evidences
        elif cost_tracker:
            cost_tracker.add_action(EvidenceActionType.REPOSITORY_SEARCH)
            cost_tracker.add_file_scan(2)

        target_src = self._get_file_content_at_commit(repo_root, target_commit, file_path)
        base_src = self._get_file_content_at_commit(repo_root, base_commit, file_path)

        if not target_src:
            return evidences

        # Parse target AST to find parent_symbol and check child_symbol presence
        target_has_child = False
        target_has_parent = False
        target_parent_node = None

        try:
            target_tree = ast.parse(target_src)
            for node in ast.walk(target_tree):
                if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                    if node.name == parent_symbol:
                        target_has_parent = True
                        target_parent_node = node
                        # Inspect inner body for child_symbol
                        for inner in ast.walk(node):
                            if isinstance(inner, (ast.FunctionDef, ast.AsyncFunctionDef)) and inner.name == child_symbol:
                                target_has_child = True
                                break
                            elif isinstance(inner, ast.Attribute) and inner.attr == child_symbol:
                                target_has_child = True
                                break
                            elif isinstance(inner, ast.Name) and inner.id == child_symbol:
                                target_has_child = True
                                break
                            elif isinstance(inner, ast.Assign):
                                for tgt in inner.targets:
                                    if isinstance(tgt, ast.Name) and tgt.id == child_symbol:
                                        target_has_child = True
                                        break
        except Exception:
            pass

        # Parse base AST to verify whether parent_symbol.child_symbol existed at base
        base_had_child = False
        base_had_parent = False
        if base_src:
            try:
                base_tree = ast.parse(base_src)
                for node in ast.walk(base_tree):
                    if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                        if node.name == parent_symbol:
                            base_had_parent = True
                            for inner in ast.walk(node):
                                if isinstance(inner, (ast.FunctionDef, ast.AsyncFunctionDef)) and inner.name == child_symbol:
                                    base_had_child = True
                                    break
                                elif isinstance(inner, ast.Assign):
                                    for tgt in inner.targets:
                                        if isinstance(tgt, ast.Name) and tgt.id == child_symbol:
                                            base_had_child = True
                                            break
            except Exception:
                pass

        # Inspect diff for deletion markers
        diff_text = self._get_git_diff(repo_root, base_commit, target_commit, file_path)
        diff_deleted_child = False
        if diff_text and child_symbol:
            del_pattern = re.compile(rf"^\-\s*(?:def\s+{re.escape(child_symbol)}|{re.escape(child_symbol)}\s*=)", re.MULTILINE)
            if del_pattern.search(diff_text):
                diff_deleted_child = True

        base_chash = hashlib.sha256((base_src or "").encode("utf-8")).hexdigest() if base_src else ""
        target_chash = hashlib.sha256((target_src or "").encode("utf-8")).hexdigest() if target_src else ""

        if base_had_child and (not target_has_child or diff_deleted_child):
            # Proved removal of qualified symbol / attribute
            ev = AcquiredEvidence(
                evidence_id=f"EV-QUAL-REM-{hashlib.sha256(f'{claim_id}:{parent_symbol}.{child_symbol}'.encode()).hexdigest()[:8]}",
                claim_id=claim_id,
                action_type=EvidenceActionType.REPOSITORY_SEARCH,
                source_type="AST_SNAPSHOT_AND_DIFF",
                evidence_kind=EvidenceKind.STRUCTURAL_AST_EVIDENCE,
                repository=repository_name,
                commit=target_commit,
                file_path=file_path,
                content_hash=target_chash,
                binding_strength=BindingStrength.STRONG,
                supports_or_contradicts="CONTRADICTS",
                confidence=0.95,
                source_origin_status="NOT_APPLICABLE",
                repository_snapshot_status="VERIFIED_TARGET_COMMIT",
                base_file_sha256=base_chash,
                target_file_sha256=target_chash,
                base_symbol_presence=base_had_child,
                target_symbol_presence=target_has_child,
                detail=f"Qualified symbol '{parent_symbol}.{child_symbol}' existed in base commit but was removed in target commit (diff deletion confirmed: {diff_deleted_child}).",
                extra_metadata={
                    "parent_symbol": parent_symbol,
                    "child_symbol": child_symbol,
                    "base_had_child": base_had_child,
                    "target_has_child": target_has_child,
                    "diff_deleted_child": diff_deleted_child
                }
            )
            evidences.append(ev)
        elif target_has_child:
            ev = AcquiredEvidence(
                evidence_id=f"EV-QUAL-PRES-{hashlib.sha256(f'{claim_id}:{parent_symbol}.{child_symbol}'.encode()).hexdigest()[:8]}",
                claim_id=claim_id,
                action_type=EvidenceActionType.REPOSITORY_SEARCH,
                source_type="AST_SNAPSHOT",
                evidence_kind=EvidenceKind.STRUCTURAL_AST_EVIDENCE,
                repository=repository_name,
                commit=target_commit,
                file_path=file_path,
                content_hash=target_chash,
                binding_strength=BindingStrength.STRONG,
                supports_or_contradicts="SUPPORTS",
                confidence=0.95,
                source_origin_status="NOT_APPLICABLE",
                repository_snapshot_status="VERIFIED_TARGET_COMMIT",
                base_file_sha256=base_chash,
                target_file_sha256=target_chash,
                base_symbol_presence=base_had_child,
                target_symbol_presence=target_has_child,
                detail=f"Qualified symbol '{parent_symbol}.{child_symbol}' verified present in target commit AST.",
                extra_metadata={
                    "parent_symbol": parent_symbol,
                    "child_symbol": child_symbol,
                    "target_has_child": True
                }
            )
            evidences.append(ev)

        return evidences

    def search_dependency_usage(
        self,
        claim_id: str,
        repo_root: str,
        repository_name: str,
        base_commit: str,
        target_commit: str,
        file_path: str,
        subject_symbol: str,
        dependency_symbol: str,
        cost_tracker: Optional[CostTracker] = None,
        budget: Optional[CostBudget] = None
    ) -> List[AcquiredEvidence]:
        """
        Searches for references to dependency_symbol within subject_symbol definition.
        Checks if dependency reference was removed in git diff.
        """
        evidences: List[AcquiredEvidence] = []
        if cost_tracker and budget:
            from .cost import BudgetGuard
            ok, reason = BudgetGuard.reserve(cost_tracker, budget, files=2, actions=1, action_type=EvidenceActionType.DEPENDENCY_INSPECTION)
            if not ok:
                return evidences
        elif cost_tracker:
            cost_tracker.add_action(EvidenceActionType.DEPENDENCY_INSPECTION)
            cost_tracker.add_file_scan(2)

        target_src = self._get_file_content_at_commit(repo_root, target_commit, file_path)
        base_src = self._get_file_content_at_commit(repo_root, base_commit, file_path)

        if not target_src:
            return evidences

        # Check if subject_symbol in target contains dependency_symbol
        subject_found_in_target = False
        target_uses_dep = False
        try:
            tree = ast.parse(target_src)
            for node in ast.walk(tree):
                if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == subject_symbol:
                    subject_found_in_target = True
                    for inner in ast.walk(node):
                        if isinstance(inner, ast.Name) and inner.id == dependency_symbol:
                            target_uses_dep = True
                            break
                        elif isinstance(inner, ast.Attribute) and inner.attr == dependency_symbol:
                            target_uses_dep = True
                            break
        except Exception:
            pass

        # Check base usage
        base_uses_dep = False
        if base_src:
            try:
                tree_b = ast.parse(base_src)
                for node in ast.walk(tree_b):
                    if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == subject_symbol:
                        for inner in ast.walk(node):
                            if isinstance(inner, ast.Name) and inner.id == dependency_symbol:
                                base_uses_dep = True
                                break
                            elif isinstance(inner, ast.Attribute) and inner.attr == dependency_symbol:
                                base_uses_dep = True
                                break
            except Exception:
                pass

        # Check if diff removed dependency_symbol
        diff_text = self._get_git_diff(repo_root, base_commit, target_commit, file_path)
        diff_removed_dep = False
        if diff_text and dependency_symbol:
            del_pattern = re.compile(rf"^\-.*\b{re.escape(dependency_symbol)}\b", re.MULTILINE)
            if del_pattern.search(diff_text):
                diff_removed_dep = True

        base_chash = hashlib.sha256((base_src or "").encode("utf-8")).hexdigest() if base_src else ""
        target_chash = hashlib.sha256((target_src or "").encode("utf-8")).hexdigest() if target_src else ""

        if base_uses_dep and not target_uses_dep:
            ev = AcquiredEvidence(
                evidence_id=f"EV-DEP-REM-{hashlib.sha256(f'{claim_id}:{subject_symbol}:{dependency_symbol}'.encode()).hexdigest()[:8]}",
                claim_id=claim_id,
                action_type=EvidenceActionType.DEPENDENCY_INSPECTION,
                source_type="AST_AND_DIFF",
                evidence_kind=EvidenceKind.DEPENDENCY_EVIDENCE,
                repository=repository_name,
                commit=target_commit,
                file_path=file_path,
                content_hash=target_chash,
                binding_strength=BindingStrength.STRONG,
                supports_or_contradicts="CONTRADICTS",
                confidence=0.92,
                source_origin_status="NOT_APPLICABLE",
                repository_snapshot_status="VERIFIED_TARGET_COMMIT",
                base_file_sha256=base_chash,
                target_file_sha256=target_chash,
                base_symbol_presence=base_uses_dep,
                target_symbol_presence=target_uses_dep,
                detail=f"Dependency on '{dependency_symbol}' inside '{subject_symbol}' was removed between base and target commit (diff removed: {diff_removed_dep}).",
                extra_metadata={
                    "subject_symbol": subject_symbol,
                    "dependency_symbol": dependency_symbol,
                    "base_uses_dep": base_uses_dep,
                    "target_uses_dep": target_uses_dep,
                    "diff_removed_dep": diff_removed_dep
                }
            )
            evidences.append(ev)
        elif target_uses_dep:
            # AST reference alone is only weak evidence of contract validity
            ev = AcquiredEvidence(
                evidence_id=f"EV-DEP-PRES-{hashlib.sha256(f'{claim_id}:{subject_symbol}:{dependency_symbol}'.encode()).hexdigest()[:8]}",
                claim_id=claim_id,
                action_type=EvidenceActionType.DEPENDENCY_INSPECTION,
                source_type="AST",
                evidence_kind=EvidenceKind.DEPENDENCY_EVIDENCE,
                repository=repository_name,
                commit=target_commit,
                file_path=file_path,
                content_hash=target_chash,
                binding_strength=BindingStrength.WEAK,
                supports_or_contradicts="SUPPORTS",
                confidence=0.60,
                source_origin_status="NOT_APPLICABLE",
                repository_snapshot_status="VERIFIED_TARGET_COMMIT",
                base_file_sha256=base_chash,
                target_file_sha256=target_chash,
                base_symbol_presence=base_uses_dep,
                target_symbol_presence=target_uses_dep,
                detail=f"Static reference to '{dependency_symbol}' inside '{subject_symbol}' exists in AST (weak evidence; runtime contract unverified).",
                extra_metadata={
                    "subject_symbol": subject_symbol,
                    "dependency_symbol": dependency_symbol,
                    "target_uses_dep": True
                }
            )
            evidences.append(ev)

        return evidences

