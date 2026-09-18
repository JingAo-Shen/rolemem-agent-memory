#!/usr/bin/env python3
"""
scripts/mine_track_a_candidates.py
Mines 60–100 raw Track A candidate transitions across 15–20 real Python repositories.
Extracts commit ancestry, diff hunks, changed symbols, transition types, and task sketches.
Saves raw candidates to data/candidates/track_a_raw.jsonl.
"""

import os
import sys
import json
import re
import subprocess
from typing import Dict, Any, List, Optional

sys.path.insert(0, "/code/rolemem-agent-memory")

CANDIDATES_OUT = "/code/rolemem-agent-memory/data/candidates/track_a_raw.jsonl"
REPO_CACHE = "/code/repo_cache"
os.makedirs(os.path.dirname(CANDIDATES_OUT), exist_ok=True)

# List of target repositories to mine from
REPOS = [
    {"repo_name": "pallets/click", "path": "/code/repo_cache/click", "url": "https://github.com/pallets/click"},
    {"repo_name": "pallets/flask", "path": "/code/repo_cache/flask", "url": "https://github.com/pallets/flask"},
    {"repo_name": "pallets/werkzeug", "path": "/code/repo_cache/werkzeug", "url": "https://github.com/pallets/werkzeug"},
    {"repo_name": "pallets/jinja", "path": "/code/repo_cache/jinja", "url": "https://github.com/pallets/jinja"},
    {"repo_name": "pallets/itsdangerous", "path": "/code/repo_cache/itsdangerous", "url": "https://github.com/pallets/itsdangerous"},
    {"repo_name": "pallets/markupsafe", "path": "/code/repo_cache/markupsafe", "url": "https://github.com/pallets/markupsafe"},
    {"repo_name": "psf/requests", "path": "/code/repo_cache/requests", "url": "https://github.com/psf/requests"},
    {"repo_name": "urllib3/urllib3", "path": "/code/repo_cache/urllib3", "url": "https://github.com/urllib3/urllib3"},
    {"repo_name": "encode/httpx", "path": "/code/repo_cache/httpx", "url": "https://github.com/encode/httpx"},
    {"repo_name": "encode/starlette", "path": "/code/repo_cache/starlette", "url": "https://github.com/encode/starlette"},
    {"repo_name": "Textualize/rich", "path": "/code/repo_cache/rich", "url": "https://github.com/Textualize/rich"},
    {"repo_name": "marshmallow-code/marshmallow", "path": "/code/repo_cache/marshmallow", "url": "https://github.com/marshmallow-code/marshmallow"},
    {"repo_name": "pytest-dev/pluggy", "path": "/code/repo_cache/pluggy", "url": "https://github.com/pytest-dev/pluggy"},
    {"repo_name": "pytest-dev/iniconfig", "path": "/code/repo_cache/iniconfig", "url": "https://github.com/pytest-dev/iniconfig"},
    {"repo_name": "PyCQA/flake8", "path": "/code/repo_cache/flake8", "url": "https://github.com/PyCQA/flake8"},
    {"repo_name": "python-attrs/attrs", "path": "/code/repo_cache/attrs", "url": "https://github.com/python-attrs/attrs"},
    {"repo_name": "pypa/virtualenv", "path": "/code/repo_cache/virtualenv", "url": "https://github.com/pypa/virtualenv"},
    {"repo_name": "pydantic/pydantic", "path": "/code/repo_cache/pydantic", "url": "https://github.com/pydantic/pydantic"}
]


def mine_git_repo_transitions(repo_info: Dict[str, str], max_cands: int = 5) -> List[Dict[str, Any]]:
    """Scan commit history for genuine API deprecations, renames, removals, or behavior shifts."""
    repo_path = repo_info["path"]
    if not os.path.exists(repo_path):
        return []

    mined = []
    # Search git commits with deprecation / removal / rename in message
    try:
        cmd = [
            "git", "-C", repo_path, "log", "-n", "200",
            "--grep=deprecat\\|remov\\|renam\\|replac",
            "--format=%H%x00%P%x00%s%x00%b%x1e"
        ]
        out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode("utf-8", errors="ignore")
    except Exception:
        return []

    commits = out.split("\x1e")
    for item in commits:
        if not item.strip():
            continue
        parts = item.strip().split("\x00")
        if len(parts) < 3:
            continue
        commit_hash = parts[0]
        parents = parts[1].split()
        subject = parts[2]
        body = parts[3] if len(parts) > 3 else ""

        if not parents:
            continue
        base_commit = parents[0]

        # Check diff to see if Python code changed
        try:
            diff_stat = subprocess.check_output(
                ["git", "-C", repo_path, "diff", "--name-only", f"{base_commit}..{commit_hash}"],
                stderr=subprocess.DEVNULL
            ).decode("utf-8", errors="ignore").splitlines()
        except Exception:
            continue

        py_files = [f for f in diff_stat if f.endswith(".py") and not f.startswith("tests/") and not f.startswith("docs/")]
        if not py_files:
            continue

        primary_file = py_files[0]

        # Classify transition type
        subj_lower = subject.lower()
        if "deprecat" in subj_lower:
            ttype = "API_DEPRECATION"
        elif "remov" in subj_lower or "delete" in subj_lower:
            ttype = "API_REMOVAL"
        elif "renam" in subj_lower:
            ttype = "FUNCTION_RENAME"
        elif "signatur" in subj_lower or "arg" in subj_lower or "param" in subj_lower:
            ttype = "SIGNATURE_CHANGE"
        else:
            ttype = "API_EVOLUTION"

        # Extract symbol hint from subject
        sym_match = re.findall(r"`?([A-Za-z_][A-Za-z0-9_]{3,})`?", subject)
        changed_symbols = sym_match[:2] if sym_match else ["api_symbol"]

        cand_id = f"cand_{repo_info['repo_name'].split('/')[-1]}_{commit_hash[:8]}"
        mined.append({
            "candidate_id": cand_id,
            "repo_name": repo_info["repo_name"],
            "repo_url": repo_info["url"],
            "base_commit": base_commit,
            "target_commit": commit_hash,
            "changed_files": py_files[:3],
            "changed_symbols": changed_symbols,
            "transition_type": ttype,
            "commit_subject": subject,
            "commit_body": body[:300],
            "stale_sensitive": (ttype in ["API_DEPRECATION", "API_REMOVAL", "FUNCTION_RENAME", "SIGNATURE_CHANGE"])
        })

        if len(mined) >= max_cands:
            break

    return mined


def run_mining():
    print("=== Running Track A Candidate Mining Engine ===")
    all_candidates = []
    repo_counts = {}

    # 1. Load curated candidates from mine_github_transitions.py if available
    try:
        from scripts.mine_github_transitions import get_all_mined_candidates
        curated = get_all_mined_candidates()
        print(f"Loaded {len(curated)} candidates from curated pool.")
        for c in curated:
            r = c["repo_name"]
            repo_counts[r] = repo_counts.get(r, 0) + 1
            all_candidates.append({
                "candidate_id": c["transition_id"],
                "repo_name": c["repo_name"],
                "repo_url": c["repo_url"],
                "base_commit": c["base_commit"],
                "target_commit": c["target_commit"],
                "changed_files": c.get("changed_files", []),
                "changed_symbols": c.get("changed_symbols", []),
                "transition_type": "API_DEPRECATION" if "deprecat" in str(c.get("repository_change", "")).lower() else "API_EVOLUTION",
                "commit_subject": c.get("repository_change", "")[:100],
                "commit_body": str(c.get("historical_evidence", ""))[:300],
                "stale_sensitive": True,
                "current_task": c.get("current_task", ""),
                "stale_memory_candidate": c.get("stale_memory_candidate", ""),
                "valid_memory_candidate": c.get("valid_memory_candidate", "")
            })
    except Exception as e:
        print(f"Curated candidate loading skipped: {e}")

    # 2. Mine additional candidates from all cloned repositories
    for r_info in REPOS:
        r_name = r_info["repo_name"]
        curr_count = repo_counts.get(r_name, 0)
        target_to_mine = max(0, 4 - curr_count)
        if target_to_mine > 0:
            print(f"Mining up to {target_to_mine} candidates from {r_name} ({r_info['path']})...")
            new_cands = mine_git_repo_transitions(r_info, max_cands=target_to_mine)
            for nc in new_cands:
                all_candidates.append(nc)
                repo_counts[r_name] = repo_counts.get(r_name, 0) + 1

    # Deduplicate candidates by candidate_id
    seen_ids = set()
    deduped = []
    for c in all_candidates:
        cid = c["candidate_id"]
        if cid not in seen_ids:
            seen_ids.add(cid)
            deduped.append(c)

    print(f"\nTotal raw candidates mined: {len(deduped)}")
    print(f"Total unique repositories: {len(repo_counts)}")
    print("Repository breakdown:")
    for r, count in sorted(repo_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {r:<30}: {count} candidates")

    # Write to data/candidates/track_a_raw.jsonl
    with open(CANDIDATES_OUT, "w", encoding="utf-8") as f:
        for c in deduped:
            f.write(json.dumps(c) + "\n")
    print(f"\nSaved raw candidates to {CANDIDATES_OUT}")


if __name__ == "__main__":
    run_mining()
