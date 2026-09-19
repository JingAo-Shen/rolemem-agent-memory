#!/usr/bin/env python3
"""
scripts/audit_external_ground_truth_v3.py
Dual-Source External Ground Truth Auditor V3 for RoleMem.

Authenticates with GitHub REST API, downloads full evidence to data/external_evidence/<tid>/,
cross-verifies with local git mirrors, enforces strict ancestry check,
validates issue linkage (no unconditional PASS), and computes comprehensive audit fingerprint.
"""

import os
import sys
import json
import time
import glob
import re
import hashlib
import subprocess
import urllib.request
import urllib.error

sys.path.insert(0, "/code/rolemem-agent-memory")
from src.fingerprint import compute_unified_audit_fingerprint, DEFAULT_AUDITOR_VERSION

AUDITOR_VERSION = "3.0.0"

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
}

def get_github_token():
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        return token
    git_cred_path = "/root/.git-credentials"
    if os.path.exists(git_cred_path):
        with open(git_cred_path, "r", encoding="utf-8") as f:
            for line in f:
                if "github.com" in line:
                    creds = line.strip().split("@github.com")[0].split("//")[-1]
                    if ":" in creds:
                        return creds.split(":")[1]
    return None

def fetch_github_api(url, headers, is_diff=False, max_retries=3):
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=15) as resp:
                if is_diff:
                    return resp.read().decode("utf-8", errors="replace")
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if attempt < max_retries - 1:
                time.sleep(2 * (attempt + 1))
            else:
                raise
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(2 * (attempt + 1))
            else:
                raise
    return None

def compute_audit_fingerprint(spec_path, fixture_dir, auditor_version, git_dir):
    h = hashlib.sha256()
    with open(spec_path, "rb") as f:
        h.update(f.read())
    
    manifest_p = os.path.join(fixture_dir, "metadata.json")
    if os.path.exists(manifest_p):
        with open(manifest_p, "rb") as f:
            h.update(f.read())
            
    hidden_test_p = os.path.join(fixture_dir, "hidden_tests", "test_evaluation.py")
    if os.path.exists(hidden_test_p):
        with open(hidden_test_p, "rb") as f:
            h.update(f.read())
            
    stale_ctrl_p = os.path.join(fixture_dir, "controls", "stale_solution.py")
    if os.path.exists(stale_ctrl_p):
        with open(stale_ctrl_p, "rb") as f:
            h.update(f.read())
            
    valid_ctrl_p = os.path.join(fixture_dir, "controls", "valid_solution.py")
    if os.path.exists(valid_ctrl_p):
        with open(valid_ctrl_p, "rb") as f:
            h.update(f.read())
            
    h.update(auditor_version.encode("utf-8"))
    
    # Target git tree hash
    res = subprocess.run(["git", "-C", git_dir, "rev-parse", "HEAD^{tree}"], capture_output=True, text=True)
    if res.returncode == 0:
        h.update(res.stdout.strip().encode("utf-8"))
        
    return h.hexdigest()

def audit_transition_v3(spec_path):
    with open(spec_path, "r", encoding="utf-8") as f:
        spec = json.load(f)

    tid = spec["transition_id"]
    repo_name = spec["repo_name"]
    pr_url = spec["pr_url"]
    declared_issue_url = spec.get("issue_url")
    base_commit = spec["base_commit"]
    target_commit = spec["target_commit"]

    git_dir = REPO_MIRRORS.get(repo_name)
    if not git_dir or not os.path.isdir(git_dir):
        return {"transition_id": tid, "status": "FAIL", "error": f"Missing git mirror for {repo_name}"}

    fixture_dir = f"/code/rolemem-agent-memory/fixtures_v2/{tid}"
    fingerprint = compute_unified_audit_fingerprint(spec, fixture_dir=fixture_dir, auditor_version=DEFAULT_AUDITOR_VERSION)

    evidence_dir = f"/code/rolemem-agent-memory/data/external_evidence/{tid}"
    os.makedirs(evidence_dir, exist_ok=True)

    token = get_github_token()
    headers = {
        "User-Agent": "RoleMem-Auditor-V3",
        "Accept": "application/vnd.github.v3+json"
    }
    if token:
        headers["Authorization"] = f"token {token}"

    m = re.match(r"https://github\.com/([^/]+)/([^/]+)/pull/(\d+)", pr_url)
    if not m:
        return {"transition_id": tid, "status": "FAIL", "error": f"Malformed PR URL: {pr_url}"}
    owner, repo, pr_num_str = m.groups()
    pr_num = int(pr_num_str)

    # 1. Fetch GitHub PR Metadata (with local cache check)
    pr_cache = os.path.join(evidence_dir, "pr.json")
    if os.path.exists(pr_cache):
        with open(pr_cache, "r", encoding="utf-8") as f:
            pr_data = json.load(f)
    else:
        pr_api_url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_num}"
        pr_data = fetch_github_api(pr_api_url, headers)
        if not pr_data:
            return {"transition_id": tid, "status": "FAIL", "error": f"PR #{pr_num} not found on GitHub"}
        with open(pr_cache, "w", encoding="utf-8") as f:
            json.dump(pr_data, f, indent=2)

    # 2. Fetch Changed Files
    files_cache = os.path.join(evidence_dir, "changed_files.json")
    if os.path.exists(files_cache):
        with open(files_cache, "r", encoding="utf-8") as f:
            files_data = json.load(f)
    else:
        files_api_url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_num}/files"
        files_data = fetch_github_api(files_api_url, headers)
        with open(files_cache, "w", encoding="utf-8") as f:
            json.dump(files_data or [], f, indent=2)

    # 3. Fetch Commits
    commits_cache = os.path.join(evidence_dir, "commits.json")
    if os.path.exists(commits_cache):
        with open(commits_cache, "r", encoding="utf-8") as f:
            commits_data = json.load(f)
    else:
        commits_api_url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_num}/commits"
        commits_data = fetch_github_api(commits_api_url, headers)
        with open(commits_cache, "w", encoding="utf-8") as f:
            json.dump(commits_data or [], f, indent=2)

    # 4. Fetch Raw Diff Patch
    diff_cache = os.path.join(evidence_dir, "diff.patch")
    if os.path.exists(diff_cache):
        with open(diff_cache, "r", encoding="utf-8") as f:
            raw_diff = f.read()
    else:
        diff_headers = dict(headers)
        diff_headers["Accept"] = "application/vnd.github.v3.diff"
        raw_diff = fetch_github_api(pr_api_url, diff_headers, is_diff=True)
        with open(diff_cache, "w", encoding="utf-8") as f:
            f.write(raw_diff or "")

    # 5. Handle Issue Linkage
    issue_data = None
    issue_status = "NOT_APPLICABLE"
    issue_required = False
    issue_id_verified = None

    if declared_issue_url:
        im = re.match(r"https://github\.com/([^/]+)/([^/]+)/issues/(\d+)", declared_issue_url)
        if im:
            _, _, issue_num_str = im.groups()
            issue_num = int(issue_num_str)
            if issue_num != pr_num:
                # Independent Issue declared!
                issue_required = True
                issue_api_url = f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_num}"
                issue_data = fetch_github_api(issue_api_url, headers)
                if not issue_data:
                    issue_status = "FAIL"
                else:
                    # Check linkage between PR and issue
                    pr_body = pr_data.get("body") or ""
                    commit_msgs = " ".join([c.get("commit", {}).get("message", "") for c in (commits_data or [])])
                    issue_ref_pattern = rf"#{issue_num}\b"
                    if re.search(issue_ref_pattern, pr_body, re.IGNORECASE) or re.search(issue_ref_pattern, commit_msgs, re.IGNORECASE):
                        issue_status = "PASS"
                        issue_id_verified = issue_num
                    else:
                        issue_status = "FAIL"
            else:
                # PR and issue have same number (common in GitHub where PR is an issue)
                issue_required = False
                issue_status = "NOT_APPLICABLE"

    if issue_data:
        with open(os.path.join(evidence_dir, "issue.json"), "w", encoding="utf-8") as f:
            json.dump(issue_data, f, indent=2)
    else:
        with open(os.path.join(evidence_dir, "issue.json"), "w", encoding="utf-8") as f:
            json.dump({"note": "No independent issue declared", "status": issue_status}, f, indent=2)

    GIT_ENV = {**os.environ, "GIT_NO_LAZY_FETCH": "1", "GIT_TERMINAL_PROMPT": "0"}

    # 6. Local Git Ancestry Verification
    # git merge-base --is-ancestor <base_commit> <target_commit>
    ancestry_cmd = ["git", "-C", git_dir, "merge-base", "--is-ancestor", base_commit, target_commit]
    try:
        ancestry_res = subprocess.run(ancestry_cmd, capture_output=True, text=True, env=GIT_ENV, timeout=5)
        ancestry_verified = (ancestry_res.returncode == 0)
    except Exception:
        ancestry_verified = False

    # 7. Merge Relationship Verification
    pr_merged = bool(pr_data.get("merged"))
    pr_merge_commit = pr_data.get("merge_commit_sha")
    pr_base_sha = pr_data.get("base", {}).get("sha")
    pr_head_sha = pr_data.get("head", {}).get("sha")

    merge_strategy = "unknown"
    merge_relationship_verified = False

    if pr_merged:
        if pr_merge_commit and pr_merge_commit.lower().startswith(target_commit.lower()[:8]):
            merge_strategy = "merge_commit"
            merge_relationship_verified = True
        elif pr_head_sha and pr_head_sha.lower().startswith(target_commit.lower()[:8]):
            merge_strategy = "fast_forward"
            merge_relationship_verified = True
        else:
            # Check if target commit contains PR head changes (squash/rebase)
            head_exists = False
            if pr_head_sha:
                try:
                    cat_chk = subprocess.run(
                        ["git", "-C", git_dir, "cat-file", "-e", pr_head_sha],
                        capture_output=True, env=GIT_ENV, timeout=5
                    )
                    head_exists = (cat_chk.returncode == 0)
                except Exception:
                    head_exists = False

            if head_exists:
                try:
                    head_ancestry = subprocess.run(
                        ["git", "-C", git_dir, "merge-base", "--is-ancestor", pr_head_sha, target_commit],
                        capture_output=True, text=True, env=GIT_ENV, timeout=5
                    )
                    if head_ancestry.returncode == 0:
                        merge_strategy = "rebase_ancestor"
                        merge_relationship_verified = True
                except Exception:
                    pass

            if not merge_relationship_verified:
                # Squash merge check: verify commit message or changed files
                try:
                    target_log = subprocess.run(
                        ["git", "-C", git_dir, "log", "-n", "1", "--format=%B", target_commit],
                        capture_output=True, text=True, env=GIT_ENV, timeout=5
                    ).stdout
                    if f"#{pr_num}" in target_log or pr_data.get("title", "").lower() in target_log.lower():
                        merge_strategy = "squash_merge"
                        merge_relationship_verified = True
                except Exception:
                    pass

    # 8. Changed Files Cross-Verification
    try:
        git_diff_files = subprocess.run(
            ["git", "-C", git_dir, "diff", "--name-only", base_commit, target_commit],
            capture_output=True, text=True, env=GIT_ENV, timeout=5
        ).stdout.splitlines()
    except Exception:
        git_diff_files = []

    pr_files = [f.get("filename") for f in (files_data or [])]
    spec_changed = spec.get("changed_files", [])

    diff_match = all(f in git_diff_files for f in spec_changed) and any(f in pr_files for f in spec_changed)

    # Master verdict for Ground Truth V3
    gt_v3_pass = (
        pr_merged
        and ancestry_verified
        and merge_relationship_verified
        and diff_match
        and (not issue_required or issue_status == "PASS")
    )

    result = {
        "transition_id": tid,
        "repo_name": repo_name,
        "pr_number": pr_num,
        "pr_title": pr_data.get("title"),
        "pr_merged": pr_merged,
        "pr_merge_commit_sha": pr_merge_commit,
        "pr_base_sha": pr_base_sha,
        "pr_head_sha": pr_head_sha,
        "base_commit": base_commit,
        "target_commit": target_commit,
        "ancestry_verified": ancestry_verified,
        "merge_strategy": merge_strategy,
        "merge_relationship_verified": merge_relationship_verified,
        "diff_match": diff_match,
        "issue_required": issue_required,
        "issue_id_verified": issue_id_verified,
        "issue_status": issue_status,
        "spec_sha256": hashlib.sha256(open(spec_path, "rb").read()).hexdigest(),
        "audit_fingerprint": fingerprint,
        "auditor_version": AUDITOR_VERSION,
        "overall_status": "PASS" if gt_v3_pass else "FAIL"
    }

    out_dir = "/code/rolemem-agent-memory/data/ground_truth_audit_v3"
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, f"{tid}.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    return result

if __name__ == "__main__":
    if len(sys.argv) > 1:
        specs = sorted(glob.glob(sys.argv[1]))
    else:
        specs = sorted(glob.glob("/code/rolemem-agent-memory/data/specs/trans_track_a_*.json") + glob.glob("/code/rolemem-agent-memory/data/specs/trans_gold_*.json"))
    print(f"Starting Ground Truth V3 Audit on {len(specs)} specs...")
    passed = 0
    for s in specs:
        r = audit_transition_v3(s)
        status = r.get("overall_status")
        print(f"  {r['transition_id']:45} : {status} (PR #{r.get('pr_number')}, Merge: {r.get('merge_strategy')}, Issue: {r.get('issue_status')})")
        if status == "PASS":
            passed += 1
    print(f"\nGround Truth V3 Audit Complete: {passed}/{len(specs)} PASS")
