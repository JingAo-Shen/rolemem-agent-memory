"""
src/rolemem/store.py

RoleMem Memory Store:
In-memory and JSONL-persistent store for RoleMemoryRecord instances with multi-index acceleration.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Set, Tuple, Any, Iterable
import json
import os
from .schema import RoleMemoryRecord, RoleEnum, MemoryStatus


class RoleMemStore:
    """
    Multi-indexed thread-safe memory store for RoleMemoryRecord units.
    Maintains indices over:
      - primary memory_id
      - epistemic role
      - (module, symbol) identifier
      - repository name
      - evidence file path
      - memory lifecycle status
    """

    def __init__(self):
        self._records: Dict[str, RoleMemoryRecord] = {}
        self._role_index: Dict[RoleEnum, Set[str]] = {role: set() for role in RoleEnum}
        self._symbol_index: Dict[Tuple[str, str], Set[str]] = {}
        self._repo_index: Dict[str, Set[str]] = {}
        self._path_index: Dict[str, Set[str]] = {}
        self._status_index: Dict[MemoryStatus, Set[str]] = {st: set() for st in MemoryStatus}

    def __len__(self) -> int:
        return len(self._records)

    def add_record(self, record: RoleMemoryRecord) -> None:
        """Insert or update a memory record, maintaining all secondary indices."""
        mid = record.memory_id
        if mid in self._records:
            self._remove_from_indices(self._records[mid])

        self._records[mid] = record
        self._add_to_indices(record)

    def _add_to_indices(self, record: RoleMemoryRecord) -> None:
        mid = record.memory_id
        # Role index
        self._role_index.setdefault(record.role, set()).add(mid)
        # Status index
        self._status_index.setdefault(record.status, set()).add(mid)
        # Repository index
        repo = record.claim.repository_name
        if repo:
            self._repo_index.setdefault(repo, set()).add(mid)
        # Symbol index
        mod = record.claim.structured_claim.get("module", "")
        sym = record.claim.structured_claim.get("symbol", "")
        if mod or sym:
            self._symbol_index.setdefault((mod, sym), set()).add(mid)
        # Path index
        path = record.evidence.evidence_path
        if path:
            self._path_index.setdefault(path, set()).add(mid)

    def _remove_from_indices(self, record: RoleMemoryRecord) -> None:
        mid = record.memory_id
        if record.role in self._role_index:
            self._role_index[record.role].discard(mid)
        if record.status in self._status_index:
            self._status_index[record.status].discard(mid)
        repo = record.claim.repository_name
        if repo and repo in self._repo_index:
            self._repo_index[repo].discard(mid)
        mod = record.claim.structured_claim.get("module", "")
        sym = record.claim.structured_claim.get("symbol", "")
        if (mod, sym) in self._symbol_index:
            self._symbol_index[(mod, sym)].discard(mid)
        path = record.evidence.evidence_path
        if path and path in self._path_index:
            self._path_index[path].discard(mid)

    def get(self, memory_id: str) -> Optional[RoleMemoryRecord]:
        """Retrieve memory record by primary ID."""
        return self._records.get(memory_id)

    def get_all(self) -> List[RoleMemoryRecord]:
        """Return all memory records in store."""
        return list(self._records.values())

    def get_active(self) -> List[RoleMemoryRecord]:
        """Return all ACTIVE or PRESERVED records in store."""
        active_ids = self._status_index.get(MemoryStatus.ACTIVE, set()) | self._status_index.get(MemoryStatus.PRESERVED, set())
        return [self._records[mid] for mid in active_ids if mid in self._records]

    def filter_by_role(self, role: RoleEnum, active_only: bool = True) -> List[RoleMemoryRecord]:
        """Filter memory records by epistemic role."""
        mids = self._role_index.get(role, set())
        records = [self._records[mid] for mid in mids if mid in self._records]
        if active_only:
            records = [r for r in records if r.status in (MemoryStatus.ACTIVE, MemoryStatus.PRESERVED, MemoryStatus.DOWNGRADED)]
        return records

    def filter_by_symbol(self, module: str, symbol: str, active_only: bool = True) -> List[RoleMemoryRecord]:
        """Filter memory records by module and symbol."""
        mids = self._symbol_index.get((module, symbol), set())
        records = [self._records[mid] for mid in mids if mid in self._records]
        if active_only:
            records = [r for r in records if r.status in (MemoryStatus.ACTIVE, MemoryStatus.PRESERVED, MemoryStatus.DOWNGRADED)]
        return records

    def filter_by_repository(self, repository: str, active_only: bool = True) -> List[RoleMemoryRecord]:
        """Filter memory records by repository name."""
        mids = self._repo_index.get(repository, set())
        records = [self._records[mid] for mid in mids if mid in self._records]
        if active_only:
            records = [r for r in records if r.status in (MemoryStatus.ACTIVE, MemoryStatus.PRESERVED, MemoryStatus.DOWNGRADED)]
        return records

    def update_status(self, memory_id: str, new_status: MemoryStatus, note: Optional[str] = None) -> bool:
        """Update memory record status and synchronize status index."""
        record = self.get(memory_id)
        if not record:
            return False
        old_status = record.status
        if old_status != new_status:
            self._status_index[old_status].discard(memory_id)
            record.status = new_status
            self._status_index.setdefault(new_status, set()).add(memory_id)
        if note:
            record.advisory_notes.append(note)
        return True

    def invalidate(self, memory_id: str, reason: str = "") -> bool:
        """Mark memory record as INVALIDATED and attach invalidation reason."""
        note = f"Invalidated: {reason}" if reason else "Invalidated"
        return self.update_status(memory_id, MemoryStatus.INVALIDATED, note=note)

    def export_jsonl(self, file_path: str) -> int:
        """Export all memory records to a JSONL file."""
        os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
        count = 0
        with open(file_path, "w", encoding="utf-8") as f:
            for rec in self._records.values():
                f.write(rec.to_json() + "\n")
                count += 1
        return count

    def load_jsonl(self, file_path: str) -> int:
        """Load memory records from a JSONL file into the store."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"JSONL file not found: {file_path}")
        count = 0
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    rec = RoleMemoryRecord.from_json(line)
                    self.add_record(rec)
                    count += 1
        return count
