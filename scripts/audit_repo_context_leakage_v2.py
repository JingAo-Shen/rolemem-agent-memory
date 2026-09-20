#!/usr/bin/env python3
"""
scripts/audit_repo_context_leakage_v2.py
Audits repository context retrieved for each transition task.
Detects:
- Replacement symbol presence
- Replacement code patterns
- Exact task solution / target function implementation
- Migration comments or migration documentation

Classifies into three strict categories:
1. REPO_CONTEXT_NONTRIVIAL:
   Repo context does not mention replacement symbol or task solution; task requires external/historical knowledge.
2. REPO_CONTEXT_HINTED:
   Repo context contains replacement symbols or general usage, but does NOT supply the task solution.
3. REPO_CONTEXT_TRIVIALIZES_TASK:
   Repo context contains the exact target function implementation, task wrapper, or copy-paste answer.

Outputs:
- data/repo_context_leakage/<tid>.json
- reports/repo-context-leakage.md
"""

import os
import sys
import json
import glob
import re
from typing import Dict, Any, List

sys.path.insert(0, "/code/rolemem-agent-memory")
from src.bm25_retriever import RepoBM25Retriever
from scripts.run_causal_counterfactual_v2 import load_workspace

DATA_DIR = "/code/rolemem-agent-memory/data"
FIXTURES_DIR = "/code/rolemem-agent-memory/fixtures_v2"
OUTPUT_DIR = os.path.join(DATA_DIR, "repo_context_leakage")
REPORT_PATH = "/code/rolemem-agent-memory/reports/repo-context-leakage.md"
MANIFEST_PATH = os.path.join(DATA_DIR, "track_a_reconstructed_manifest.jsonl")


class SimpleTokenizer:
    def encode(self, text: str, add_special_tokens: bool = False):
        return re.findall(r"\w+|[^\w\s]", text)

    def decode(self, tokens: List[str]):
        return " ".join(tokens)


def audit_task_repo_context(spec: Dict[str, Any], workspace_dir: str) -> Dict[str, Any]:
    tid = spec["transition_id"]
    current_task = spec.get("current_task", "")
    target_symbol = spec.get("target_symbol", "")
    deprecated_symbols = spec.get("deprecated_symbols", [])
    replacement_symbols = spec.get("replacement_symbols", [])

    # Load workspace and retrieve context
    workspace_files = load_workspace(workspace_dir)
    retriever = RepoBM25Retriever(workspace_files)
    tokenizer = SimpleTokenizer()
    combined_context, token_count = retriever.retrieve_context(
        query=current_task,
        tokenizer=tokenizer,
        max_tokens=1200
    )

    context_lower = combined_context.lower()

    # 1. Replacement symbol check
    found_replacements = []
    for rep in replacement_symbols:
        rep_clean = rep.strip()
        if len(rep_clean) >= 3 and re.search(r"\b" + re.escape(rep_clean.lower()) + r"\b", context_lower):
            found_replacements.append(rep)

    # 2. Exact answer / Target function implementation check
    target_impl_found = False
    exact_pattern = ""
    if target_symbol:
        sym_clean = target_symbol.split(".")[-1]
        patterns = [
            rf"def\s+{re.escape(sym_clean)}\s*\(",
            rf"class\s+{re.escape(sym_clean)}\s*[:\(]"
        ]
        for pat in patterns:
            if re.search(pat, combined_context):
                target_impl_found = True
                exact_pattern = pat
                break

    # 3. Migration comments check
    migration_terms = [
        r"use .* instead of",
        r"deprecated.*use",
        r"replaced by",
        r"migrate from",
        r"in favor of"
    ]
    migration_comments_found = []
    for line in combined_context.splitlines():
        line_s = line.strip()
        if line_s.startswith("#") or line_s.startswith("*") or line_s.startswith('"""'):
            for mt in migration_terms:
                if re.search(mt, line_s, re.IGNORECASE):
                    migration_comments_found.append(line_s)

    # 4. Classification
    if target_impl_found:
        leakage_class = "REPO_CONTEXT_TRIVIALIZES_TASK"
        rationale = f"Target symbol implementation '{target_symbol}' found directly inside retrieved repo context."
    elif found_replacements or migration_comments_found:
        leakage_class = "REPO_CONTEXT_HINTED"
        rationale = f"Context contains replacement symbols {found_replacements} or migration comments, but no task implementation."
    else:
        leakage_class = "REPO_CONTEXT_NONTRIVIAL"
        rationale = "Retrieved repository context contains neither replacement symbols nor migration hints."

    return {
        "transition_id": tid,
        "repo_name": spec.get("repo_name"),
        "leakage_class": leakage_class,
        "rationale": rationale,
        "retrieved_tokens": token_count,
        "found_replacements": found_replacements,
        "target_implementation_found": target_impl_found,
        "migration_comments_found": migration_comments_found[:3]
    }


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)

    manifest_files = [MANIFEST_PATH]
    scale_manifest = os.path.join(DATA_DIR, "track_a_scale_manifest.jsonl")
    if os.path.exists(scale_manifest):
        manifest_files.append(scale_manifest)

    all_specs = {}
    for mf in manifest_files:
        if os.path.exists(mf):
            with open(mf, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        s = json.loads(line)
                        all_specs[s["transition_id"]] = s

    results = []
    class_counts = {
        "REPO_CONTEXT_NONTRIVIAL": 0,
        "REPO_CONTEXT_HINTED": 0,
        "REPO_CONTEXT_TRIVIALIZES_TASK": 0
    }

    for tid, spec in all_specs.items():
        after_workspace = os.path.join(FIXTURES_DIR, tid, "after")
        if not os.path.exists(after_workspace):
            continue

        audit_res = audit_task_repo_context(spec, after_workspace)
        cls = audit_res["leakage_class"]
        class_counts[cls] = class_counts.get(cls, 0) + 1

        out_p = os.path.join(OUTPUT_DIR, f"{tid}.json")
        with open(out_p, "w", encoding="utf-8") as f:
            json.dump(audit_res, f, indent=2)

        results.append(audit_res)

    total = len(results)
    nontrivial_pct = (class_counts["REPO_CONTEXT_NONTRIVIAL"] / total * 100.0) if total > 0 else 0.0
    hinted_pct = (class_counts["REPO_CONTEXT_HINTED"] / total * 100.0) if total > 0 else 0.0
    trivial_pct = (class_counts["REPO_CONTEXT_TRIVIALIZES_TASK"] / total * 100.0) if total > 0 else 0.0

    report_lines = [
        "# Repository Context Leakage Audit Report (V2)",
        "",
        "## Summary Metrics",
        "",
        f"- **Total Transitions Audited**: {total}",
        f"- **REPO_CONTEXT_NONTRIVIAL**: **{class_counts['REPO_CONTEXT_NONTRIVIAL']} / {total} ({nontrivial_pct:.1f}%)**",
        f"- **REPO_CONTEXT_HINTED**: **{class_counts['REPO_CONTEXT_HINTED']} / {total} ({hinted_pct:.1f}%)**",
        f"- **REPO_CONTEXT_TRIVIALIZES_TASK**: **{class_counts['REPO_CONTEXT_TRIVIALIZES_TASK']} / {total} ({trivial_pct:.1f}%)**",
        "",
        "> **Core Challenge Policy**: Only tasks with `REPO_CONTEXT_NONTRIVIAL` or `REPO_CONTEXT_HINTED` qualify for `AGENT_STALE_CHALLENGE_CORE`. Any task classified as `REPO_CONTEXT_TRIVIALIZES_TASK` is strictly barred from core challenge qualification and reserved for control analysis.",
        "",
        "## Detailed Evaluation Matrix",
        "",
        "| Transition ID | Repo | Classification | Found Replacements | Target Impl in Context | Migration Comments | Rationale |",
        "| :--- | :--- | :---: | :---: | :---: | :---: | :--- |"
    ]

    for r in results:
        reps = ", ".join(r["found_replacements"]) if r["found_replacements"] else "None"
        impl = "YES (LEAK)" if r["target_implementation_found"] else "Clean"
        cmts = f"{len(r['migration_comments_found'])} found" if r["migration_comments_found"] else "None"
        report_lines.append(
            f"| `{r['transition_id']}` | `{r['repo_name']}` | **{r['leakage_class']}** | `{reps}` | {impl} | {cmts} | {r['rationale'][:65]} |"
        )

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines) + "\n")

    print(f"Repo Context Leakage Audit Complete:")
    print(f"- Total: {total}")
    print(f"- REPO_CONTEXT_NONTRIVIAL: {class_counts['REPO_CONTEXT_NONTRIVIAL']} ({nontrivial_pct:.1f}%)")
    print(f"- REPO_CONTEXT_HINTED: {class_counts['REPO_CONTEXT_HINTED']} ({hinted_pct:.1f}%)")
    print(f"- REPO_CONTEXT_TRIVIALIZES_TASK: {class_counts['REPO_CONTEXT_TRIVIALIZES_TASK']} ({trivial_pct:.1f}%)")


if __name__ == "__main__":
    main()
