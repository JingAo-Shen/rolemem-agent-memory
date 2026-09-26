"""
src/rolemem/retriever.py

RoleMem Role-Aware Hybrid Retriever:
Implements role-gated, BM25-lexical, dense-similarity, and confidence-weighted retrieval.
Formula:
  Score_RoleMem(q, m) = I(RoleMatch(q, m)) * [ alpha * BM25(q, m) + beta * Dense(q, m) + omega * gamma_m ]
"""

from __future__ import annotations
from typing import List, Dict, Tuple, Optional, Set, Any
import math
import re
from .schema import RoleMemoryRecord, RoleEnum, MemoryStatus
from .store import RoleMemStore


class BM25RetrieverScorer:
    """Standard Okapi BM25 scorer over memory text documents."""

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b

    def tokenize(self, text: str) -> List[str]:
        """Tokenize text into lowercase alphanumeric stems."""
        return [w.lower() for w in re.findall(r"[A-Za-z0-9_]+", text) if len(w) > 1]

    def score(
        self,
        query_tokens: List[str],
        doc_tokens: List[str],
        avg_doc_len: float,
        idf_dict: Dict[str, float]
    ) -> float:
        """Compute BM25 relevance score for a document."""
        if not doc_tokens:
            return 0.0
        doc_len = len(doc_tokens)
        doc_tf: Dict[str, int] = {}
        for t in doc_tokens:
            doc_tf[t] = doc_tf.get(t, 0) + 1

        score = 0.0
        for token in query_tokens:
            if token in doc_tf:
                tf = doc_tf[token]
                idf = idf_dict.get(token, 0.5)
                denom = tf + self.k1 * (1.0 - self.b + self.b * (doc_len / max(1.0, avg_doc_len)))
                score += idf * (tf * (self.k1 + 1.0)) / max(1e-6, denom)
        return score


class RoleAwareRetriever:
    """
    Role-Aware Multi-Channel Retriever for RoleMem:
    Combines strict epistemic role-gating with lexical BM25, semantic overlap, and belief confidence.
    """

    def __init__(
        self,
        store: RoleMemStore,
        alpha: float = 1.0,      # BM25 weight
        beta: float = 0.5,       # Semantic / Jaccard similarity weight
        omega: float = 0.3,      # Confidence weighting
        k1: float = 1.5,
        b: float = 0.75
    ):
        self.store = store
        self.alpha = alpha
        self.beta = beta
        self.omega = omega
        self.bm25 = BM25RetrieverScorer(k1=k1, b=b)

    def _build_doc_repr(self, record: RoleMemoryRecord) -> str:
        """Construct comprehensive searchable document representation from record."""
        slots = record.claim.structured_claim
        slot_text = " ".join(f"{k} {v}" for k, v in slots.items())
        return f"{record.claim.raw_statement} {slot_text} {record.evidence.evidence_snippet} {record.claim.claim_type} {record.role.value}"

    def _compute_dense_similarity(self, query_tokens: List[str], doc_tokens: List[str]) -> float:
        """Compute character-ngram or token Jaccard semantic similarity."""
        if not query_tokens or not doc_tokens:
            return 0.0
        q_set = set(query_tokens)
        d_set = set(doc_tokens)
        intersection = len(q_set & d_set)
        union = len(q_set | d_set)
        return intersection / union if union > 0 else 0.0

    def retrieve(
        self,
        query: str,
        target_role: Optional[RoleEnum] = None,
        repository: Optional[str] = None,
        top_k: int = 5,
        active_only: bool = True,
        min_score: float = 0.0
    ) -> List[Tuple[RoleMemoryRecord, float]]:
        """
        Execute role-aware hybrid retrieval.
        Returns ranked list of (record, score) tuples.
        """
        # Step 1: Filter candidates by role & repository
        if target_role:
            candidates = self.store.filter_by_role(target_role, active_only=active_only)
        else:
            candidates = self.store.get_active() if active_only else self.store.get_all()

        if repository:
            candidates = [r for r in candidates if r.claim.repository_name == repository or not r.claim.repository_name]

        if not candidates:
            return []

        # Step 2: Prepare Corpus and compute IDF
        query_tokens = self.bm25.tokenize(query)
        doc_tokens_list = [self.bm25.tokenize(self._build_doc_repr(r)) for r in candidates]
        num_docs = len(candidates)
        avg_doc_len = sum(len(dt) for dt in doc_tokens_list) / max(1, num_docs)

        df_dict: Dict[str, int] = {}
        for dt in doc_tokens_list:
            for token in set(dt):
                df_dict[token] = df_dict.get(token, 0) + 1

        idf_dict: Dict[str, float] = {}
        for token, df in df_dict.items():
            idf_dict[token] = math.log(1.0 + (num_docs - df + 0.5) / (df + 0.5))

        # Step 3: Score each candidate
        scored: List[Tuple[RoleMemoryRecord, float]] = []
        for rec, dt in zip(candidates, doc_tokens_list):
            # Role hard-gate check
            if target_role and rec.role != target_role:
                continue

            bm25_score = self.bm25.score(query_tokens, dt, avg_doc_len, idf_dict)
            dense_score = self._compute_dense_similarity(query_tokens, dt)
            conf_bonus = rec.confidence

            total_score = (self.alpha * bm25_score) + (self.beta * dense_score) + (self.omega * conf_bonus)
            if total_score >= min_score:
                scored.append((rec, round(total_score, 4)))

        # Step 4: Sort descending
        scored.sort(key=lambda item: item[1], reverse=True)
        return scored[:top_k]
