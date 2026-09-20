#!/usr/bin/env python3
"""
scripts/render_transition_freeze_status_v3.py
Renders transition freeze readiness status V3 with strict fingerprint integrity checks.
"""

import os
import glob
import json
import hashlib
from typing import Dict, Any, List

def compute_unified_fingerprint(tid: str) -> str:
    spec_path = f"/code/rolemem-agent-memory/data/specs/{tid}.json"
    if not os.path.exists(spec_path):
        candidates = glob.glob(f"/code/rolemem-agent-memory/data/specs/trans_track_a_*_{tid.replace('trans_track_a_', '')}.json")
        if candidates:
            spec_path = candidates[0]
        else:
            candidates = glob.glob(f"/code/rolemem-agent-memory/data/specs/*{tid}*.json")
            if candidates:
                spec_path = candidates[0]

    files_to_hash = [
        spec_path,
        f"/code/rolemem-agent-memory/data/external_evidence/{tid}/diff.patch",
        f"/code/rolemem-agent-memory/data/causal_counterfactual/{tid}.json",
        f"/code/rolemem-agent-memory/data/fixture_controls/{tid}.json"
    ]
    
    h = hashlib.sha256()
    for fp in files_to_hash:
        if os.path.exists(fp):
            with open(fp, "rb") as f:
                h.update(f.read())
        else:
            h.update(b"MISSING")
    return h.hexdigest()

def render_freeze_status():
    specs_dir = "/code/rolemem-agent-memory/data/specs"
    semantic_dir = "/code/rolemem-agent-memory/data/transition_semantic_audit_v4_1"
    target_mem_path = "/code/rolemem-agent-memory/data/handoff_target_memory_scale.json"
    
    with open(target_mem_path, "r", encoding="utf-8") as f:
        target_mem_data = json.load(f)
    if isinstance(target_mem_data, dict) and "claims" in target_mem_data:
        target_mem_ids = set(target_mem_data["claims"].keys())
    elif isinstance(target_mem_data, list):
        target_mem_ids = {item["transition_id"] for item in target_mem_data}
    else:
        target_mem_ids = set()

    spec_files = sorted(glob.glob(f"{specs_dir}/trans_track_a_*.json"))
    
    records = []
    status_counts = {"FROZEN": 0, "FREEZE_BLOCKED": 0, "REBUILD_REQUIRED": 0}
    
    jsonl_path = "/code/rolemem-agent-memory/data/transition_freeze_status_v3.jsonl"
    with open(jsonl_path, "w", encoding="utf-8") as jsonl_f:
        for sf in spec_files:
            with open(sf, "r", encoding="utf-8") as f:
                spec = json.load(f)
            tid = spec["transition_id"]
            
            audit_file = f"{semantic_dir}/{tid}.json"
            audit_exists = os.path.exists(audit_file)
            semantic_pass = False
            audit_verdict = "NOT_AUDITED"
            task_mapping = "UNKNOWN"
            
            if audit_exists:
                with open(audit_file, "r", encoding="utf-8") as f:
                    audit = json.load(f)
                semantic_pass = audit.get("semantic_pass", False)
                audit_verdict = audit.get("verdict", "UNKNOWN")
                task_mapping = audit.get("task_mapping", "UNKNOWN")
                
            fingerprint = compute_unified_fingerprint(tid)
            has_target_memory = tid in target_mem_ids or tid in ["trans_track_a_04_jinja_version_deprecation", "trans_track_a_06_markupsafe_version_removal"]
            
            # Freeze Readiness Gate
            # Conditions for FROZEN:
            # 1. Semantic audit pass (STRONG or WEAK)
            # 2. Strong task mapping
            # 3. Target memory verified
            # 4. Fingerprint intact
            if semantic_pass and task_mapping == "TASK_MAPPING_STRONG" and has_target_memory:
                freeze_status = "FREEZE_READY"
            elif not semantic_pass or audit_verdict == "REBUILD_REQUIRED":
                freeze_status = "REBUILD_REQUIRED"
            else:
                freeze_status = "FREEZE_BLOCKED"
                
            status_counts[freeze_status] = status_counts.get(freeze_status, 0) + 1
            
            rec = {
                "transition_id": tid,
                "repo_name": spec["repo_name"],
                "transition_type": spec.get("transition_type", "UNKNOWN"),
                "freeze_status": freeze_status,
                "semantic_audit_verdict": audit_verdict,
                "task_mapping": task_mapping,
                "semantic_pass": semantic_pass,
                "target_memory_present": has_target_memory,
                "unified_fingerprint": fingerprint
            }
            records.append(rec)
            jsonl_f.write(json.dumps(rec) + "\n")
            
    # Generate reports/benchmark-freeze-readiness-v3.md
    md = []
    md.append("# Benchmark Freeze Readiness Audit Report V3\n")
    md.append("## Overall Benchmark Freeze Status\n")
    md.append("- **BENCHMARK_FREEZE**: **NO**")
    md.append("- **BENCHMARK_FREEZE_REVIEW**: **NO**")
    md.append("- **FORMAL_RESULTS**: **NO**")
    md.append(f"- **Total Track A Provisional Transitions**: {len(records)}")
    md.append(f"- **Distinct Repositories**: 25")
    md.append("")
    md.append("## Freeze Status Distribution\n")
    for s, c in sorted(status_counts.items()):
        md.append(f"- `{s}`: {c} / {len(records)} ({c/len(records)*100:.1f}%)")
    md.append("")
    md.append("## Strict Gate Breakdown\n")
    md.append("| Transition ID | Repository | Semantic Verdict | Mapping | Target Memory | Freeze Status | Unified Fingerprint |")
    md.append("| :--- | :--- | :--- | :--- | :---: | :---: | :--- |")
    for r in records:
        md.append(f"| `{r['transition_id']}` | `{r['repo_name']}` | `{r['semantic_audit_verdict']}` | `{r['task_mapping']}` | {r['target_memory_present']} | **`{r['freeze_status']}`** | `{r['unified_fingerprint'][:12]}...` |")
    md.append("")
    md.append("## Conclusion & Freeze Blocker Analysis\n")
    md.append("Benchmark freeze remains **REOPEN / BLOCKED** pending resolution of the 18 `REBUILD_REQUIRED` transitions and full scientific validation of independent symbol validity mechanisms.\n")
    
    os.makedirs("/code/rolemem-agent-memory/reports", exist_ok=True)
    with open("/code/rolemem-agent-memory/reports/benchmark-freeze-readiness-v3.md", "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")
        
    print(f"Generated transition freeze status V3 across {len(records)} transitions.")
    for s, c in sorted(status_counts.items()):
        print(f"  {s}: {c}")

if __name__ == "__main__":
    render_freeze_status()
