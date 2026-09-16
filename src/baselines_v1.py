"""
Rigorous Baseline Implementations for Dynamic Agent Memory Benchmarks.
Guarantees distinct execution logic across all conditions (No Aliasing).
All non-B0 baselines enforce strict token budgeting via MemoryBudgeter and deepcopy state isolation.
"""

from typing import List, Dict, Optional, Tuple
import copy
from src.schema_v1 import MemoryRecordV1
from src.rolemem_core_v1 import RoleMemStoreV1
from src.budgeter import MemoryBudgeter


class BaselineRunnerV1:
    """Dispatches distinct memory representation strategies with strict information budgeting and state isolation."""

    @staticmethod
    def run_B0_no_memory(
        query: str,
        role: str,
        current_time: float,
        workspace_files: Dict[str, str],
        all_memories: List[MemoryRecordV1],
        budgeter: Optional[MemoryBudgeter] = None
    ) -> Tuple[str, int]:
        """B0: Zero historical memory. Agent receives only current task & workspace state."""
        return "", 0

    @staticmethod
    def run_B1_recent_raw_history(
        query: str,
        role: str,
        current_time: float,
        workspace_files: Dict[str, str],
        all_memories: List[MemoryRecordV1],
        budgeter: Optional[MemoryBudgeter] = None,
        max_items: int = 10
    ) -> Tuple[str, int]:
        """B1: Recent raw history under equal token budget (reverse chronological, unvalidated)."""
        b = budgeter or MemoryBudgeter(max_memory_tokens=512)
        # Deepcopy to prevent cross-method mutation
        isolated_mems = copy.deepcopy(all_memories)
        sorted_mems = sorted(isolated_mems, key=lambda m: m.observed_at, reverse=True)
        recent = sorted_mems[:max_items]
        return b.format_and_budget(recent, header="### Recent Activity History (Unfiltered)")

    @staticmethod
    def run_B2_chronological_history(
        query: str,
        role: str,
        current_time: float,
        workspace_files: Dict[str, str],
        all_memories: List[MemoryRecordV1],
        budgeter: Optional[MemoryBudgeter] = None
    ) -> Tuple[str, int]:
        """B2: Chronological activity history formatted under strict token budget."""
        b = budgeter or MemoryBudgeter(max_memory_tokens=512)
        isolated_mems = copy.deepcopy(all_memories)
        sorted_mems = sorted(isolated_mems, key=lambda m: m.observed_at)
        return b.format_and_budget(sorted_mems, header="### Chronological Activity History")

    @staticmethod
    def run_B3_bm25_unscoped(
        query: str,
        role: str,
        current_time: float,
        workspace_files: Dict[str, str],
        all_memories: List[MemoryRecordV1],
        budgeter: Optional[MemoryBudgeter] = None,
        top_k: int = 10
    ) -> Tuple[str, int]:
        """B3: Genuine BM25 lexical retrieval over all historical records without validity filtering."""
        b = budgeter or MemoryBudgeter(max_memory_tokens=512)
        isolated_mems = copy.deepcopy(all_memories)
        store = RoleMemStoreV1()
        for m in isolated_mems:
            store.records[m.memory_id] = m
        
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
        return b.format_and_budget(results, header="### Retrieved Project Context (BM25 Unscoped)")

    @staticmethod
    def run_B4_bm25_temporal(
        query: str,
        role: str,
        current_time: float,
        workspace_files: Dict[str, str],
        all_memories: List[MemoryRecordV1],
        budgeter: Optional[MemoryBudgeter] = None,
        top_k: int = 10
    ) -> Tuple[str, int]:
        """B4: BM25 lexical retrieval filtered by explicit logical validity window [valid_from, valid_to]."""
        b = budgeter or MemoryBudgeter(max_memory_tokens=512)
        isolated_mems = copy.deepcopy(all_memories)
        store = RoleMemStoreV1()
        for m in isolated_mems:
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
        return b.format_and_budget(results, header="### Retrieved Project Context (BM25 + Temporal Filter)")

    @staticmethod
    def run_B5_memstrata_temporal_supersession(
        query: str,
        role: str,
        current_time: float,
        workspace_files: Dict[str, str],
        all_memories: List[MemoryRecordV1],
        budgeter: Optional[MemoryBudgeter] = None,
        top_k: int = 10
    ) -> Tuple[str, int]:
        """
        B5: MemStrata baseline principles: Causal DAG supersedes resolution + temporal validity window,
        but WITHOUT physical artifact SHA-256 verification.
        """
        b = budgeter or MemoryBudgeter(max_memory_tokens=512)
        isolated_mems = copy.deepcopy(all_memories)
        store = RoleMemStoreV1()
        for m in isolated_mems:
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
        return b.format_and_budget(results, header="### Retrieved Project Context (MemStrata Temporal Supersession)")

    @staticmethod
    def run_F_rolemem_full(
        query: str,
        role: str,
        current_time: float,
        workspace_files: Dict[str, str],
        all_memories: List[MemoryRecordV1],
        budgeter: Optional[MemoryBudgeter] = None,
        top_k: int = 10
    ) -> Tuple[str, int]:
        """
        F: RoleMem (Ours): Full artifact-grounded SHA-256 digest verification,
        causal supersedes DAG, temporal validity window, and role-conditioned retrieval.
        """
        b = budgeter or MemoryBudgeter(max_memory_tokens=512)
        isolated_mems = copy.deepcopy(all_memories)
        store = RoleMemStoreV1()
        for m in isolated_mems:
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
        return b.format_and_budget(results, header="### Evidence-Scoped Role Memory (RoleMem)")
