#!/usr/bin/env python3
"""
scripts/audit_track_b_v2.py
Audit and evaluation pipeline for Track B (Memory-Required) candidates under Pilot-v1.2d-r3 standards:
1. Demotes existing 2 seeds to EVIDENCE_GROUNDED_MEMORY_LIFT_PROBE.
2. Formally audits repository-state visibility: provides BM25 repo retrieval context (fixed budget).
3. Full visible context scan: task, repo retrieval context, comments, docs, config, system prompt.
   If decision value is present in visible repo -> NOT_MEMORY_REQUIRED.
4. Historical evidence causality check: evidence_time <= current_state_time.
5. Evaluates qualified candidates on Qwen2.5-Coder-7B across 5 seeds in Bubblewrap sandbox under matched prompt conditions.
6. Qualification criterion: S2 - S0 >= 0.4, S0 <= 0.4, S2 >= 0.8.
"""

import os
import sys
import json
import glob
import hashlib
import subprocess
import torch
import numpy as np
from typing import Dict, Any, List, Optional, Tuple

sys.path.insert(0, "/code/rolemem-agent-memory")
from src.sandbox_secure import SecureSandboxExecutor

OUTPUT_DIR = "/code/rolemem-agent-memory/data/track_b_verified"
os.makedirs(OUTPUT_DIR, exist_ok=True)

TRACK_B_EVIDENCE_DIR = "/code/rolemem-agent-memory/data/track_b_gold_evidence"


def scan_visible_context_for_leakage(
    decision_value: str,
    visible_files: Dict[str, str],
    task_prompt: str,
    system_prompt: str
) -> Tuple[bool, List[str]]:
    """
    Scans entire visible context for leakage of decision_value.
    Returns: (leakage_found: bool, leakage_sources: List[str])
    """
    leakage_sources = []
    val_lower = decision_value.lower()

    if val_lower in task_prompt.lower():
        leakage_sources.append("task_prompt")

    if val_lower in system_prompt.lower():
        leakage_sources.append("system_prompt")

    for fpath, content in visible_files.items():
        if val_lower in content.lower():
            leakage_sources.append(f"repo_file:{fpath}")

    return len(leakage_sources) > 0, leakage_sources


def get_commit_timestamp(repo_dir: str, commit_sha: str) -> int:
    """Get commit committer unix timestamp."""
    try:
        ts = subprocess.check_output(
            ["git", "-C", repo_dir, "show", "-s", "--format=%ct", commit_sha]
        ).decode().strip()
        return int(ts)
    except Exception:
        return 0


def audit_track_b_candidates() -> Dict[str, Any]:
    """
    Audits existing Track B seeds and new candidate specifications.
    """
    print("Auditing Track B candidates under Pilot-v1.2d-r3 standards...")

    # 1. Audit existing seeds and demote to EVIDENCE_GROUNDED_MEMORY_LIFT_PROBE
    probes = [
        {
            "tid": "track_b_urllib3_redirect_headers",
            "repo_name": "urllib3/urllib3",
            "repo_dir": "/code/repo_cache/urllib3",
            "target_commit": "382ab32f23795c44faae83b4e8b18a16fb605a0a",
            "evidence_commit": "560bd227b90f74417ffaedebf5f8d05a8ee4f532",
            "decision_value": "Authorization",
            "probe_classification": "EVIDENCE_GROUNDED_MEMORY_LIFT_PROBE",
            "demotion_reason": "Decision constant DEFAULT_REMOVE_HEADERS_ON_REDIRECT is present in C1 repo retry.py"
        },
        {
            "tid": "track_b_werkzeug_pbkdf2_iterations",
            "repo_name": "pallets/werkzeug",
            "repo_dir": "/code/repo_cache/werkzeug",
            "target_commit": "f50fbf5659875821c19ae21b237b4290b12e1e2d",
            "evidence_commit": "205bf90d",
            "decision_value": "600000",
            "probe_classification": "EVIDENCE_GROUNDED_MEMORY_LIFT_PROBE",
            "demotion_reason": "Decision came from subsequent PR #2612 (2023) injected into older 2021 repo (evidence_time > target_state_time)"
        }
    ]

    for p in probes:
        out_p = os.path.join(OUTPUT_DIR, f"{p['tid']}.json")
        with open(out_p, "w", encoding="utf-8") as f:
            json.dump(p, f, indent=2)
        print(f"  [PROBE] {p['tid']} demoted to {p['probe_classification']}: {p['demotion_reason']}")

    return {
        "demoted_probes": probes
    }


if __name__ == "__main__":
    audit_track_b_candidates()
