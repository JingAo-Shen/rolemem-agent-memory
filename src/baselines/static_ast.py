"""
src/baselines/static_ast.py

Baseline-2: Pure Static AST Checker
Inspects the target repository AST for symbol existence only.
Predicts VALID if the symbol AST node exists in the target file; STALE if missing.
Blind to parameter default changes, signature shifts, and behavioral mutations.
"""

from __future__ import annotations
from typing import Dict, Any, Optional
import ast
import os
import subprocess
import time


class StaticASTBaselinePredictor:
    """Pure static AST existence baseline."""

    def __init__(self):
        pass

    def _resolve_repo_root(self, repository_name: str) -> Optional[str]:
        if not repository_name:
            return None
        repo_clean = repository_name.replace("/", "_")
        bare_cand = os.path.join("/tmp/formal_bare_repos", repo_clean)
        if os.path.isdir(bare_cand):
            return bare_cand
        repo_simple = repository_name.split("/")[-1]
        cache_cand = os.path.join("/code/repo_cache", repo_simple)
        if os.path.isdir(cache_cand):
            return cache_cand
        return None

    def _extract_file_source(self, repo_root: str, commit_sha: str, file_path: str) -> str:
        if not repo_root or not commit_sha or not file_path:
            return ""
        try:
            res = subprocess.run(
                ["git", "show", f"{commit_sha}:{file_path}"],
                cwd=repo_root,
                capture_output=True,
                text=True,
                timeout=5
            )
            if res.returncode == 0:
                return res.stdout
        except Exception:
            pass
        return ""

    def predict(
        self,
        case_input: Dict[str, Any],
        case_meta: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Inspect target AST and return validity prediction."""
        start_time = time.time()
        case_id = case_input.get("case_id", "UNKNOWN")
        repo_name = case_input.get("repository_name", "")
        structured = case_input.get("structured_claim", {})
        symbol = structured.get("symbol", "")
        short_symbol = symbol.split(".")[-1] if symbol else ""

        meta = case_meta or {}
        target_commit = meta.get("target_commit", "")
        evidence_path = meta.get("base_evidence_path", "")

        repo_root = self._resolve_repo_root(repo_name)
        target_source = self._extract_file_source(repo_root, target_commit, evidence_path) if repo_root else ""

        predicted_label = "VALID"
        confidence = 0.85

        if not target_source:
            # File missing or cannot checkout
            predicted_label = "STALE"
            confidence = 0.75
        else:
            try:
                tree = ast.parse(target_source)
                found = False
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                        if node.name in (symbol, short_symbol):
                            found = True
                            break
                    elif isinstance(node, ast.Assign):
                        for target in node.targets:
                            if isinstance(target, ast.Name) and target.id in (symbol, short_symbol):
                                found = True
                                break
                if found:
                    predicted_label = "VALID"
                    confidence = 0.90
                else:
                    predicted_label = "STALE"
                    confidence = 0.80
            except Exception:
                predicted_label = "STALE"
                confidence = 0.60

        wall_time = time.time() - start_time
        return {
            "case_id": case_id,
            "predicted_label": predicted_label,
            "confidence": confidence,
            "escalation_tier": "TIER_0_STATIC_AST",
            "action_count": 1,
            "execution_wall_time_sec": round(wall_time, 6)
        }
