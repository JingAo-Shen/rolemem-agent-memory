#!/usr/bin/env python3
"""
scripts/audit_repo_context_leakage_v5.py
Formal Evidence-Backed Repository Context Leakage Audit V5.

Enhancements:
1. Fixes header parsing to accurately match `# File: <path> (Lines <start>-<end>)`.
2. TRIVIALIZES_MIGRATION / TRIVIALIZES_TASK detection:
   - Direct definition of target wrapper/function
   - Direct execution/replacement statements matching valid solution (e.g. importlib.metadata.version in Jinja/MarkupSafe)
3. Multi-line AST normalized code matching for NEAR_SOLUTION.
4. Comprehensive classification: TRIVIALIZES_TASK, NEAR_SOLUTION, HINTED, NONTRIVIAL.

Outputs:
- data/repo_context_leakage_v5/<tid>.json
- reports/repo-context-leakage-v5.md
"""

import os
import sys
import json
import glob
import re
import ast
from typing import Dict, Any, List, Set, Tuple

sys.path.insert(0, "/code/rolemem-agent-memory")
from src.bm25_retriever import RepoBM25Retriever
from scripts.run_causal_counterfactual_v2 import load_workspace

SPECS_DIR = "/code/rolemem-agent-memory/data/specs"
FIXTURES_DIR = "/code/rolemem-agent-memory/fixtures_v2"
OUT_DIR = "/code/rolemem-agent-memory/data/repo_context_leakage_v5"
REPORT_PATH = "/code/rolemem-agent-memory/reports/repo-context-leakage-v5.md"

os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)


class SimpleTokenizer:
    def encode(self, text: str, add_special_tokens: bool = False):
        return re.findall(r"\w+|[^\w\s]", text)

    def decode(self, tokens: List[str]):
        return " ".join(tokens)


def normalize_code_snippet(code: str) -> str:
    return re.sub(r"\s+", " ", code).strip()


def audit_repo_leakage_v5(spec: Dict[str, Any]) -> Dict[str, Any]:
    tid = spec["transition_id"]
    task_prompt = spec.get("current_task", "")
    target_sym = spec.get("target_symbol", "")
    target_file = spec.get("target_file", "")
    replacements = spec.get("replacement_symbols", [])
    valid_sol = spec.get("valid_solution", "")

    fixture_dir = os.path.join(FIXTURES_DIR, tid)
    after_dir = os.path.join(fixture_dir, "after")
    if not os.path.exists(after_dir):
        repo_short = spec["repo_name"].split("/")[-1]
        after_dir = f"/code/repo_cache/{repo_short}"

    target_ws = load_workspace(after_dir)
    retriever = RepoBM25Retriever(target_ws)
    s_tokenizer = SimpleTokenizer()
    
    retrieved_context, retrieved_tokens = retriever.retrieve_context(
        query=task_prompt,
        tokenizer=s_tokenizer,
        max_tokens=1200
    )

    # Correct header parser for '# File: <path> (Lines ...)'
    retrieved_files = re.findall(r"^# File:\s+(.*?)\s+\(Lines", retrieved_context, re.MULTILINE)

    norm_context = normalize_code_snippet(retrieved_context)

    # 1. Check TRIVIALIZES_TASK
    target_func_def = False
    if target_sym and f"def {target_sym}(" in retrieved_context:
        target_func_def = True

    # 2. Check TRIVIALIZES_MIGRATION (exact critical statement present in context)
    trivializes_migration = False
    migration_evidence = ""
    if valid_sol:
        # Check single-line or key expressions from valid solution in context
        lines = [l.strip() for l in valid_sol.splitlines() if l.strip() and not l.strip().startswith("#") and not l.strip().startswith("def ")]
        for line in lines:
            if len(line) > 25 and line in retrieved_context:
                trivializes_migration = True
                migration_evidence = line
                break

    # 3. Check NEAR_SOLUTION (multi-line AST block)
    near_solution = False
    if valid_sol:
        try:
            tree = ast.parse(valid_sol)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    body_stmts = [ast.unparse(s) for s in node.body if not isinstance(s, ast.Expr) or not isinstance(s.value, ast.Constant)]
                    if len(body_stmts) >= 2:
                        norm_body = normalize_code_snippet(" ".join(body_stmts))
                        if len(norm_body) > 30 and norm_body in norm_context:
                            near_solution = True
                            break
        except Exception:
            pass

    # 4. Check HINTED
    hinted_terms = []
    for r in replacements:
        r_short = r.split(".")[-1].split("(")[0]
        if len(r_short) > 2 and r_short in retrieved_context:
            hinted_terms.append(r_short)

    for word in ["deprecated", "use instead", "replaced by", "migration", "superseded"]:
        if word in retrieved_context.lower():
            hinted_terms.append(word)

    hinted_terms = list(set(hinted_terms))
    is_hinted = len(hinted_terms) > 0

    if target_func_def or trivializes_migration:
        leakage_level = "REPO_CONTEXT_TRIVIALIZES_TASK"
    elif near_solution:
        leakage_level = "REPO_CONTEXT_NEAR_SOLUTION"
    elif is_hinted:
        leakage_level = "REPO_CONTEXT_HINTED"
    else:
        leakage_level = "REPO_CONTEXT_NONTRIVIAL"

    return {
        "transition_id": tid,
        "repo_name": spec["repo_name"],
        "leakage_level": leakage_level,
        "retrieved_tokens": retrieved_tokens,
        "retrieved_files": retrieved_files,
        "hinted_terms_found": hinted_terms,
        "target_func_def_found": target_func_def,
        "trivializes_migration": trivializes_migration,
        "migration_evidence": migration_evidence,
        "near_solution_found": near_solution,
        "retrieved_context_excerpt": retrieved_context[:500]
    }


def run_all_repo_leakage_v5():
    spec_files = sorted(glob.glob(f"{SPECS_DIR}/trans_track_a_*.json"))
    results = {}
    counts = {}

    for p in spec_files:
        with open(p, "r", encoding="utf-8") as f:
            spec = json.load(f)
        tid = spec["transition_id"]
        res = audit_repo_leakage_v5(spec)
        results[tid] = res
        level = res["leakage_level"]
        counts[level] = counts.get(level, 0) + 1

        with open(f"{OUT_DIR}/{tid}.json", "w", encoding="utf-8") as f:
            json.dump(res, f, indent=2)

    total = len(results)
    print(f"=== Repo Context Leakage Audit V5 ({total} transitions) ===")
    for k, v in sorted(counts.items()):
        print(f"  {k}: {v}/{total} ({v/total*100:.1f}%)")

    # Generate reports/repo-context-leakage-v5.md
    md = []
    md.append("# Repository Context Leakage Audit Report V5\n")
    md.append("## Executive Summary\n")
    md.append(f"- **Total Transitions Evaluated**: {total}")
    md.append("- **Retriever**: `RepoBM25Retriever` (Deterministic Okapi BM25, max_tokens=1200)")
    md.append("- **Audit Metric**: Evaluates whether real retrieved workspace context gives away target solutions.\n")
    md.append("## Leakage Level Distribution\n")
    for k, v in sorted(counts.items()):
        md.append(f"- `{k}`: {v} / {total} ({v/total*100:.1f}%)")
    md.append("")
    md.append("## Detailed Audit Table\n")
    md.append("| Transition ID | Leakage Level | Files Retrieved | Tokens | Hints Found |")
    md.append("| :--- | :--- | :--- | :---: | :--- |")
    for tid, r in results.items():
        files_str = ", ".join(r["retrieved_files"][:2]) + (f" (+{len(r['retrieved_files'])-2})" if len(r["retrieved_files"]) > 2 else "")
        hints_str = ", ".join(r["hinted_terms_found"]) if r["hinted_terms_found"] else "None"
        md.append(f"| `{tid}` | `{r['leakage_level']}` | `{files_str or 'None'}` | {r['retrieved_tokens']} | {hints_str} |")
    md.append("")

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")

    print(f"Generated {REPORT_PATH} successfully.")


if __name__ == "__main__":
    run_all_repo_leakage_v5()
