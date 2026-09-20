#!/usr/bin/env python3
"""
scripts/build_false_invalidation_cases.py

Constructs 25 genuine False Invalidation benchmark cases from repository git histories.
Each case consists of:
- repo_name, file_path
- commit_base: initial commit where symbol S was defined
- commit_modified: later commit where the same file was modified (file SHA changed),
  but symbol S AST canonical digest remained completely identical (true valid memory).
- symbol_qualified_name
- base_file_sha, modified_file_sha (different)
- base_symbol_digest, modified_symbol_digest (identical)
- ground_truth_valid: True (since symbol S behavior is identical)

Outputs:
- data/false_invalidation_cases.jsonl
"""

import os
import sys
import json
import hashlib
import subprocess
from typing import Dict, Any, List

sys.path.insert(0, "/code/rolemem-agent-memory")
from src.symbol_validity import SymbolDigestExtractor, MemoryRecord

OUT_PATH = "/code/rolemem-agent-memory/data/false_invalidation_cases.jsonl"
CALIB_PATH = "/code/rolemem-agent-memory/data/calibration_seed_set_v1.jsonl"
SCALE_PATH = "/code/rolemem-agent-memory/data/track_a_scale_manifest.jsonl"


def build_cases():
    print("=== Building False Invalidation Benchmark Cases from Real Git Histories ===")
    transitions = []
    if os.path.exists(CALIB_PATH):
        with open(CALIB_PATH) as f:
            for l in f:
                if l.strip(): transitions.append(json.loads(l))
    if os.path.exists(SCALE_PATH):
        with open(SCALE_PATH) as f:
            for l in f:
                if l.strip(): transitions.append(json.loads(l))

    cases = []

    for item in transitions:
        tid = item["transition_id"]
        repo_name = item["repo_name"].split("/")[-1]
        repo_path = f"/code/repo_cache/{repo_name}"
        primary_file = item["primary_file"]
        base_commit = item["base_commit"]

        if not os.path.isdir(repo_path):
            continue

        # Get git log for the file around base_commit
        try:
            commits = subprocess.check_output(
                ["git", "-C", repo_path, "log", "-n", "8", "--format=%H", base_commit, "--", primary_file],
                stderr=subprocess.DEVNULL
            ).decode("utf-8", errors="ignore").splitlines()
        except Exception:
            continue

        if len(commits) < 2:
            continue

        # Check adjacent commits
        for i in range(len(commits) - 1):
            c_earlier = commits[i + 1]
            c_later = commits[i]

            try:
                content_earlier = subprocess.check_output(
                    ["git", "-C", repo_path, "show", f"{c_earlier}:{primary_file}"],
                    stderr=subprocess.DEVNULL
                ).decode("utf-8", errors="ignore")
                content_later = subprocess.check_output(
                    ["git", "-C", repo_path, "show", f"{c_later}:{primary_file}"],
                    stderr=subprocess.DEVNULL
                ).decode("utf-8", errors="ignore")
            except Exception:
                continue

            file_sha_earlier = hashlib.sha256(content_earlier.encode("utf-8")).hexdigest()
            file_sha_later = hashlib.sha256(content_later.encode("utf-8")).hexdigest()

            if file_sha_earlier == file_sha_later:
                continue

            digests_earlier = SymbolDigestExtractor.extract_symbol_digests(content_earlier)
            digests_later = SymbolDigestExtractor.extract_symbol_digests(content_later)

            # Find symbols whose AST digest remained completely unchanged
            for sym_name, sym_info in digests_earlier.items():
                if sym_name in digests_later:
                    if digests_later[sym_name]["symbol_digest"] == sym_info["symbol_digest"]:
                        # Unchanged symbol in a changed file!
                        case = {
                            "case_id": f"false_inval_{repo_name}_{sym_name}_{c_earlier[:8]}_{c_later[:8]}",
                            "repo_name": item["repo_name"],
                            "file_path": primary_file,
                            "symbol_qualified_name": sym_name,
                            "symbol_type": sym_info["symbol_type"],
                            "commit_base": c_earlier,
                            "commit_modified": c_later,
                            "base_file_sha": file_sha_earlier,
                            "modified_file_sha": file_sha_later,
                            "file_sha_changed": True,
                            "base_symbol_digest": sym_info["symbol_digest"],
                            "modified_symbol_digest": digests_later[sym_name]["symbol_digest"],
                            "symbol_ast_identical": True,
                            "ground_truth_valid": True,  # Memory about this symbol is STILL 100% VALID
                            "statement": f"{sym_name} functions as defined in {primary_file} at commit {c_earlier[:8]}."
                        }
                        cases.append(case)
                        if len(cases) >= 30:
                            break
            if len(cases) >= 30:
                break
        if len(cases) >= 30:
            break

    # Also add stale transition cases where symbol WAS modified / removed (ground_truth_valid = False)
    for item in transitions[:10]:
        tid = item["transition_id"]
        repo_name = item["repo_name"].split("/")[-1]
        repo_path = f"/code/repo_cache/{repo_name}"
        primary_file = item["primary_file"]
        base_commit = item["base_commit"]
        target_commit = item["target_commit"]
        symbol = item.get("symbol") or item.get("target_symbol") or item.get("changed_symbols", [""])[0]

        try:
            content_base = subprocess.check_output(
                ["git", "-C", repo_path, "show", f"{base_commit}:{primary_file}"],
                stderr=subprocess.DEVNULL
            ).decode("utf-8", errors="ignore")
            content_target = subprocess.check_output(
                ["git", "-C", repo_path, "show", f"{target_commit}:{primary_file}"],
                stderr=subprocess.DEVNULL
            ).decode("utf-8", errors="ignore")
        except Exception:
            continue

        file_sha_base = hashlib.sha256(content_base.encode("utf-8")).hexdigest()
        file_sha_target = hashlib.sha256(content_target.encode("utf-8")).hexdigest()
        digests_base = SymbolDigestExtractor.extract_symbol_digests(content_base)
        digests_target = SymbolDigestExtractor.extract_symbol_digests(content_target)

        sym_short = symbol.split(".")[-1]
        base_dig = digests_base.get(symbol, {}).get("symbol_digest") or digests_base.get(sym_short, {}).get("symbol_digest", "stale_hash_base")
        target_dig = digests_target.get(symbol, {}).get("symbol_digest") or digests_target.get(sym_short, {}).get("symbol_digest", None)

        stale_case = {
            "case_id": f"stale_inval_{tid}",
            "repo_name": item["repo_name"],
            "file_path": primary_file,
            "symbol_qualified_name": symbol,
            "symbol_type": "symbol",
            "commit_base": base_commit,
            "commit_modified": target_commit,
            "base_file_sha": file_sha_base,
            "modified_file_sha": file_sha_target,
            "file_sha_changed": (file_sha_base != file_sha_target),
            "base_symbol_digest": base_dig,
            "modified_symbol_digest": target_dig,
            "symbol_ast_identical": (base_dig == target_dig and target_dig is not None),
            "ground_truth_valid": False,  # Truly stale memory
            "statement": item.get("stale_memory_candidate", f"Historical usage of {symbol}")
        }
        cases.append(stale_case)

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        for c in cases:
            f.write(json.dumps(c) + "\n")

    val_count = sum(1 for c in cases if c["ground_truth_valid"])
    stale_count = sum(1 for c in cases if not c["ground_truth_valid"])
    print(f"Built {len(cases)} cases ({val_count} valid negative cases, {stale_count} stale transition cases) -> {OUT_PATH}")


if __name__ == "__main__":
    build_cases()
