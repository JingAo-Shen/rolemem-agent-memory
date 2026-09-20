#!/usr/bin/env python3
"""
scripts/build_tree_manifest.py
Tree-Level Snapshot Purity Verifier and Manifest Generator for RoleMem.

Verifies:
- Every file in fixtures_v2/<tid>/before/ and fixtures_v2/<tid>/after/ matches
  the pristine Git archive extracted directly from the repository mirror at
  base_commit and target_commit respectively.
- Zero untracked or mutated files.
- Generates data/tree_manifests/<tid>.json and fixtures_v2/<tid>/fixture_tree_manifest.json
  with relative_path, size, and sha256 for all package files.
- Emits TREE_PURITY_PASS only if 100% of files match bit-for-bit.
"""

import os
import sys
import json
import glob
import hashlib
import tempfile
import subprocess
from typing import Dict, Any, List, Tuple

REPO_MIRRORS = {
    "pallets/click": "/code/repo_cache/click",
    "pallets/flask": "/code/repo_cache/flask",
    "pallets/werkzeug": "/code/repo_cache/werkzeug",
    "pallets/jinja": "/code/repo_cache/jinja",
    "pallets/itsdangerous": "/code/repo_cache/itsdangerous",
    "pallets/markupsafe": "/code/repo_cache/markupsafe",
    "pytest-dev/pluggy": "/code/repo_cache/pluggy",
    "python-attrs/attrs": "/code/repo_cache/attrs",
    "pypa/virtualenv": "/code/repo_cache/virtualenv",
    "encode/httpx": "/code/repo_cache/httpx",
    "psf/requests": "/code/repo_cache/requests",
    "urllib3/urllib3": "/code/repo_cache/urllib3",
    "encode/starlette": "/code/repo_cache/starlette",
    "tiangolo/fastapi": "/code/repo_cache/fastapi",
    "pydantic/pydantic": "/code/repo_cache/pydantic",
    "pytest-dev/pytest": "/code/repo_cache/pytest",
    "celery/celery": "/code/repo_cache/celery",
    "marshmallow-code/marshmallow": "/code/repo_cache/marshmallow",
    "PyCQA/flake8": "/code/repo_cache/flake8",
    "pyca/cryptography": "/code/repo_cache/cryptography",
    "Textualize/rich": "/code/repo_cache/rich",
    "pytest-dev/iniconfig": "/code/repo_cache/iniconfig",
    "sqlalchemy/sqlalchemy": "/code/repo_cache/sqlalchemy",
    "more-itertools/more-itertools": "/code/repo_cache/more-itertools",
    "pypa/packaging": "/code/repo_cache/packaging",
    "dateutil/dateutil": "/code/repo_cache/dateutil",
    "tqdm/tqdm": "/code/repo_cache/tqdm",
    "encode/uvicorn": "/code/repo_cache/uvicorn",
    "pallets/cachelib": "/code/repo_cache/cachelib",
    "pallets-eco/cachelib": "/code/repo_cache/cachelib"
}

OUT_DIR = "/code/rolemem-agent-memory/data/tree_manifests"
FIXTURES_ROOT = "/code/rolemem-agent-memory/fixtures_v2"
os.makedirs(OUT_DIR, exist_ok=True)


def hash_file(filepath: str) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def scan_directory(directory: str) -> Dict[str, Dict[str, Any]]:
    """Scan directory recursively returning relative_path -> {size, sha256}."""
    result = {}
    if not os.path.isdir(directory):
        return result
    for root, _, files in os.walk(directory):
        for fn in files:
            full_p = os.path.join(root, fn)
            rel_p = os.path.relpath(full_p, directory)
            sz = os.path.getsize(full_p)
            sha = hash_file(full_p)
            result[rel_p] = {"size": sz, "sha256": sha}
    return result


def extract_git_tree(repo_dir: str, commit: str, pkg_path: str) -> Dict[str, Dict[str, Any]]:
    """Extract git archive for pkg_path at commit to a tempdir and scan."""
    git_env = {**os.environ, "GIT_NO_LAZY_FETCH": "1", "GIT_TERMINAL_PROMPT": "0"}
    with tempfile.TemporaryDirectory(prefix="git_tree_") as tmpdir:
        # Run git archive | tar -x
        cmd = f"git -C {repo_dir} archive {commit} {pkg_path} | tar -x -C {tmpdir}"
        res = subprocess.run(cmd, shell=True, env=git_env, capture_output=True)
        if res.returncode != 0:
            raise RuntimeError(f"Failed git archive for {commit}:{pkg_path} in {repo_dir}: {res.stderr.decode()}")
        return scan_directory(tmpdir)


def verify_transition_tree(spec_path: str) -> Dict[str, Any]:
    with open(spec_path, "r", encoding="utf-8") as f:
        spec = json.load(f)

    tid = spec["transition_id"]
    repo_name = spec["repo_name"]
    base_commit = spec["base_commit"]
    target_commit = spec["target_commit"]
    pkg_path = spec.get("pkg_path", "")

    repo_dir = REPO_MIRRORS.get(repo_name)
    if not repo_dir or not os.path.isdir(repo_dir):
        return {"transition_id": tid, "status": "FAIL", "error": f"Missing mirror {repo_name}"}

    fix_dir = os.path.join(FIXTURES_ROOT, tid)
    fix_before = os.path.join(fix_dir, "before")
    fix_after = os.path.join(fix_dir, "after")

    # 1. Scan fixture directories
    disk_before = scan_directory(fix_before)
    disk_after = scan_directory(fix_after)

    # 2. Extract git archives
    git_before = extract_git_tree(repo_dir, base_commit, pkg_path)
    git_after = extract_git_tree(repo_dir, target_commit, pkg_path)

    # 3. Compare before tree
    before_mismatches = []
    for rel_p, meta in git_before.items():
        if rel_p not in disk_before:
            before_mismatches.append(f"MISSING: {rel_p}")
        elif disk_before[rel_p]["sha256"] != meta["sha256"]:
            before_mismatches.append(f"SHA_MISMATCH: {rel_p}")

    for rel_p in disk_before:
        if rel_p not in git_before:
            before_mismatches.append(f"EXTRA: {rel_p}")

    # 4. Compare after tree
    after_mismatches = []
    for rel_p, meta in git_after.items():
        if rel_p not in disk_after:
            after_mismatches.append(f"MISSING: {rel_p}")
        elif disk_after[rel_p]["sha256"] != meta["sha256"]:
            after_mismatches.append(f"SHA_MISMATCH: {rel_p}")

    for rel_p in disk_after:
        if rel_p not in git_after:
            after_mismatches.append(f"EXTRA: {rel_p}")

    before_pass = len(before_mismatches) == 0
    after_pass = len(after_mismatches) == 0
    tree_purity = "TREE_PURITY_PASS" if (before_pass and after_pass) else "TREE_PURITY_FAIL"

    # Sorted file lists for deterministic manifest
    before_files = [{"relative_path": p, "size": disk_before[p]["size"], "sha256": disk_before[p]["sha256"]} for p in sorted(disk_before.keys())]
    after_files = [{"relative_path": p, "size": disk_after[p]["size"], "sha256": disk_after[p]["sha256"]} for p in sorted(disk_after.keys())]

    manifest = {
        "transition_id": tid,
        "repo_name": repo_name,
        "base_commit": base_commit,
        "target_commit": target_commit,
        "pkg_path": pkg_path,
        "tree_purity_status": tree_purity,
        "before_tree_purity": "TREE_PURITY_PASS" if before_pass else "TREE_PURITY_FAIL",
        "after_tree_purity": "TREE_PURITY_PASS" if after_pass else "TREE_PURITY_FAIL",
        "before_mismatches": before_mismatches,
        "after_mismatches": after_mismatches,
        "total_files_before": len(before_files),
        "total_files_after": len(after_files),
        "has_environment_overlay": os.path.exists(os.path.join(fix_dir, "environment_overlay", "overlay_manifest.json")),
        "before_files": before_files,
        "after_files": after_files,
    }

    # Compute deterministic SHA256 of manifest content
    manifest_bytes = json.dumps(manifest, sort_keys=True).encode("utf-8")
    manifest["fixture_manifest_hash"] = hashlib.sha256(manifest_bytes).hexdigest()

    # Save to data/tree_manifests/<tid>.json
    with open(os.path.join(OUT_DIR, f"{tid}.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    # Also save to fixture dir
    with open(os.path.join(fix_dir, "fixture_tree_manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    return manifest


def main():
    specs = sorted(glob.glob("/code/rolemem-agent-memory/data/specs/trans_track_a_*.json"))
    print(f"=== Running Tree-Level Snapshot Purity Verification ({len(specs)} transitions) ===")
    passed = 0
    for s in specs:
        res = verify_transition_tree(s)
        status = res["tree_purity_status"]
        tid = res["transition_id"]
        overlay_str = " (has overlay)" if res.get("has_environment_overlay") else ""
        print(f"[{tid:45}] {status:16} | before: {res['total_files_before']:3d} files | after: {res['total_files_after']:3d} files{overlay_str}")
        if status == "TREE_PURITY_PASS":
            passed += 1
        else:
            print(f"   Before mismatches: {res['before_mismatches'][:3]}")
            print(f"   After mismatches:  {res['after_mismatches'][:3]}")

    print(f"\nTree-Level Snapshot Purity: {passed}/{len(specs)} PASS\n")


if __name__ == "__main__":
    main()
