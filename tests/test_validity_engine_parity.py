"""
tests/test_validity_engine_parity.py

Verifies production/experiment parity for Protocol V2.1:
Ensures that calling RoleMemValidityEngine directly and reading
from the prediction runner results produce identical decisions.
"""

import os
import json
import pytest
from src.validity import RoleMemValidityEngine

BLIND_PATH = "/code/rolemem-agent-memory/data/memory_validity_v2_1/blind_inputs.jsonl"
PRED_PATH = "/code/rolemem-agent-memory/data/memory_validity_v2_1/predictions_rolemem.jsonl"


def test_production_experiment_parity():
    assert os.path.exists(BLIND_PATH)
    assert os.path.exists(PRED_PATH)

    with open(BLIND_PATH, "r", encoding="utf-8") as f:
        blind_cases = [json.loads(line) for line in f if line.strip()]

    with open(PRED_PATH, "r", encoding="utf-8") as f:
        pred_records = {p["case_id"]: p for p in (json.loads(line) for line in f if line.strip())}

    engine = RoleMemValidityEngine()

    for c in blind_cases:
        cid = c["case_id"]
        repo = c.get("repository", "")
        repo_root = f"/code/repo_cache/{repo}" if repo else None
        res = engine.evaluate(
            memory_statement=c.get("memory_statement", ""),
            symbol_qualified_name=c.get("symbol_qualified_name", ""),
            base_source=c.get("base_source_excerpt", ""),
            target_source=c.get("target_source_excerpt", ""),
            file_path=c.get("file_path", ""),
            diff_hunk=c.get("diff_hunk", ""),
            repository_root=repo_root,
            base_commit=c.get("base_commit"),
            target_commit=c.get("target_commit")
        )

        expected_pred = "STALE" if res.decision == "STALE" else "VALID"
        stored_pred = pred_records[cid]["prediction"]

        assert expected_pred == stored_pred, f"Parity mismatch on {cid}: direct={expected_pred}, stored={stored_pred}"
