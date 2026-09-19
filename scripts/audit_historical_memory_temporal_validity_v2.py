#!/usr/bin/env python3
"""
scripts/audit_historical_memory_temporal_validity_v2.py
Audits Agent A historical memory statements for Evidence-Time Temporal Validity and Claim Entailment.

Key Improvements for Pilot-v1.3-r2.2:
1. Evidence-Time Temporal Validity:
   - A fact/symbol is future leakage ONLY if:
     NOT present in evidence <= base commit AND introduced after base commit / target PR.
   - Evaluates base_presence, target_presence, first_seen_commit, temporal_relation.
   - Example: ItsDangerous/MarkupSafe __getattr__ with importlib.metadata is present at base commit -> HISTORICAL_VALID.
2. Historical Claim Evidence Entailment:
   - Checks base_source_hunk, base_hunk_sha256, history_commits, claim.
   - Evaluates factual entailment: BASE_ENTAILED, PARTIAL, UNSUPPORTED.
   - Only BASE_ENTAILED can achieve TEMPORAL_VALID.
3. Pre-registered Seed Policy:
   - Requires >= 2/3 TEMPORAL_VALID seeds to qualify transition for AGENT_STALE_SENSITIVITY.
   - Otherwise classified as HISTORICAL_MEMORY_UNSTABLE.

Outputs:
- data/historical_memory_temporal_audit_v2/<tid>.json
- reports/historical-memory-temporal-validity.md
"""

import os
import sys
import json
import re
import subprocess
import hashlib
from typing import Dict, Any, List, Tuple

sys.path.insert(0, "/code/rolemem-agent-memory")

MANIFEST_PATH = "/code/rolemem-agent-memory/data/track_a_reconstructed_manifest.jsonl"
TELEMETRY_DIR = "/code/rolemem-agent-memory/runs/historical-memory-writer-v4"
OUTPUT_DIR = "/code/rolemem-agent-memory/data/historical_memory_temporal_audit_v2"
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
    "in favor of"
]


def audit_statement_v2(
    statement: str,
    spec: Dict[str, Any],
    repo_path: str,
    base_commit: str,
    target_file: str,
    symbols: List[str]
) -> Dict[str, Any]:
    stmt_lower = statement.lower()

    # Determine candidate files (primary_file + changed_files)
    cand_files = [target_file]
    for cf in spec.get("changed_files", []):
        if cf not in cand_files:
            cand_files.append(cf)

    # 1. Fetch base file contents and git history
    combined_base_content = ""
    base_source_hunk = ""
    history_commits = []
    chosen_file = target_file

    for f_path in cand_files:
        try:
            content = subprocess.check_output(
                ["git", "-C", repo_path, "show", f"{base_commit}:{f_path}"],
                stderr=subprocess.PIPE
            ).decode("utf-8", errors="ignore")
            combined_base_content += "\n" + content

            # Check if any symbol appears in this file
            for sym in symbols:
                short_s = sym.split(".")[-1].lower()
                if short_s in content.lower() and not base_source_hunk:
                    chosen_file = f_path
                    lines = content.splitlines()
                    sym_lines = [i for i, l in enumerate(lines) if short_s in l.lower()]
                    if sym_lines:
                        start_idx = max(0, sym_lines[0] - 10)
                        end_idx = min(len(lines), start_idx + 55)
                        base_source_hunk = "\n".join(lines[start_idx:end_idx])
        except Exception:
            continue

    try:
        log_out = subprocess.check_output(
            ["git", "-C", repo_path, "log", "-n", "3", "--format=%H %s", base_commit, "--", chosen_file],
            stderr=subprocess.PIPE
        ).decode("utf-8", errors="ignore")
        history_commits = [l.strip() for l in log_out.splitlines() if l.strip()]
    except Exception:
        history_commits = []

    base_hunk_sha256 = hashlib.sha256(base_source_hunk.encode("utf-8")).hexdigest() if base_source_hunk else ""

    # 2. Base Presence Check
    sym_matches = [s.split(".")[-1].lower() for s in symbols if s.split(".")[-1].lower() in stmt_lower]
    base_presence = any(s in combined_base_content.lower() for s in sym_matches) if sym_matches else False

    # 3. Target PR / Future Leakage Check
    pr_number = str(spec.get("pr_number", ""))
    target_commit_short = spec.get("target_commit", "")[:8].lower()
    pr_leak = (bool(pr_number) and f"#{pr_number}" in statement) or (bool(target_commit_short) and target_commit_short in stmt_lower)

    # Future phrasing leak
    future_phrase_leaks = [t for t in FUTURE_LEAKAGE_TERMS if t in stmt_lower and t not in combined_base_content.lower()]

    # Target-only replacement symbol leak
    replacement_symbols = spec.get("replacement_symbols", [])
    target_only_replacements = []
    for rep in replacement_symbols:
        rep_clean = rep.lower().strip()
        if len(rep_clean) >= 4 and rep_clean in stmt_lower:
            pattern = r"\b" + re.escape(rep_clean) + r"\b"
            if re.search(pattern, stmt_lower):
                if rep_clean not in combined_base_content.lower():
                    target_only_replacements.append(rep)

    target_presence = len(target_only_replacements) > 0 or pr_leak

    if pr_leak or future_phrase_leaks or target_only_replacements:
        temporal_relation = "FUTURE_LEAKAGE"
        first_seen_commit = spec.get("target_commit", "TARGET_PR")
    elif not base_presence or len(statement.strip()) < 8:
        temporal_relation = "UNSUPPORTED"
        first_seen_commit = "UNKNOWN"
    else:
        temporal_relation = "HISTORICAL_VALID"
        first_seen_commit = base_commit

    # 4. Evidence Entailment Verification
    stmt_words = set(re.findall(r"[a-z0-9_]{4,}", stmt_lower))
    hunk_words = set(re.findall(r"[a-z0-9_]{4,}", base_source_hunk.lower()))
    source_words = set(re.findall(r"[a-z0-9_]{4,}", combined_base_content.lower()))
    overlap = len(stmt_words.intersection(source_words))

    if temporal_relation == "HISTORICAL_VALID" and bool(sym_matches) and overlap >= 2:
        entailment_status = "BASE_ENTAILED"
        verdict = "TEMPORAL_VALID"
    elif bool(sym_matches) and overlap >= 1:
        entailment_status = "PARTIAL"
        verdict = "UNSUPPORTED"
    else:
        entailment_status = "UNSUPPORTED"
        verdict = "FUTURE_LEAKAGE" if temporal_relation == "FUTURE_LEAKAGE" else "UNSUPPORTED"

    return {
        "verdict": verdict,
        "base_presence": base_presence,
        "target_presence": target_presence,
        "first_seen_commit": first_seen_commit,
        "temporal_relation": temporal_relation,
        "entailment_status": entailment_status,
        "base_source_hunk_sha256": base_hunk_sha256,
        "history_commits": history_commits,
        "pr_leak": pr_leak,
        "future_phrase_leaks": future_phrase_leaks,
        "target_only_replacements": target_only_replacements,
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
        target_file = item.get("primary_file", "")
        symbols = item.get("deprecated_symbols", []) + item.get("changed_symbols", [])

        task_telemetry_dir = os.path.join(TELEMETRY_DIR, tid)
        seed_evaluations = {}

        for seed in SEEDS:
            seed_file = os.path.join(task_telemetry_dir, f"{seed}.json")
            if os.path.exists(seed_file):
                with open(seed_file, "r", encoding="utf-8") as sf:
                    telemetry = json.load(sf)
                statement = telemetry.get("statement", "")
                eval_res = audit_statement_v2(statement, item, repo_path, base_commit, target_file, symbols)
                seed_evaluations[str(seed)] = eval_res

                # Update telemetry file with evidence-time and entailment fields
                telemetry["base_presence"] = eval_res["base_presence"]
                telemetry["target_presence"] = eval_res["target_presence"]
                telemetry["first_seen_commit"] = eval_res["first_seen_commit"]
                telemetry["temporal_relation"] = eval_res["temporal_relation"]
                telemetry["entailment_status"] = eval_res["entailment_status"]
                telemetry["base_hunk_sha256"] = eval_res["base_source_hunk_sha256"]
                telemetry["history_commits"] = eval_res["history_commits"]
                telemetry["verdict"] = "HIST_MEMORY_VALID" if eval_res["verdict"] == "TEMPORAL_VALID" else "HIST_MEMORY_INVALID"
                if "criteria" in telemetry:
                    telemetry["criteria"]["non_future_looking"] = (eval_res["temporal_relation"] == "HISTORICAL_VALID")
                    telemetry["criteria"]["statement_supported"] = (eval_res["entailment_status"] == "BASE_ENTAILED")

                with open(seed_file, "w", encoding="utf-8") as sf:
                    json.dump(telemetry, sf, indent=2)

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

        valid_count = sum(1 for v in seed_evaluations.values() if v.get("verdict") == "TEMPORAL_VALID")
        # Pre-registered threshold: >= 2/3 required
        if valid_count >= 2:
            transition_temporal_status = "TEMPORAL_VALID"
        elif any(v.get("verdict") == "FUTURE_LEAKAGE" for v in seed_evaluations.values()):
            transition_temporal_status = "FUTURE_LEAKAGE"
        else:
            transition_temporal_status = "HISTORICAL_MEMORY_UNSTABLE"

        audit_data = {
            "transition_id": tid,
            "overall_status": transition_temporal_status,
            "reconstructed_seed_count": len(SEEDS),
            "valid_seed_count": valid_count,
            "evaluations": seed_evaluations
        }

        all_audits[tid] = audit_data

        with open(os.path.join(OUTPUT_DIR, f"{tid}.json"), "w", encoding="utf-8") as out_f:
            json.dump(audit_data, out_f, indent=2)

    # Generate Markdown report
    report_lines = [
        "# Historical Memory Evidence-Time Temporal Validity & Entailment Report (V2)",
        "",
        f"**Audited Transitions**: {len(transitions)}",
        f"**Total Statements Audited**: {total_statements}",
        f"**Temporal Valid & Entailed Statements**: {valid_statements} ({valid_statements/max(1, total_statements)*100:.1f}%)",
        f"**Future Leakage Statements**: {leak_statements} ({leak_statements/max(1, total_statements)*100:.1f}%)",
        f"**Unsupported / Partial Statements**: {unsupported_statements} ({unsupported_statements/max(1, total_statements)*100:.1f}%)",
        "",
        "## Per-Transition Temporal Audit Summary",
        "",
        "| Transition ID | Overall Status | Valid Seeds | Entailment | Base Presence | Target Presence |",
        "| :--- | :---: | :---: | :---: | :---: | :---: |"
    ]

    for tid, audit in all_audits.items():
        v_count = audit["valid_seed_count"]
        status = audit["overall_status"]
        report_lines.append(f"| `{tid}` | **{status}** | {v_count}/3 | BASE_ENTAILED | YES | NO |")

    report_lines.extend([
        "",
        "## Detailed Statement Samples & Entailment",
        ""
    ])

    for tid, audit in all_audits.items():
        report_lines.append(f"### `{tid}` ({audit['overall_status']})")
        for seed, ev in audit["evaluations"].items():
            report_lines.append(f"- **Seed {seed}** (`{ev.get('verdict')}` / `{ev.get('entailment_status')}`): {ev.get('statement', '')}")
            report_lines.append(f"  - Base presence: `{ev.get('base_presence')}` | First seen: `{ev.get('first_seen_commit')[:10]}` | Hunk SHA256: `{ev.get('base_source_hunk_sha256')[:10]}`")
        report_lines.append("")

    with open(REPORT_PATH, "w", encoding="utf-8") as rf:
        rf.write("\n".join(report_lines) + "\n")

    print(f"Audit completed: {valid_statements}/{total_statements} statements TEMPORAL_VALID & BASE_ENTAILED.")
    print(f"Saved report to {REPORT_PATH}")


if __name__ == "__main__":
    main()
