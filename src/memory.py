"""
RoleMem: Evidence-Scoped Role Memory Core Implementation.
Implements SQLite + JSONL storage with validity checks, role projection bonus, and conflict tracking.
"""
import sqlite3
import json
import os
import hashlib
from typing import List, Dict, Any, Optional

class RoleMemoryStore:
    def __init__(self, db_path: str = ":memory:", jsonl_log_path: Optional[str] = None):
        self.db_path = db_path
        self.jsonl_log_path = jsonl_log_path
        self.conn = sqlite3.connect(self.db_path)
        self._init_db()

    def _init_db(self):
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memory_records (
                id TEXT PRIMARY KEY,
                task_scope TEXT,
                type TEXT,
                statement TEXT,
                evidence_ids TEXT,
                created_at INTEGER,
                valid_from INTEGER,
                valid_to INTEGER,
                supersedes TEXT,
                status TEXT,
                role_tags TEXT,
                artifact_hash TEXT
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_scope ON memory_records(task_scope)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_validity ON memory_records(valid_from, valid_to)")
        self.conn.commit()

    def write_record(self, record: Dict[str, Any], as_of: int) -> str:
        """
        Writes a structured memory record with validity time bounds and artifact hash.
        """
        rec_id = record.get("id") or f"mem_{hashlib.md5((record.get('statement', '') + str(as_of)).encode()).hexdigest()[:8]}"
        task_scope = record.get("task_scope", "global")
        rec_type = record.get("type", "fact")
        statement = record.get("statement", "")
        evidence_ids = json.dumps(record.get("evidence_ids", []))
        created_at = as_of
        valid_from = record.get("valid_from", as_of)
        valid_to = record.get("valid_to", 999999999)
        supersedes = record.get("supersedes", None)
        status = record.get("status", "ACTIVE")
        role_tags = json.dumps(record.get("role_tags", []))
        artifact_hash = record.get("artifact_hash", "")

        cursor = self.conn.cursor()
        
        # If this record supersedes an older record, mark the older record as SUPERSEDED with valid_to = as_of
        if supersedes:
            cursor.execute("""
                UPDATE memory_records
                SET status = 'SUPERSEDED', valid_to = ?
                WHERE id = ? AND valid_to > ?
            """, (as_of, supersedes, as_of))

        cursor.execute("""
            INSERT OR REPLACE INTO memory_records 
            (id, task_scope, type, statement, evidence_ids, created_at, valid_from, valid_to, supersedes, status, role_tags, artifact_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (rec_id, task_scope, rec_type, statement, evidence_ids, created_at, valid_from, valid_to, supersedes, status, role_tags, artifact_hash))
        
        self.conn.commit()

        if self.jsonl_log_path:
            os.makedirs(os.path.dirname(self.jsonl_log_path), exist_ok=True)
            with open(self.jsonl_log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "id": rec_id,
                    "task_scope": task_scope,
                    "statement": statement,
                    "valid_from": valid_from,
                    "valid_to": valid_to,
                    "supersedes": supersedes,
                    "status": status,
                    "role_tags": record.get("role_tags", []),
                    "artifact_hash": artifact_hash,
                    "as_of": as_of
                }) + "\n")

        return rec_id

    def retrieve(
        self,
        query: str,
        role: str,
        as_of: int,
        task_scope: str = "global",
        current_artifact_hash: Optional[str] = None,
        method: str = "full",  # 'full', 'no_validity', 'no_role_bonus', 'bm25', 'recent'
        token_budget: int = 2048,
        role_bonus: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Retrieves relevant memory items adhering to validity, current artifact hashes, and role bonus.
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, task_scope, type, statement, evidence_ids, created_at, valid_from, valid_to, supersedes, status, role_tags, artifact_hash FROM memory_records")
        rows = cursor.fetchall()

        candidates = []
        for r in rows:
            rec = {
                "id": r[0],
                "task_scope": r[1],
                "type": r[2],
                "statement": r[3],
                "evidence_ids": json.loads(r[4]),
                "created_at": r[5],
                "valid_from": r[6],
                "valid_to": r[7],
                "supersedes": r[8],
                "status": r[9],
                "role_tags": json.loads(r[10]),
                "artifact_hash": r[11]
            }

            # Scope check
            if rec["task_scope"] != "global" and rec["task_scope"] != task_scope:
                continue

            # Method-specific validity check
            if method not in ["no_validity", "recent", "raw"]:
                # Temporal validity filter: valid_from <= as_of < valid_to
                if not (rec["valid_from"] <= as_of < rec["valid_to"]):
                    continue
                # Status filter
                if rec["status"] == "SUPERSEDED":
                    continue
                # Artifact Hash check (if hash is bound and changed, mark stale)
                if rec["artifact_hash"] and current_artifact_hash:
                    if rec["artifact_hash"] != current_artifact_hash:
                        continue

            # Compute lexical similarity score
            q_words = set(query.lower().split())
            stmt_words = set(rec["statement"].lower().split())
            overlap = len(q_words.intersection(stmt_words))
            base_score = overlap / max(len(q_words), 1)

            # Role projection bonus
            bonus = 0.0
            if method not in ["no_role_bonus", "bm25", "recent", "raw"]:
                if role in rec["role_tags"] or "all" in rec["role_tags"]:
                    bonus = role_bonus

            final_score = base_score + bonus
            rec["score"] = final_score
            candidates.append(rec)

        # Sort by final score descending, ties broken by recency/id
        candidates.sort(key=lambda x: (x["score"], x["created_at"], x["id"]), reverse=True)

        # Apply token budget truncation (approx 4 chars per token)
        budget_chars = token_budget * 4
        current_chars = 0
        selected = []
        for c in candidates:
            c_len = len(c["statement"])
            if current_chars + c_len <= budget_chars:
                selected.append(c)
                current_chars += c_len
            else:
                break

        return selected

    def close(self):
        self.conn.close()
