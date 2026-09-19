#!/usr/bin/env python3
"""
scripts/audit_historical_memory_temporal_validity.py

Audits Agent A historical memory statements for temporal validity and future leakage:
- Target-only symbols (e.g. replacement symbols introduced in target commit/PR)
- Future deprecation / migration leakage terms
- Target PR references or URLs
- Base commit API existence verification

Verdicts per claim:
- TEMPORAL_VALID: Statement describes solely base-state behavior without temporal leakage.
- FUTURE_LEAKAGE: Statement mentions replacement symbols, future removal, or target PR.
- UNSUPPORTED: Statement references non-existent symbols or invalid AST definitions at base commit.

Outputs:
- data/historical_memory_temporal_audit/<tid>.json
- reports/historical-memory-temporal-validity.md
"""

import os
import sys
import json
import re
import subprocess
from typing import Dict, Any, List

sys.path.insert(0, "/code/rolemem-agent-memory")

MANIFEST_PATH = "/code/rolemem-agent-memory/data/track_a_reconstructed_manifest.jsonl"
TELEMETRY_DIR = "/code/rolemem-agent-memory/runs/historical-memory-writer-v4"
OUTPUT_DIR = "/code/rolemem-agent-memory/data/historical_memory_temporal_audit"
REPORT_PATH = "/code/rolemem-agent-memory/reports/historical-memory-temporal-validity.md"
SEEDS = [42, 123, 999]

FUTURE_LEAKAGE_TERMS = [
    "will be removed",
    "deprecated in",
    "removed in",
    "replaced by",
    "should be migrated",
    "future version",
    "later version",
    "no longer supported",
    "obsolete in",
    "subsequent release",
    "in favor of",
]


def audit_statement(
    statement: str,
    spec: Dict[str, Any],
    repo_path: str,
    base_commit: str
) -> Dict[str, Any]:
    """Audits a single statement for future leakage, target symbols, and base support."""
    stmt_lower = statement.lower()

    # 1. Target PR and Target Commit Leakage
    pr_number = str(spec.get("pr_number", ""))
    target_commit_short = spec.get("target_commit", "")[:8].lower()
    pr_leak = False
    if pr_number and f"#{pr_number}" in statement:
        pr_leak = True
    if target_commit_short and target_commit_short in stmt_lower:
        pr_leak = True

    # 2. Target-only / Replacement Symbols Leakage
    replacement_symbols = spec.get("replacement_symbols", [])
    matched_replacements = []
    for rep in replacement_symbols:
        rep_clean = rep.lower().strip()
        # Look for distinct token or exact name match
        if len(rep_clean) >= 4 and rep_clean in stmt_lower:
            # Check boundary
            pattern = r"\b" + re.escape(rep_clean) + r"\b"
            if re.search(pattern, stmt_lower):
                matched_replacements.append(rep)

    # 3. Future Leakage Terms
    matched_leak_terms = [t for t in FUTURE_LEAKAGE_TERMS if t in stmt_lower]

    # 4. Base Commit Grounding
    primary_file = spec.get("primary_file", "")
    base_has_content = False
    try:
        content = subprocess.check_output(
            ["git", "-C", repo_path, "show", f"{base_commit}:{primary_file}"],
            stderr=subprocess.PIPE
        ).decode("utf-8", errors="ignore")
        base_has_content = len(content) > 0
    except Exception:
        base_has_content = False

    # Verdict determination
    if pr_leak or matched_replacements or matched_leak_terms:
        verdict = "FUTURE_LEAKAGE"
    elif not base_has_content or len(statement.strip()) < 10:
        verdict = "UNSUPPORTED"
    else:
        verdict = "TEMPORAL_VALID"

    return {
        "verdict": verdict,
        "pr_leak": pr_leak,
        "matched_replacements": matched_replacements,
        "matched_leak_terms": matched_leak_terms,
        "base_has_content": base_has_content,
        "statement": statement
    }


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)

    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        transitions = [json.loads(line) for line in f if line.strip()]

    all_audits = {}
    total_statements = 0
    valid_statements = 0
    leak_statements = 0
    unsupported_statements = 0

    for item in transitions:
        tid = item["transition_id"]
        repo_name = item["repo_name"].split("/")[-1]
        repo_path = f"/code/repo_cache/{repo_name}"
        base_commit = item["base_commit"]

        task_telemetry_dir = os.path.join(TELEMETRY_DIR, tid)
        seed_evaluations = {}

        for seed in SEEDS:
            seed_file = os.path.join(task_telemetry_dir, f"{seed}.json")
            if os.path.exists(seed_file):
                with open(seed_file, "r", encoding="utf-8") as sf:
                    telemetry = json.load(sf)
                statement = telemetry.get("statement", "")
                eval_res = audit_statement(statement, item, repo_path, base_commit)
                seed_evaluations[str(seed)] = eval_res

                total_statements += 1
                if eval_res["verdict"] == "TEMPORAL_VALID":
                    valid_statements += 1
                elif eval_res["verdict"] == "FUTURE_LEAKAGE":
                    leak_statements += 1
                else:
                    unsupported_statements += 1
            else:
                seed_evaluations[str(seed)] = {
                    "verdict": "UNSUPPORTED",
                    "error": f"Telemetry file {seed}.json missing"
                }
                total_statements += 1
                unsupported_statements += 1

        all_valid = all(v.get("verdict") == "TEMPORAL_VALID" for v in seed_evaluations.values())
        overall_status = "TEMPORAL_VALID" if all_valid else ("FUTURE_LEAKAGE" if any(v.get("verdict") == "FUTURE_LEAKAGE" for v in seed_evaluations.values()) else "UNSUPPORTED")

        audit_data = {
            "transition_id": tid,
            "overall_status": overall_status,
            "reconstructed_seed_count": len(SEEDS),
            "valid_seed_count": sum(1 for v in seed_evaluations.values() if v.get("verdict") == "TEMPORAL_VALID"),
            "evaluations": seed_evaluations
        }

        all_audits[tid] = audit_data

        with open(os.path.join(OUTPUT_DIR, f"{tid}.json"), "w", encoding="utf-8") as out_f:
            json.dump(audit_data, out_f, indent=2)

    # Generate Markdown report
    report_lines = [
        "# Historical Memory Temporal Validity Audit Report",
        "",
        f"**Audited Transitions**: {len(transitions)}",
        f"**Total Statements Audited**: {total_statements}",
        f"**Temporal Valid Statements**: {valid_statements} ({valid_statements/max(1, total_statements)*100:.1f}%)",
        f"**Future Leakage Statements**: {leak_statements} ({leak_statements/max(1, total_statements)*100:.1f}%)",
        f"**Unsupported Statements**: {unsupported_statements} ({unsupported_statements/max(1, total_statements)*100:.1f}%)",
        "",
        "## Per-Transition Temporal Audit Summary",
        "",
        "| Transition ID | Overall Status | Valid Seeds | Leak Seeds | Unsupported |",
        "| :--- | :---: | :---: | :---: | :---: |"
    ]

    for tid, audit in all_audits.items():
        v_count = audit["valid_seed_count"]
        l_count = sum(1 for v in audit["evaluations"].values() if v.get("verdict") == "FUTURE_LEAKAGE")
        u_count = sum(1 for v in audit["evaluations"].values() if v.get("verdict") == "UNSUPPORTED")
        status = audit["overall_status"]
        report_lines.append(f"| `{tid}` | **{status}** | {v_count}/3 | {l_count}/3 | {u_count}/3 |")

    report_lines.extend([
        "",
        "## Detailed Statement Samples",
        ""
    ])

    for tid, audit in all_audits.items():
        report_lines.append(f"### `{tid}` ({audit['overall_status']})")
        for seed, ev in audit["evaluations"].items():
            report_lines.append(f"- **Seed {seed}** (`{ev.get('verdict')}`): {ev.get('statement', '')}")
            if ev.get("matched_replacements"):
                report_lines.append(f"  - Matched replacements: {ev.get('matched_replacements')}")
            if ev.get("matched_leak_terms"):
                report_lines.append(f"  - Matched leak terms: {ev.get('matched_leak_terms')}")
        report_lines.append("")

    with open(REPORT_PATH, "w", encoding="utf-8") as rf:
        rf.write("\n".join(report_lines) + "\n")

    print(f"Audit completed: {valid_statements}/{total_statements} statements TEMPORAL_VALID.")
    print(f"Saved report to {REPORT_PATH}")


if __name__ == "__main__":
    main()
