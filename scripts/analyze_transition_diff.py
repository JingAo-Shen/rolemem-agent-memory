#!/usr/bin/env python3
"""
scripts/analyze_transition_diff.py
Performs AST + Git Diff symbol analysis across candidates in data/candidates/track_a_raw.jsonl.
Classifies each candidate as HIGH_CONFIDENCE, NOISE, REJECT_DOCS_ONLY, REJECT_TEST_ONLY,
REJECT_FORMAT_OR_COMMENTS_ONLY, REJECT_NON_API, REJECT_NOT_ANCESTOR, or REJECT_SYNTHETIC_COMMIT.
Extracts real symbol transitions: removed_symbols, added_symbols, signature_changes, deprecated_symbols.
Saves analyzed results to data/candidates/track_a_analyzed.jsonl.
"""

import os
import sys
import json
import ast
import subprocess
from typing import Dict, Any, List, Set, Tuple, Optional

REPO_MAP = {
    "pallets/click": "/code/repo_cache/click",
    "pallets/flask": "/code/repo_cache/flask",
    "pallets/werkzeug": "/code/repo_cache/werkzeug",
    "pallets/jinja": "/code/repo_cache/jinja",
    "pallets/itsdangerous": "/code/repo_cache/itsdangerous",
    "pallets/markupsafe": "/code/repo_cache/markupsafe",
    "psf/requests": "/code/repo_cache/requests",
    "urllib3/urllib3": "/code/repo_cache/urllib3",
    "encode/httpx": "/code/repo_cache/httpx",
    "encode/starlette": "/code/repo_cache/starlette",
    "Textualize/rich": "/code/repo_cache/rich",
    "marshmallow-code/marshmallow": "/code/repo_cache/marshmallow",
    "pytest-dev/pluggy": "/code/repo_cache/pluggy",
    "pytest-dev/iniconfig": "/code/repo_cache/iniconfig",
    "PyCQA/flake8": "/code/repo_cache/flake8",
    "python-attrs/attrs": "/code/repo_cache/attrs",
    "pypa/virtualenv": "/code/repo_cache/virtualenv",
    "pydantic/pydantic": "/code/repo_cache/pydantic",
}

GIT_ENV = {**os.environ, "GIT_NO_LAZY_FETCH": "1", "GIT_TERMINAL_PROMPT": "0"}


class SymbolExtractor(ast.NodeVisitor):
    def __init__(self):
        self.symbols: Dict[str, Dict[str, Any]] = {}
        self.scope_stack: List[str] = []
        self.deprecated_symbols: Set[str] = set()

    def _current_prefix(self) -> str:
        return ".".join(self.scope_stack) + ("." if self.scope_stack else "")

    def visit_ClassDef(self, node: ast.ClassDef):
        name = self._current_prefix() + node.name
        self.symbols[name] = {
            "type": "class",
            "name": name,
            "lineno": node.lineno,
            "bases": [ast.unparse(b) for b in node.bases] if hasattr(ast, "unparse") else []
        }
        self.scope_stack.append(node.name)
        self.generic_visit(node)
        self.scope_stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef):
        name = self._current_prefix() + node.name
        params = [a.arg for a in node.args.args]
        kwonly = [a.arg for a in node.args.kwonlyargs]
        defaults_len = len(node.args.defaults)
        kw_defaults = len([d for d in node.args.kw_defaults if d is not None])

        # Check for deprecation warnings inside body
        is_deprecated = False
        for stmt in ast.walk(node):
            if isinstance(stmt, ast.Call):
                func_name = ""
                if isinstance(stmt.func, ast.Name):
                    func_name = stmt.func.id
                elif isinstance(stmt.func, ast.Attribute):
                    func_name = stmt.func.attr
                if "warn" in func_name.lower() or "deprecated" in func_name.lower():
                    is_deprecated = True
                    break

        if is_deprecated:
            self.deprecated_symbols.add(name)

        self.symbols[name] = {
            "type": "function",
            "name": name,
            "lineno": node.lineno,
            "params": params,
            "kwonly": kwonly,
            "pos_defaults": defaults_len,
            "kw_defaults": kw_defaults,
            "is_deprecated": is_deprecated
        }
        self.scope_stack.append(node.name)
        self.generic_visit(node)
        self.scope_stack.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        name = self._current_prefix() + node.name
        params = [a.arg for a in node.args.args]
        kwonly = [a.arg for a in node.args.kwonlyargs]
        self.symbols[name] = {
            "type": "async_function",
            "name": name,
            "lineno": node.lineno,
            "params": params,
            "kwonly": kwonly,
            "pos_defaults": len(node.args.defaults),
            "kw_defaults": len([d for d in node.args.kw_defaults if d is not None]),
            "is_deprecated": False
        }
        self.scope_stack.append(node.name)
        self.generic_visit(node)
        self.scope_stack.pop()


def extract_symbols_from_code(code_str: str) -> Tuple[Dict[str, Dict[str, Any]], Set[str]]:
    try:
        tree = ast.parse(code_str)
        extractor = SymbolExtractor()
        extractor.visit(tree)
        return extractor.symbols, extractor.deprecated_symbols
    except Exception:
        return {}, set()


def compare_symbols(
    base_syms: Dict[str, Dict[str, Any]],
    target_syms: Dict[str, Dict[str, Any]],
    target_depr: Set[str]
) -> Dict[str, Any]:
    removed = []
    added = []
    sig_changes = []
    deprecated = list(target_depr)

    for sname, sinfo in base_syms.items():
        if sname not in target_syms:
            removed.append(sname)
        else:
            tinfo = target_syms[sname]
            if sinfo["type"] in ("function", "async_function") and tinfo["type"] in ("function", "async_function"):
                if sinfo["params"] != tinfo["params"] or sinfo["kwonly"] != tinfo["kwonly"]:
                    sig_changes.append({
                        "symbol": sname,
                        "base_params": sinfo["params"],
                        "target_params": tinfo["params"],
                        "base_kwonly": sinfo["kwonly"],
                        "target_kwonly": tinfo["kwonly"]
                    })

    for sname in target_syms:
        if sname not in base_syms:
            added.append(sname)

    return {
        "removed_symbols": removed,
        "added_symbols": added,
        "signature_changes": sig_changes,
        "deprecated_symbols": deprecated
    }


def analyze_candidate(cand: Dict[str, Any]) -> Dict[str, Any]:
    cid = cand.get("candidate_id") or cand.get("transition_id", "unknown")
    repo_name = cand.get("repo_name", "")
    base_commit = cand.get("base_commit", "")
    target_commit = cand.get("target_commit", "")

    res = {
        "candidate_id": cid,
        "repo_name": repo_name,
        "base_commit": base_commit,
        "target_commit": target_commit,
        "classification": "UNKNOWN",
        "rationale": "",
        "analysis": {}
    }

    repo_dir = REPO_MAP.get(repo_name)
    if not repo_dir or not os.path.exists(repo_dir):
        res["classification"] = "REJECT_REPO_NOT_FOUND"
        res["rationale"] = f"Repository cache not found for {repo_name}"
        return res

    # 1. Check commit existence
    r_base = subprocess.run(["git", "-C", repo_dir, "cat-file", "-e", base_commit], env=GIT_ENV, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    r_target = subprocess.run(["git", "-C", repo_dir, "cat-file", "-e", target_commit], env=GIT_ENV, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if r_base.returncode != 0 or r_target.returncode != 0:
        res["classification"] = "REJECT_SYNTHETIC_COMMIT"
        res["rationale"] = f"Commit objects do not exist in local git repository (base={r_base.returncode}, target={r_target.returncode})"
        return res

    # 2. Check commit ancestry
    r_anc = subprocess.run(["git", "-C", repo_dir, "merge-base", "--is-ancestor", base_commit, target_commit], env=GIT_ENV)
    if r_anc.returncode != 0:
        res["classification"] = "REJECT_NOT_ANCESTOR"
        res["rationale"] = "Base commit is not an ancestor of target commit"
        return res

    # 3. Check diff files
    try:
        diff_out = subprocess.check_output(
            ["git", "-C", repo_dir, "diff", "--name-status", f"{base_commit}..{target_commit}"],
            env=GIT_ENV, stderr=subprocess.DEVNULL
        ).decode("utf-8", errors="ignore").splitlines()
    except Exception as e:
        res["classification"] = "REJECT_DIFF_FAILED"
        res["rationale"] = str(e)
        return res

    if not diff_out:
        res["classification"] = "REJECT_MERGE_OR_EMPTY"
        res["rationale"] = "Git diff between base and target commit is empty"
        return res

    changed_files = []
    for line in diff_out:
        parts = line.strip().split()
        if len(parts) >= 2:
            changed_files.append((parts[0], parts[-1]))

    all_paths = [cf[1] for cf in changed_files]
    py_paths = [p for p in all_paths if p.endswith(".py")]

    # Check docs-only
    non_doc_paths = [p for p in all_paths if not any(p.startswith(d) for d in ["docs/", "doc/"]) and not p.endswith((".md", ".rst", ".txt"))]
    if not non_doc_paths:
        res["classification"] = "REJECT_DOCS_ONLY"
        res["rationale"] = "Diff only touches documentation files"
        return res

    # Check test-only
    non_test_paths = [p for p in py_paths if not any(p.startswith(t) for t in ["test/", "tests/", "testing/"])]
    if not non_test_paths and py_paths:
        res["classification"] = "REJECT_TEST_ONLY"
        res["rationale"] = "Diff only touches test files"
        return res

    if not py_paths:
        res["classification"] = "REJECT_NON_PYTHON"
        res["rationale"] = "No python files changed"
        return res

    # 4. AST Diff on core library files
    total_removed = []
    total_added = []
    total_sig_changes = []
    total_depr = []

    for path in non_test_paths:
        try:
            base_code = subprocess.check_output(
                ["git", "-C", repo_dir, "show", f"{base_commit}:{path}"],
                env=GIT_ENV, stderr=subprocess.DEVNULL
            ).decode("utf-8", errors="ignore")
        except Exception:
            base_code = ""

        try:
            target_code = subprocess.check_output(
                ["git", "-C", repo_dir, "show", f"{target_commit}:{path}"],
                env=GIT_ENV, stderr=subprocess.DEVNULL
            ).decode("utf-8", errors="ignore")
        except Exception:
            target_code = ""

        base_syms, _ = extract_symbols_from_code(base_code)
        target_syms, target_depr = extract_symbols_from_code(target_code)

        diff_res = compare_symbols(base_syms, target_syms, target_depr)
        total_removed.extend([f"{path}:{s}" for s in diff_res["removed_symbols"]])
        total_added.extend([f"{path}:{s}" for s in diff_res["added_symbols"]])
        total_sig_changes.extend([{"file": path, **sc} for sc in diff_res["signature_changes"]])
        total_depr.extend([f"{path}:{s}" for s in diff_res["deprecated_symbols"]])

    res["analysis"] = {
        "changed_files": all_paths,
        "library_py_files": non_test_paths,
        "removed_symbols": total_removed,
        "added_symbols": total_added,
        "signature_changes": total_sig_changes,
        "deprecated_symbols": total_depr
    }

    # Filter comments/format only
    if not total_removed and not total_added and not total_sig_changes and not total_depr:
        res["classification"] = "REJECT_FORMAT_OR_COMMENTS_ONLY"
        res["rationale"] = "No class, function, or signature changes detected in AST analysis"
        return res

    # Check if changes represent actionable API transitions
    public_removals = [s for s in total_removed if not any(part.startswith("_") and not part.startswith("__") for part in s.split(":")[1].split("."))]
    public_sigs = [s for s in total_sig_changes if not any(part.startswith("_") and not part.startswith("__") for part in s["symbol"].split("."))]
    public_depr = [s for s in total_depr if not any(part.startswith("_") and not part.startswith("__") for part in s.split(":")[1].split("."))]

    if public_removals or public_sigs or public_depr or len(total_removed) > 0 or len(total_sig_changes) > 0:
        res["classification"] = "HIGH_CONFIDENCE"
        res["rationale"] = f"Actionable API transition found: {len(public_removals)} public removals, {len(public_sigs)} sig changes, {len(public_depr)} deprecations"
    else:
        res["classification"] = "NOISE"
        res["rationale"] = "Changes confined to private helpers or internal implementation without clear API shift"

    return res


def main():
    raw_path = "/code/rolemem-agent-memory/data/candidates/track_a_raw.jsonl"
    out_path = "/code/rolemem-agent-memory/data/candidates/track_a_analyzed.jsonl"

    print("=== Running AST + Git Diff Symbol Analysis across Track A Candidates ===")
    candidates = []
    if os.path.exists(raw_path):
        with open(raw_path, "r") as f:
            for line in f:
                if line.strip():
                    candidates.append(json.loads(line))

    print(f"Loaded {len(candidates)} raw candidates.")

    results = []
    tally = {}
    for c in candidates:
        a = analyze_candidate(c)
        results.append(a)
        cls = a["classification"]
        tally[cls] = tally.get(cls, 0) + 1

    with open(out_path, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")

    print(f"\nAnalysis completed! Saved to {out_path}")
    print("Classification Tally:")
    for cls, count in sorted(tally.items(), key=lambda x: x[1], reverse=True):
        print(f"  {cls:<32}: {count}")

    print("\nHIGH_CONFIDENCE candidates sample:")
    high_conf = [r for r in results if r["classification"] == "HIGH_CONFIDENCE"]
    for hc in high_conf[:15]:
        syms_desc = []
        if hc["analysis"]["removed_symbols"]:
            syms_desc.append(f"removals={len(hc['analysis']['removed_symbols'])}")
        if hc["analysis"]["signature_changes"]:
            syms_desc.append(f"sigs={len(hc['analysis']['signature_changes'])}")
        if hc["analysis"]["deprecated_symbols"]:
            syms_desc.append(f"depr={len(hc['analysis']['deprecated_symbols'])}")
        print(f"  [{hc['repo_name']}] {hc['candidate_id']} -> {', '.join(syms_desc)} ({hc['rationale']})")


if __name__ == "__main__":
    main()
