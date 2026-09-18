"""
src/fingerprint.py
Unified cryptographic fingerprint module for RoleMem benchmark transitions.
Binds:
- canonical spec
- fixture metadata
- before/after git tree hashes
- hidden test
- stale control
- valid control
- auditor version
- target commit tree hash
"""

import os
import json
import hashlib
import subprocess
from typing import Dict, Any, Optional, Union

REPO_CACHE_ROOT = "/code/repo_cache"
DEFAULT_AUDITOR_VERSION = "v7.0"

REPO_DIR_MAP = {
    "pallets/werkzeug": os.path.join(REPO_CACHE_ROOT, "werkzeug"),
    "pallets/flask": os.path.join(REPO_CACHE_ROOT, "flask"),
    "pallets/click": os.path.join(REPO_CACHE_ROOT, "click"),
    "urllib3/urllib3": os.path.join(REPO_CACHE_ROOT, "urllib3"),
    "psf/requests": os.path.join(REPO_CACHE_ROOT, "requests"),
}


def get_git_tree_hash(repo_dir: str, commit_ref: str) -> str:
    """Get git tree hash for a commit reference."""
    if not repo_dir or not os.path.exists(repo_dir) or not commit_ref:
        return ""
    try:
        res = subprocess.run(
            ["git", "-C", repo_dir, "rev-parse", f"{commit_ref}^{{tree}}"],
            capture_output=True,
            text=True,
            check=False
        )
        if res.returncode == 0:
            return res.stdout.strip()
    except Exception:
        pass
    return ""


def compute_unified_audit_fingerprint(
    spec: Union[str, Dict[str, Any]],
    fixture_dir: Optional[str] = None,
    auditor_version: str = DEFAULT_AUDITOR_VERSION,
    repo_cache_root: str = REPO_CACHE_ROOT
) -> str:
    """
    Computes a deterministic SHA256 audit fingerprint binding:
      1. Canonical spec (JSON with sorted keys)
      2. Fixture metadata (metadata.json)
      3. Base commit git tree hash
      4. Target commit git tree hash
      5. Hidden test (test_evaluation.py)
      6. Stale control (stale_solution.py)
      7. Valid control (valid_solution.py)
      8. Auditor version string
      9. Target commit tree hash
    """
    h = hashlib.sha256()

    # 1. Canonical spec
    if isinstance(spec, str):
        if os.path.exists(spec):
            with open(spec, "r", encoding="utf-8") as f:
                spec_dict = json.load(f)
        else:
            raise FileNotFoundError(f"Spec file not found: {spec}")
    else:
        spec_dict = spec

    spec_canonical_bytes = json.dumps(spec_dict, sort_keys=True).encode("utf-8")
    h.update(spec_canonical_bytes)

    tid = spec_dict.get("transition_id", "")
    repo_name = spec_dict.get("repo_name", "")
    base_commit = spec_dict.get("base_commit", "")
    target_commit = spec_dict.get("target_commit", "")

    if not fixture_dir:
        fixture_dir = f"/code/rolemem-agent-memory/fixtures_v2/{tid}"

    # 2. Fixture metadata
    meta_path = os.path.join(fixture_dir, "metadata.json")
    if os.path.exists(meta_path):
        with open(meta_path, "rb") as f:
            h.update(f.read())

    # 3 & 4. Base & Target tree hashes
    repo_dir = REPO_DIR_MAP.get(repo_name) or os.path.join(repo_cache_root, repo_name.split("/")[-1])
    base_tree = get_git_tree_hash(repo_dir, base_commit)
    target_tree = get_git_tree_hash(repo_dir, target_commit)
    h.update(base_tree.encode("utf-8"))
    h.update(target_tree.encode("utf-8"))

    # 5. Hidden test
    hidden_test_path = os.path.join(fixture_dir, "hidden_tests", "test_evaluation.py")
    if os.path.exists(hidden_test_path):
        with open(hidden_test_path, "rb") as f:
            h.update(f.read())

    # 6. Stale control
    stale_ctrl_path = os.path.join(fixture_dir, "controls", "stale_solution.py")
    if os.path.exists(stale_ctrl_path):
        with open(stale_ctrl_path, "rb") as f:
            h.update(f.read())

    # 7. Valid control
    valid_ctrl_path = os.path.join(fixture_dir, "controls", "valid_solution.py")
    if os.path.exists(valid_ctrl_path):
        with open(valid_ctrl_path, "rb") as f:
            h.update(f.read())

    # 8. Auditor version
    h.update(auditor_version.encode("utf-8"))

    # 9. Target commit tree hash
    h.update(target_tree.encode("utf-8"))

    return h.hexdigest()
