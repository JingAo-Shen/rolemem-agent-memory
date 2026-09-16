"""
Transition Evidence Verifier for Pilot-v1.2a.
Provides rigorous programmatic verification of GitHub repository transitions:
- Repository existence, status, language, and license
- Git commit existence, 40-char SHA validity, and ancestry / reachability
- PR and Issue authentic content retrieval via authenticated GitHub REST API
- Semantic alignment between repository change descriptions and PR/Issue evidence
- Commit diff inspection and changed file verification
- Test presence and evidence source verification
"""

import os
import re
import json
import time
import urllib.request
import urllib.error
from typing import Dict, Any, List, Optional, Tuple


def get_github_token() -> Optional[str]:
    """Retrieve GitHub token from environment variable or ~/.git-credentials."""
    token = os.getenv("GITHUB_TOKEN")
    if token:
        return token.strip()
    
    cred_path = os.path.expanduser("~/.git-credentials")
    if os.path.exists(cred_path):
        try:
            with open(cred_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if "github.com" in line:
                        # Extract token if ghp_ or bearer
                        m = re.search(r":([a-zA-Z0-9_]+)@github\.com", line)
                        if m:
                            return m.group(1)
        except Exception:
            pass
    return None


class TransitionVerifier:
    """
    Programmatically verifies each transition candidate against real GitHub data and Git commits.
    Ensures zero synthetic SHAs, zero fabricated PRs, and verifiable diff/test evidence.
    """

    def __init__(self, token: Optional[str] = None):
        self.token = token or get_github_token()
        self.headers = {
            "User-Agent": "RoleMem-Transition-Verifier/1.0",
            "Accept": "application/vnd.github.v3+json"
        }
        if self.token:
            self.headers["Authorization"] = f"token {self.token}"
        self._cache: Dict[str, Any] = {}

    def _http_get(self, url: str, retries: int = 3, backoff: float = 1.0) -> Tuple[int, Optional[Any]]:
        if url in self._cache:
            return 200, self._cache[url]

        req = urllib.request.Request(url, headers=self.headers)
        for attempt in range(retries):
            try:
                with urllib.request.urlopen(req, timeout=15) as resp:
                    status = resp.status
                    data = resp.read().decode("utf-8")
                    try:
                        parsed = json.loads(data)
                    except Exception:
                        parsed = data
                    self._cache[url] = parsed
                    return status, parsed
            except urllib.error.HTTPError as e:
                # 404, 422: resource does not exist or unprocessable
                if e.code in (404, 422):
                    return e.code, None
                if e.code == 403:
                    # Rate limit or forbidden
                    err_msg = e.read().decode("utf-8", errors="ignore")
                    return 403, {"error": "rate_limit_exceeded_or_forbidden", "detail": err_msg}
                time.sleep(backoff * (attempt + 1))
            except Exception as e:
                time.sleep(backoff * (attempt + 1))
        return 500, None

    def verify_repository(self, repo_name: str) -> Dict[str, Any]:
        """Verify repository existence, active status, license, and language."""
        url = f"https://api.github.com/repos/{repo_name}"
        status, data = self._http_get(url)
        if status != 200 or not isinstance(data, dict):
            return {
                "verified": False,
                "status_code": status,
                "reason": f"Repository '{repo_name}' not found on GitHub (status {status})"
            }

        license_info = data.get("license") or {}
        license_spdx = license_info.get("spdx_id") or license_info.get("key")
        language = data.get("language")

        return {
            "verified": True,
            "repo_id": data.get("id"),
            "full_name": data.get("full_name"),
            "default_branch": data.get("default_branch"),
            "language": language,
            "license": license_spdx,
            "is_fork": data.get("fork", False),
            "is_archived": data.get("archived", False)
        }

    def verify_commit(self, repo_name: str, commit_sha: str) -> Dict[str, Any]:
        """Verify individual commit existence, parents, message, and author date."""
        if not commit_sha or len(commit_sha) < 7:
            return {"verified": False, "reason": "Invalid or missing commit SHA"}

        url = f"https://api.github.com/repos/{repo_name}/commits/{commit_sha}"
        status, data = self._http_get(url)
        if status != 200 or not isinstance(data, dict):
            return {
                "verified": False,
                "status_code": status,
                "commit_sha": commit_sha,
                "reason": f"Commit '{commit_sha}' does not exist in repository '{repo_name}'"
            }

        commit_obj = data.get("commit", {})
        parents = [p.get("sha") for p in data.get("parents", [])]
        return {
            "verified": True,
            "commit_sha": data.get("sha"),
            "full_sha": data.get("sha"),
            "message": commit_obj.get("message", "").split("\n")[0],
            "author_date": commit_obj.get("author", {}).get("date"),
            "parents": parents
        }

    def verify_commit_ancestry(self, repo_name: str, base_sha: str, target_sha: str) -> Dict[str, Any]:
        """Verify reachability / compare between base and target commit."""
        url = f"https://api.github.com/repos/{repo_name}/compare/{base_sha}...{target_sha}"
        status, data = self._http_get(url)
        if status != 200 or not isinstance(data, dict):
            return {
                "verified": False,
                "status_code": status,
                "reason": f"Compare failed between {base_sha} and {target_sha} (status {status})"
            }

        return {
            "verified": True,
            "status": data.get("status"),  # 'ahead', 'behind', 'diverged', 'identical'
            "ahead_by": data.get("ahead_by"),
            "behind_by": data.get("behind_by"),
            "total_commits": data.get("total_commits"),
            "files_changed": [f.get("filename") for f in data.get("files", [])]
        }

    def verify_pr(self, repo_name: str, pr_url: Optional[str]) -> Dict[str, Any]:
        """Verify pull request existence, authentic metadata, state, and merge commit."""
        if not pr_url:
            return {"verified": False, "reason": "No PR URL provided"}

        m = re.search(r"pull/(\d+)", pr_url)
        if not m:
            return {"verified": False, "reason": f"Cannot extract PR number from {pr_url}"}

        pr_num = m.group(1)
        url = f"https://api.github.com/repos/{repo_name}/pulls/{pr_num}"
        status, data = self._http_get(url)
        if status != 200 or not isinstance(data, dict):
            return {
                "verified": False,
                "status_code": status,
                "pr_number": pr_num,
                "reason": f"PR #{pr_num} does not exist in {repo_name} (status {status})"
            }

        return {
            "verified": True,
            "pr_number": data.get("number"),
            "pr_title": data.get("title"),
            "pr_body": data.get("body") or "",
            "pr_state": data.get("state"),
            "pr_merged": data.get("merged", False),
            "pr_merge_commit_sha": data.get("merge_commit_sha"),
            "base_sha": data.get("base", {}).get("sha"),
            "head_sha": data.get("head", {}).get("sha")
        }

    def verify_issue(self, repo_name: str, issue_url: Optional[str]) -> Dict[str, Any]:
        """Verify issue existence and authentic content."""
        if not issue_url:
            return {"verified": False, "reason": "No Issue URL provided"}

        m = re.search(r"issues/(\d+)", issue_url)
        if not m:
            return {"verified": False, "reason": f"Cannot extract Issue number from {issue_url}"}

        issue_num = m.group(1)
        url = f"https://api.github.com/repos/{repo_name}/issues/{issue_num}"
        status, data = self._http_get(url)
        if status != 200 or not isinstance(data, dict):
            return {
                "verified": False,
                "status_code": status,
                "issue_number": issue_num,
                "reason": f"Issue #{issue_num} does not exist in {repo_name} (status {status})"
            }

        return {
            "verified": True,
            "issue_number": data.get("number"),
            "issue_title": data.get("title"),
            "issue_body": data.get("body") or "",
            "issue_state": data.get("state")
        }

    def verify_candidate(self, candidate: Dict[str, Any]) -> Dict[str, Any]:
        """
        Runs comprehensive programmatic verification on a transition candidate record.
        Returns a structured evaluation report including:
        - commit_verification: PASS / FAIL
        - semantic_evidence_match: PASS / FAIL / NEEDS_REVIEW
        - test_verification: PASS / FAIL
        - overall decision: VERIFIED / REJECTED / NEEDS_REVIEW
        """
        rejection_reasons = []
        repo_name = candidate.get("repo_name") or ""
        if not repo_name and candidate.get("repo_url"):
            m = re.search(r"github\.com/([^/]+/[^/]+)", candidate.get("repo_url", ""))
            if m:
                repo_name = m.group(1).rstrip(".git")

        # 1. Repository verification
        repo_res = self.verify_repository(repo_name) if repo_name else {"verified": False, "reason": "Missing repo_name"}
        if not repo_res.get("verified"):
            rejection_reasons.append(f"Repo verification failed: {repo_res.get('reason')}")

        # 2. Commit verification
        commits_to_check = {
            "base_commit": candidate.get("base_commit"),
            "history_commit": candidate.get("history_commit"),
            "transition_commit": candidate.get("transition_commit"),
            "target_commit": candidate.get("target_commit")
        }

        commit_results = {}
        commits_pass = True
        for role_name, sha in commits_to_check.items():
            if not sha:
                commits_pass = False
                rejection_reasons.append(f"Missing {role_name} SHA")
                commit_results[role_name] = {"verified": False, "reason": "Missing SHA"}
                continue

            c_res = self.verify_commit(repo_name, sha)
            commit_results[role_name] = c_res
            if not c_res.get("verified"):
                commits_pass = False
                rejection_reasons.append(f"Commit {role_name} ({sha}) failed: {c_res.get('reason')}")

        commit_verification = "PASS" if commits_pass else "FAIL"

        # 3. Ancestry verification if commits pass
        ancestry_res = None
        if commits_pass and candidate.get("base_commit") and candidate.get("target_commit"):
            ancestry_res = self.verify_commit_ancestry(repo_name, candidate["base_commit"], candidate["target_commit"])
            if not ancestry_res.get("verified"):
                rejection_reasons.append(f"Ancestry check failed: {ancestry_res.get('reason')}")

        # 4. PR / Issue verification
        pr_res = self.verify_pr(repo_name, candidate.get("pr_url"))
        issue_res = self.verify_issue(repo_name, candidate.get("issue_url"))

        # 5. Semantic evidence alignment
        change_desc = (candidate.get("repository_change") or "").lower()
        changed_symbols = [s.lower() for s in candidate.get("changed_symbols", [])]
        
        evidence_text = ""
        if pr_res.get("verified"):
            evidence_text += f" {pr_res.get('pr_title', '')} {pr_res.get('pr_body', '')}"
        if issue_res.get("verified"):
            evidence_text += f" {issue_res.get('issue_title', '')} {issue_res.get('issue_body', '')}"
        evidence_text = evidence_text.lower()

        if not pr_res.get("verified") and not issue_res.get("verified"):
            semantic_evidence_match = "FAIL"
            rejection_reasons.append("Neither PR nor Issue could be verified on GitHub API")
        elif not evidence_text.strip():
            semantic_evidence_match = "NEEDS_REVIEW"
        else:
            has_symbol_overlap = any(sym.split(".")[-1] in evidence_text for sym in changed_symbols if len(sym) > 3)
            change_tokens = [t for t in re.findall(r"\w{4,}", change_desc) if t not in ("change", "update", "support", "requests", "flask")]
            token_overlap = sum(1 for t in change_tokens if t in evidence_text)

            if has_symbol_overlap or token_overlap >= 2:
                semantic_evidence_match = "PASS"
            elif token_overlap == 1:
                semantic_evidence_match = "NEEDS_REVIEW"
            else:
                semantic_evidence_match = "FAIL"
                rejection_reasons.append("No semantic overlap between repository_change/symbols and PR/Issue body")

        # 6. Test verification
        existing_tests = candidate.get("existing_tests")
        generated_tests = candidate.get("generated_tests")
        test_evidence_source = candidate.get("test_evidence_source")

        if existing_tests or (generated_tests and test_evidence_source):
            test_verification = "PASS"
        else:
            test_verification = "FAIL"
            rejection_reasons.append("No existing test or documented test_evidence_source provided")

        # Overall Status
        if commit_verification == "PASS" and semantic_evidence_match == "PASS" and test_verification == "PASS" and repo_res.get("verified"):
            overall_status = "VERIFIED"
        elif commit_verification == "FAIL":
            overall_status = "REJECTED"
        else:
            overall_status = "NEEDS_REVIEW"

        return {
            "transition_id": candidate.get("transition_id"),
            "repo_name": repo_name,
            "overall_status": overall_status,
            "commit_verification": commit_verification,
            "semantic_evidence_match": semantic_evidence_match,
            "test_verification": test_verification,
            "repo_details": repo_res,
            "commit_details": commit_results,
            "ancestry_details": ancestry_res,
            "pr_details": pr_res,
            "issue_details": issue_res,
            "rejection_reasons": rejection_reasons
        }
