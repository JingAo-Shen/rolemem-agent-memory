"""
Rigorous Baseline Implementations for Dynamic Agent Memory Benchmarks.
Guarantees distinct execution logic across all conditions (No Aliasing).
"""

from typing import List, Dict, Optional
from src.schema_v1 import MemoryRecordV1
from src.rolemem_core_v1 import RoleMemStoreV1, BM25LexicalScorer
import math
import re


def format_memory_block(records: List[MemoryRecordV1], header: str = "### Historical Context & Project Memory") -> str:
    """Format retrieved memory records into a standardized markdown context block."""
    if not records:
        return ""
    lines = [header, ""]
    for r in records:
        evidence_str = f" [Evidence: {r.evidence_type} ({r.evidence_ref})]" if r.evidence_ref else ""
        artifact_str = f" [Artifact: {r.artifact_uri}]" if r.artifact_uri else ""
        lines.append(f"- **{r.memory_id}** ({r.artifact_type}){artifact_str}: {r.statement}{evidence_str}")
    lines.append("")
    return "\n".join(lines)


class BaselineRunnerV1:
    """Dispatches distinct memory representation strategies with strict information budgeting."""

    @staticmethod
    def run_B0_no_memory(
        query: str,
        role: str,
        current_time: float,
        workspace_files: Dict[str, str],
        all_memories: List[MemoryRecordV1]
    ) -> str:
        """B0: Zero historical memory. Agent receives only current task & workspace state."""
        return ""

    @staticmethod
    def run_B1_recent_raw_history(
        query: str,
        role: str,
        current_time: float,
        workspace_files: Dict[str, str],
        all_memories: List[MemoryRecordV1],
        max_items: int = 3
    ) -> str:
        """B1: Recent raw history under equal item/token budget (reverse chronological, unvalidated)."""
        sorted_mems = sorted(all_memories, key=lambda m: m.observed_at, reverse=True)
        recent = sorted_mems[:max_items]
        return format_memory_block(recent, header="### Recent Activity History (Unfiltered)")

    @staticmethod
    def run_B2_rolling_summary(
        query: str,
        role: str,
        current_time: float,
        workspace_files: Dict[str, str],
        all_memories: List[MemoryRecordV1]
    ) -> str:
        """B2: Rolling chronological summary of all observed memories without invalidation."""
        if not all_memories:
            return ""
        sorted_mems = sorted(all_memories, key=lambda m: m.observed_at)
        summary_lines = ["### Rolling Activity Summary", ""]
        for m in sorted_mems:
            summary_lines.append(f"- [t={m.observed_at:.1f}] {m.statement}")
        summary_lines.append("")
        return "\n".join(summary_lines)

    @staticmethod
    def run_B3_bm25_unscoped(
        query: str,
        role: str,
        current_time: float,
        workspace_files: Dict[str, str],
        all_memories: List[MemoryRecordV1],
        top_k: int = 3
    ) -> str:
        """B3: Genuine BM25 lexical retrieval over all historical records without validity filtering."""
        store = RoleMemStoreV1()
        for m in all_memories:
            # Store without DAG invalidation
            store.records[m.memory_id] = m
        
        # Retrieve with validity=False, artifact_hash=False, role_bonus=False
        results = store.retrieve(
            query=query,
            role=role,
            current_time=current_time,
            workspace_files=workspace_files,
            top_k=top_k,
            use_validity=False,
            use_artifact_hash=False,
            use_role_bonus=False
        )
        return format_memory_block(results, header="### Retrieved Project Context (BM25 Unscoped)")

    @staticmethod
    def run_B4_bm25_temporal(
        query: str,
        role: str,
        current_time: float,
        workspace_files: Dict[str, str],
        all_memories: List[MemoryRecordV1],
        top_k: int = 3
    ) -> str:
        """B4: BM25 lexical retrieval filtered by explicit logical validity window [valid_from, valid_to]."""
        store = RoleMemStoreV1()
        for m in all_memories:
            store.records[m.memory_id] = m
        
        results = store.retrieve(
            query=query,
            role=role,
            current_time=current_time,
            workspace_files=workspace_files,
            top_k=top_k,
            use_validity=True,
            use_artifact_hash=False,
            use_role_bonus=False
        )
        return format_memory_block(results, header="### Retrieved Project Context (BM25 + Temporal Filter)")

    @staticmethod
    def run_B5_memstrata_temporal_supersession(
        query: str,
        role: str,
        current_time: float,
        workspace_files: Dict[str, str],
        all_memories: List[MemoryRecordV1],
        top_k: int = 3
    ) -> str:
        """
        B5: MemStrata baseline principles: Causal DAG supersedes resolution + temporal validity window,
        but WITHOUT physical artifact SHA-256 verification.
        """
        store = RoleMemStoreV1()
        for m in all_memories:
            # add_record enforces DAG supersedes invalidation
            store.add_record(m)
        
        results = store.retrieve(
            query=query,
            role=role,
            current_time=current_time,
            workspace_files=workspace_files,
            top_k=top_k,
            use_validity=True,
            use_artifact_hash=False,
            use_role_bonus=False
        )
        return format_memory_block(results, header="### Retrieved Project Context (MemStrata Temporal Supersession)")

    @staticmethod
    def run_F_rolemem_full(
        query: str,
        role: str,
        current_time: float,
        workspace_files: Dict[str, str],
        all_memories: List[MemoryRecordV1],
        top_k: int = 3
    ) -> str:
        """
        F: RoleMem (Ours): Full artifact-grounded SHA-256 digest verification,
        causal supersedes DAG, temporal validity window, and role-conditioned retrieval.
        """
        store = RoleMemStoreV1()
        for m in all_memories:
            store.add_record(m)
        
        results = store.retrieve(
            query=query,
            role=role,
            current_time=current_time,
            workspace_files=workspace_files,
            top_k=top_k,
            use_validity=True,
            use_artifact_hash=True,
            use_role_bonus=True,
            role_bonus_weight=2.0
        )
        return format_memory_block(results, header="### Evidence-Scoped Role Memory (RoleMem)")
