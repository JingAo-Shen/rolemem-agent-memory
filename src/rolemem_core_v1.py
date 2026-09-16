"""
RoleMem Core v1: Evidence-Scoped, Artifact-Bound Memory Engine with Selective Invalidation.
"""

from typing import List, Dict, Optional, Any, Set
import math
import re
from src.schema_v1 import MemoryRecordV1


class BM25LexicalScorer:
    """Standard BM25 scorer for memory statement retrieval."""
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b

    def _tokenize(self, text: str) -> List[str]:
        return [w.lower() for w in re.findall(r"\w+", text) if len(w) > 1]

    def score(self, query: str, document: str, doc_length: int, avg_doc_length: float, idf_dict: Dict[str, float]) -> float:
        q_tokens = self._tokenize(query)
        doc_tokens = self._tokenize(document)
        doc_tf: Dict[str, int] = {}
        for t in doc_tokens:
            doc_tf[t] = doc_tf.get(t, 0) + 1

        score = 0.0
        for token in q_tokens:
            if token in doc_tf:
                tf = doc_tf[token]
                idf = idf_dict.get(token, 0.5)
                denom = tf + self.k1 * (1.0 - self.b + self.b * (doc_length / max(1.0, avg_doc_length)))
                score += idf * (tf * (self.k1 + 1.0)) / max(1e-6, denom)
        return score


class RoleMemStoreV1:
    """Structured memory store with causal supersedes DAG, selective artifact hash verification, and role projection."""
    
    def __init__(self):
        self.records: Dict[str, MemoryRecordV1] = {}
        self.scorer = BM25LexicalScorer()

    def add_record(self, record: MemoryRecordV1) -> None:
        """Add record and enforce causal supersedes invalidation."""
        self.records[record.memory_id] = record
        
        # Causal DAG invalidation
        if record.supersedes and record.supersedes in self.records:
            parent = self.records[record.supersedes]
            parent.status = "SUPERSEDED"
            parent.valid_to = min(parent.valid_to, record.valid_from)
            self._propagate_invalidation(record.supersedes, record.valid_from)

    def _propagate_invalidation(self, parent_id: str, timestamp: float) -> None:
        """Transitively invalidate dependent child records."""
        for rec in self.records.values():
            if parent_id in rec.depends_on and rec.status == "ACTIVE":
                rec.status = "SUPERSEDED"
                rec.valid_to = min(rec.valid_to, timestamp)
                self._propagate_invalidation(rec.memory_id, timestamp)

    def selective_artifact_invalidation(self, workspace_files: Dict[str, str]) -> Set[str]:
        """
        Check physical artifact digests against current workspace files.
        Only memories referencing modified files are invalidated.
        """
        invalidated_ids: Set[str] = set()
        for rec_id, rec in self.records.items():
            if rec.status == "ACTIVE" and rec.artifact_digest and rec.artifact_uri:
                if not rec.is_artifact_valid(workspace_files):
                    rec.status = "INVALIDATED_BY_ARTIFACT"
                    invalidated_ids.add(rec_id)
        return invalidated_ids

    def retrieve(
        self,
        query: str,
        role: str,
        current_time: float,
        workspace_files: Dict[str, str],
        top_k: int = 5,
        use_validity: bool = True,
        use_artifact_hash: bool = True,
        use_role_bonus: bool = True,
        role_bonus_weight: float = 2.0
    ) -> List[MemoryRecordV1]:
        """Retrieve verified, ranked candidate memories under specified constraints."""
        
        # Step 1: Selective Invalidation
        if use_artifact_hash:
            self.selective_artifact_invalidation(workspace_files)

        candidates: List[MemoryRecordV1] = []
        for rec in self.records.values():
            # Validity filter
            if use_validity:
                if rec.status != "ACTIVE":
                    continue
                if not (rec.valid_from <= current_time < rec.valid_to):
                    continue
            
            # Artifact hash verification
            if use_artifact_hash:
                if not rec.is_artifact_valid(workspace_files):
                    continue

            candidates.append(rec)

        if not candidates:
            return []

        # Step 2: Compute IDF and Document stats
        all_docs = [r.statement for r in candidates]
        avg_len = sum(len(d.split()) for d in all_docs) / len(all_docs)
        
        idf_dict: Dict[str, float] = {}
        num_docs = len(candidates)
        for doc in all_docs:
            tokens = set(re.findall(r"\w+", doc.lower()))
            for t in tokens:
                idf_dict[t] = idf_dict.get(t, 0.0) + 1.0
        
        for t, df in idf_dict.items():
            idf_dict[t] = math.log(1.0 + (num_docs - df + 0.5) / (df + 0.5))

        # Step 3: Score and Rank Candidates
        scored_candidates = []
        for rec in candidates:
            doc_len = len(rec.statement.split())
            base_score = self.scorer.score(query, rec.statement, doc_len, avg_len, idf_dict)
            
            # Role projection bonus
            role_bonus = 0.0
            if use_role_bonus and role in rec.role_tags:
                role_bonus = role_bonus_weight
            
            total_score = base_score + role_bonus
            scored_candidates.append((total_score, rec))

        scored_candidates.sort(key=lambda x: x[0], reverse=True)
        return [rec for _, rec in scored_candidates[:top_k]]
