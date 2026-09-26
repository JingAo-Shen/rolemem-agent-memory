"""
src/baselines/naive_rag.py

Baseline-3: Naive RAG Predictor
Retrieves target repository source content using unscoped keyword / lexical matching.
Predicts VALID if key query tokens co-occur in the retrieved text above a lexical overlap threshold;
predicts STALE otherwise.
Lacks epistemic role gating, AST structure semantics, and evidence escalation.
"""

from __future__ import annotations
from typing import Dict, Any, Optional, List
import os
import re
import subprocess
import time


class NaiveRAGBaselinePredictor:
    """Unscoped lexical RAG baseline."""

    def __init__(self, match_threshold: float = 0.50):
        self.match_threshold = match_threshold

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

    def _tokenize(self, text: str) -> List[str]:
        return [w.lower() for w in re.findall(r"[A-Za-z0-9_]+", text) if len(w) > 1]

    def predict(
        self,
        case_input: Dict[str, Any],
        case_meta: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Perform lexical RAG match and return validity prediction."""
        start_time = time.time()
        case_id = case_input.get("case_id", "UNKNOWN")
        repo_name = case_input.get("repository_name", "")
        raw_stmt = case_input.get("raw_statement", "")
        structured = case_input.get("structured_claim", {})

        meta = case_meta or {}
        target_commit = meta.get("target_commit", "")
        evidence_path = meta.get("base_evidence_path", "")

        repo_root = self._resolve_repo_root(repo_name)
        target_source = self._extract_file_source(repo_root, target_commit, evidence_path) if repo_root else ""

        # Extract essential query tokens from statement and structured slots
        query_text = f"{raw_stmt} {' '.join(str(v) for v in structured.values() if v)}"
        query_tokens = set(self._tokenize(query_text))

        if not target_source or not query_tokens:
            predicted_label = "STALE"
            confidence = 0.50
            overlap_ratio = 0.0
        else:
            doc_tokens = set(self._tokenize(target_source))
            intersection = query_tokens & doc_tokens
            overlap_ratio = len(intersection) / len(query_tokens)

            # Check if crucial symbol is in document
            sym = structured.get("symbol", "")
            short_sym = sym.split(".")[-1].lower() if sym else ""
            sym_present = (short_sym in doc_tokens) if short_sym else True

            if overlap_ratio >= self.match_threshold and sym_present:
                predicted_label = "VALID"
                confidence = round(min(0.95, 0.50 + overlap_ratio * 0.5), 4)
            else:
                predicted_label = "STALE"
                confidence = round(max(0.50, 1.0 - overlap_ratio), 4)

        wall_time = time.time() - start_time
        return {
            "case_id": case_id,
            "predicted_label": predicted_label,
            "confidence": confidence,
            "escalation_tier": "TIER_1_FILE_SEARCH",
            "action_count": 2,
            "execution_wall_time_sec": round(wall_time, 6)
        }
