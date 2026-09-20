#!/usr/bin/env python3
"""
scripts/run_validity_predictions_v2_1.py

Strict Phase 1 Prediction Runner for Protocol V2.1:
- Inputs ONLY data/memory_validity_v2_1/blind_inputs.jsonl.
- ZERO access to gold labels, category metadata, or ground truth files.
- Executes production validity classes directly from src.validity:
  - FileValidityChecker
  - SymbolValidityChecker
  - DependencyValidityChecker
  - RoleMemValidityEngine
- Outputs predictions to data/memory_validity_v2_1/predictions_<mech>.jsonl.
"""

import os
import sys
import json
from typing import Dict, Any, List

sys.path.insert(0, "/code/rolemem-agent-memory")
from src.validity import (
    FileValidityChecker,
    SymbolValidityChecker,
    DependencyValidityChecker,
    RoleMemValidityEngine
)

BLIND_INPUTS_PATH = "/code/rolemem-agent-memory/data/memory_validity_v2_1/blind_inputs.jsonl"
OUT_DIR = "/code/rolemem-agent-memory/data/memory_validity_v2_1"


def run_predictions():
    print(f"Loading blind inputs from: {BLIND_INPUTS_PATH}")
    with open(BLIND_INPUTS_PATH, "r", encoding="utf-8") as f:
        blind_cases = [json.loads(line) for line in f if line.strip()]

    file_checker = FileValidityChecker()
    symbol_checker = SymbolValidityChecker()
    dep_checker = DependencyValidityChecker()
    rolemem_engine = RoleMemValidityEngine()

    predictions_file = []
    predictions_symbol = []
    predictions_dep = []
    predictions_rolemem = []
    predictions_rolemem_abstain = []

    for case in blind_cases:
        cid = case["case_id"]
        base_src = case.get("base_source_excerpt", "")
        target_src = case.get("target_source_excerpt", "")
        sym_name = case.get("symbol_qualified_name", "")
        diff_hunk = case.get("diff_hunk", "")
        mem_stmt = case.get("memory_statement", "")
        f_path = case.get("file_path", "")

        # 1. File-level baseline: File modified in diff -> STALE
        if diff_hunk and not diff_hunk.startswith("// Symbol untouched"):
            f_pred = "STALE"
            f_conf = 1.0
            f_reasons = ["File modified in Git diff hunk."]
        else:
            f_res = file_checker.evaluate(base_src, target_src, file_path=f_path)
            f_pred = f_res.decision
            f_conf = f_res.confidence
            f_reasons = f_res.reasons

        predictions_file.append({
            "case_id": cid,
            "prediction": f_pred,
            "confidence": f_conf,
            "reasons": f_reasons,
            "evidence": []
        })

        # 2. Pure Symbol AST baseline: AST modified or removed -> STALE, otherwise VALID
        s_res = symbol_checker.evaluate(base_src, target_src, sym_name)
        if s_res.decision == "STALE" or s_res.symbol_changed:
            s_pred = "STALE"
        else:
            s_pred = "VALID"

        predictions_symbol.append({
            "case_id": cid,
            "prediction": s_pred,
            "confidence": s_res.confidence,
            "reasons": s_res.reasons,
            "evidence": [e.__dict__ for e in s_res.evidence]
        })

        repo = case.get("repository", "")
        repo_root = f"/code/repo_cache/{repo}" if repo else None
        b_commit = case.get("base_commit")
        t_commit = case.get("target_commit")

        # 3. Dependency AST baseline
        d_res = dep_checker.evaluate(
            base_source=base_src,
            target_source=target_src,
            symbol_qualified_name=sym_name,
            diff_hunk=diff_hunk,
            repository_root=repo_root,
            base_commit=b_commit,
            target_commit=t_commit,
            file_path=f_path
        )
        d_pred = "STALE" if d_res.decision == "STALE" else "VALID"
        predictions_dep.append({
            "case_id": cid,
            "prediction": d_pred,
            "confidence": d_res.confidence,
            "reasons": d_res.reasons,
            "evidence": [e.__dict__ for e in d_res.evidence]
        })

        # 4. RoleMem Validity Engine (No Abstention)
        r_res = rolemem_engine.evaluate(
            memory_statement=mem_stmt,
            symbol_qualified_name=sym_name,
            base_source=base_src,
            target_source=target_src,
            file_path=f_path,
            diff_hunk=diff_hunk,
            repository_root=repo_root,
            base_commit=b_commit,
            target_commit=t_commit
        )
        if r_res.decision == "STALE":
            r_pred = "STALE"
        elif r_res.decision == "VALID":
            r_pred = "VALID"
        else:
            # UNCERTAIN: without abstention, defaults to VALID
            r_pred = "VALID"

        predictions_rolemem.append({
            "case_id": cid,
            "prediction": r_pred,
            "confidence": r_res.confidence,
            "reasons": r_res.reasons,
            "evidence": [e.__dict__ for e in r_res.evidence]
        })

        # 5. RoleMem Validity Engine (With Selective Abstention on UNCERTAIN)
        if r_res.decision == "UNCERTAIN" and r_res.confidence < 0.70:
            ra_pred = "ABSTAIN"
        else:
            ra_pred = r_res.decision if r_res.decision in ("VALID", "STALE") else "VALID"

        predictions_rolemem_abstain.append({
            "case_id": cid,
            "prediction": ra_pred,
            "confidence": r_res.confidence,
            "reasons": r_res.reasons,
            "evidence": [e.__dict__ for e in r_res.evidence]
        })

    # Save prediction files
    mechs = [
        ("file", predictions_file),
        ("symbol", predictions_symbol),
        ("dependency", predictions_dep),
        ("rolemem", predictions_rolemem),
        ("rolemem_abstain", predictions_rolemem_abstain),
    ]

    for mname, preds in mechs:
        out_path = os.path.join(OUT_DIR, f"predictions_{mname}.jsonl")
        with open(out_path, "w", encoding="utf-8") as f:
            for p in preds:
                f.write(json.dumps(p) + "\n")
        print(f"  Wrote {len(preds)} predictions to: {out_path}")

    print("=== Phase 1 Prediction Complete (100% Blind Execution) ===")


if __name__ == "__main__":
    run_predictions()
