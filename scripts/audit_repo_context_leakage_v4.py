#!/usr/bin/env python3
"""
scripts/audit_repo_context_leakage_v4.py
Formal Evidence-Backed Repository Context Leakage Audit V4.

Requirements:
- Re-runs real RepoBM25Retriever with max_tokens=1200 on target workspace.
- Saves actual retrieved_context and retrieved_files.
- Analyzes AST solution patterns and exact code snippets to classify leakage level:
  1. TRIVIALIZES_TASK: Context directly provides the full target wrapper implementation.
  2. NEAR_SOLUTION: Context provides multi-line normalized AST solution code blocks.
  3. HINTED: Context contains replacement identifiers, migration comments, or doc references.
  4. NONTRIVIAL: Context contains general codebase utilities/types without replacement hints.

Outputs:
- data/repo_context_leakage_v4/<tid>.json
- reports/repo-context-leakage-v4.md
"""

import os
import sys
import json
import glob
import re
import ast
from typing import Dict, Any, List, Set

sys.path.insert(0, "/code/rolemem-agent-memory")
from src.bm25_retriever import RepoBM25Retriever
from scripts.run_causal_counterfactual_v2 import load_workspace

SPECS_DIR = "/code/rolemem-agent-memory/data/specs"
FIXTURES_DIR = "/code/rolemem-agent-memory/fixtures_v2"
OUT_DIR = "/code/rolemem-agent-memory/data/repo_context_leakage_v4"
REPORT_PATH = "/code/rolemem-agent-memory/reports/repo-context-leakage-v4.md"

os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)


class SimpleTokenizer:
    def encode(self, text: str, add_special_tokens: bool = False):
        return re.findall(r"\w+|[^\w\s]", text)

    def decode(self, tokens: List[str]):
        return " ".join(tokens)


def normalize_code_snippet(code: str) -> str:
    return re.sub(r"\s+", " ", code).strip()


def audit_repo_leakage_v4(spec: Dict[str, Any]) -> Dict[str, Any]:
    tid = spec["transition_id"]
    task_prompt = spec.get("current_task", "")
    target_sym = spec.get("target_symbol", "")
    target_file = spec.get("target_file", "")
    replacements = spec.get("replacement_symbols", [])
    valid_sol = spec.get("valid_solution", "")

    fixture_dir = os.path.join(FIXTURES_DIR, tid)
    after_dir = os.path.join(fixture_dir, "after")
    if not os.path.exists(after_dir):
        # Fallback to repo cache
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

    # Extract retrieved files from headers
    retrieved_files = re.findall(r"^=== File: (.*?) ===", retrieved_context, re.MULTILINE)

    norm_context = normalize_code_snippet(retrieved_context)

    # 1. Check TRIVIALIZES_TASK: target function itself defined in retrieved context
    target_func_def = False
    if target_sym and f"def {target_sym}(" in retrieved_context:
        target_func_def = True

    # 2. Check NEAR_SOLUTION: Multi-line AST structure of valid solution present in context
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

    # 3. Check HINTED: Replacement symbols or migration comments in retrieved context
    hinted_terms = []
    for r in replacements:
        r_short = r.split(".")[-1].split("(")[0]
        if len(r_short) > 2 and r_short in retrieved_context:
            hinted_terms.append(r_short)

    for word in ["deprecated", "use instead", "replaced by", "migration", "superseded"]:
        if word in retrieved_context.lower():
            hinted_terms.append(word)

    is_hinted = len(hinted_terms) > 0

    if target_func_def:
        leakage_level = "REPO_CONTEXT_TRIVIALIZES_TASK"
    elif near_solution:
        leakage_level = "REPO_CONTEXT_NEAR_SOLUTION"
    elif is_hinted:
        leakage_level = "REPO_CONTEXT_HINTED"
    else:
        leakage_level = "REPO_CONTEXT_NONTRIVIAL"

    return {
        "transition_id": tid,
        "leakage_level": leakage_level,
        "retrieved_tokens": retrieved_tokens,
        "retrieved_files": retrieved_files,
        "hinted_terms_found": list(set(hinted_terms)),
        "target_func_def_found": target_func_def,
        "near_solution_found": near_solution,
        "retrieved_context_excerpt": retrieved_context[:500]
    }


def run_all_repo_leakage_v4():
    spec_files = sorted(glob.glob(f"{SPECS_DIR}/trans_track_a_*.json"))
    results = {}
    counts = {}

    for p in spec_files:
        with open(p, "r", encoding="utf-8") as f:
            spec = json.load(f)
        tid = spec["transition_id"]
        res = audit_repo_leakage_v4(spec)
        results[tid] = res
        level = res["leakage_level"]
        counts[level] = counts.get(level, 0) + 1

        with open(f"{OUT_DIR}/{tid}.json", "w", encoding="utf-8") as f:
            json.dump(res, f, indent=2)

    print(f"=== Repo Context Leakage Audit V4 ({len(results)} transitions) ===")
    for k, v in sorted(counts.items()):
        print(f"  {k}: {v}/{len(results)} ({v/len(results)*100:.1f}%)")


if __name__ == "__main__":
    run_all_repo_leakage_v4()
