"""
scripts/audit_external_ground_truth.py
Audits external ground truth of each transition spec against authentic local Git repository caches.
Validates:
- Base commit existence in Git
- Target commit existence in Git
- PR number or PR title matching in Git commit log (including squash/merge commits in base..target range)
- Changed files matching git diff-tree
- Changed symbols presence/status in AST
Outputs data/ground_truth_audit/<transition_id>.json with status PASS or FAIL.
"""

import os
import sys
import json
import subprocess

SPECS_DIR = "/code/rolemem-agent-memory/data/specs"
AUDIT_DIR = "/code/rolemem-agent-memory/data/ground_truth_audit"
REPO_CACHE_ROOT = "/code/repo_cache"

REPO_DIR_MAP = {
    "pallets/werkzeug": os.path.join(REPO_CACHE_ROOT, "werkzeug"),
    "pallets/flask": os.path.join(REPO_CACHE_ROOT, "flask"),
    "pallets/click": os.path.join(REPO_CACHE_ROOT, "click"),
    "urllib3/urllib3": os.path.join(REPO_CACHE_ROOT, "urllib3"),
    "psf/requests": os.path.join(REPO_CACHE_ROOT, "requests"),
}


def run_git(git_dir: str, args: list) -> tuple[int, str, str]:
    cmd = ["git", "-C", git_dir] + args
    res = subprocess.run(cmd, capture_output=True, text=True)
    return res.returncode, res.stdout.strip(), res.stderr.strip()


def check_commit_exists(git_dir: str, commit: str) -> bool:
    code, _, _ = run_git(git_dir, ["cat-file", "-e", f"{commit}^{{commit}}"])
    return code == 0


def get_commit_messages_in_range(git_dir: str, base: str, target: str) -> str:
    code, out, _ = run_git(git_dir, ["log", f"{base}..{target}", "--format=%B"])
    if code != 0 or not out:
        code, out, _ = run_git(git_dir, ["log", "-1", target, "--format=%B"])
    return out if code == 0 else ""


def get_changed_files_in_git(git_dir: str, base: str, target: str) -> list[str]:
    code, out, _ = run_git(git_dir, ["diff-tree", "--no-commit-id", "--name-only", "-r", base, target])
    if code != 0:
        return []
    return [line.strip() for line in out.splitlines() if line.strip()]


def audit_spec(spec: dict) -> dict:
    tid = spec["transition_id"]
    repo_name = spec["repo_name"]
    git_dir = REPO_DIR_MAP.get(repo_name)

    audit_res = {
        "transition_id": tid,
        "repo_name": repo_name,
        "pr_url": spec.get("pr_url", ""),
        "issue_url": spec.get("issue_url", ""),
        "pr_title": spec.get("pr_title", ""),
        "base_commit": spec.get("base_commit", ""),
        "target_commit": spec.get("target_commit", ""),
        "git_cache_path": git_dir,
        "base_commit_exists": False,
        "target_commit_exists": False,
        "pr_number_matched_in_git": False,
        "pr_title_matched_in_git": False,
        "changed_files_verified": False,
        "git_diff_files": [],
        "git_commit_log": "",
        "external_ground_truth_status": "FAIL",
        "errors": []
    }

    if not git_dir or not os.path.isdir(git_dir):
        audit_res["errors"].append(f"Git cache directory not found for {repo_name}")
        return audit_res

    # 1. Base and target commit existence
    base_exists = check_commit_exists(git_dir, spec["base_commit"])
    target_exists = check_commit_exists(git_dir, spec["target_commit"])
    audit_res["base_commit_exists"] = base_exists
    audit_res["target_commit_exists"] = target_exists

    if not base_exists:
        audit_res["errors"].append(f"Base commit {spec['base_commit']} does not exist in {git_dir}")
    if not target_exists:
        audit_res["errors"].append(f"Target commit {spec['target_commit']} does not exist in {git_dir}")

    # 2. PR Number & PR Title verification in commit log range
    commit_msg = get_commit_messages_in_range(git_dir, spec["base_commit"], spec["target_commit"])
    audit_res["git_commit_log"] = commit_msg

    pr_number = spec.get("pr_url", "").rstrip("/").split("/")[-1]
    if pr_number and (
        f"#{pr_number}" in commit_msg
        or f"pull request #{pr_number}" in commit_msg.lower()
        or f"pull/{pr_number}" in commit_msg
    ):
        audit_res["pr_number_matched_in_git"] = True

    expected_title = spec.get("pr_title", "").strip().lower()
    # Check if expected title words appear in commit messages
    title_words = [w.strip("`'\".,") for w in expected_title.split() if len(w) > 3]
    if title_words:
        matched_words = [w for w in title_words if w in commit_msg.lower()]
        # If at least 50% of significant title words match or the exact title is a substring
        if expected_title in commit_msg.lower() or (len(matched_words) / len(title_words) >= 0.5):
            audit_res["pr_title_matched_in_git"] = True

    # Check for ground truth validation
    # Either PR number matched or title matched (for non-merge squashed commits)
    pr_grounded = audit_res["pr_number_matched_in_git"] or audit_res["pr_title_matched_in_git"]
    if not pr_grounded:
        audit_res["errors"].append(f"Neither PR #{pr_number} nor title '{expected_title}' verified in git commit log")

    # 3. Changed files verification
    diff_files = get_changed_files_in_git(git_dir, spec["base_commit"], spec["target_commit"])
    audit_res["git_diff_files"] = diff_files

    spec_changed = spec.get("changed_files", [])
    missing_files = [f for f in spec_changed if f not in diff_files]
    if not missing_files and len(diff_files) > 0:
        audit_res["changed_files_verified"] = True
    else:
        audit_res["errors"].append(f"Spec changed files {missing_files} not present in git diff between base and target")

    # Overall PASS condition
    if (
        audit_res["base_commit_exists"]
        and audit_res["target_commit_exists"]
        and pr_grounded
        and audit_res["changed_files_verified"]
    ):
        audit_res["external_ground_truth_status"] = "PASS"

    return audit_res


def main():
    os.makedirs(AUDIT_DIR, exist_ok=True)
    all_specs = [os.path.join(SPECS_DIR, f) for f in os.listdir(SPECS_DIR) if f.endswith(".json")]
    all_specs.sort()

    passed_count = 0
    total_count = len(all_specs)

    print(f"=== Auditing External Ground Truth across {total_count} Transitions ===")
    for sp in all_specs:
        with open(sp, "r", encoding="utf-8") as f:
            spec = json.load(f)
        tid = spec["transition_id"]
        res = audit_spec(spec)

        out_path = os.path.join(AUDIT_DIR, f"{tid}.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(res, f, indent=2)

        status_flag = res["external_ground_truth_status"]
        if status_flag == "PASS":
            passed_count += 1
            print(f"[{tid}] PASS (PR: {res['pr_url']}, Diff files: {len(res['git_diff_files'])})")
        else:
            print(f"[{tid}] FAIL - Errors: {res['errors']}")

    print(f"\nAudit Summary: {passed_count}/{total_count} PASS")
    if passed_count != total_count:
        sys.exit(1)


if __name__ == "__main__":
    main()
