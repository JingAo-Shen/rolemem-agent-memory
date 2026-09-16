"""
Unit tests for TransitionVerifier in Pilot-v1.2a.
Validates programmatic verification rules:
- Synthetic commit SHAs must be flagged and rejected
- Repository existence, license, and language verification
- Semantic overlap checks between candidate descriptions and PR/Issue text
- Rejection reason tracking
"""

import pytest
from src.transition_verifier import TransitionVerifier


def test_transition_verifier_rejects_synthetic_candidate(monkeypatch):
    """Verifies that candidate with synthetic commit SHAs returns overall_status='REJECTED'."""
    verifier = TransitionVerifier(token="dummy_test_token")

    # Mock HTTP get to return 404 on commit check
    def mock_http_get(url, **kwargs):
        if "repos/mock_owner/mock_repo/commits" in url:
            return 422, None
        if "repos/mock_owner/mock_repo" in url:
            return 200, {
                "id": 12345,
                "full_name": "mock_owner/mock_repo",
                "language": "Python",
                "license": {"spdx_id": "MIT"},
                "default_branch": "main",
                "fork": False,
                "archived": False
            }
        return 404, None

    monkeypatch.setattr(verifier, "_http_get", mock_http_get)

    candidate = {
        "transition_id": "trans_test_synthetic",
        "repo_name": "mock_owner/mock_repo",
        "base_commit": "1111222233334444555566667777888899990000",
        "history_commit": "1111222233334444555566667777888899990000",
        "transition_commit": "2222333344445555666677778888999900001111",
        "target_commit": "3333444455556666777788889999000011112222",
        "pr_url": "https://github.com/mock_owner/mock_repo/pull/1",
        "issue_url": "https://github.com/mock_owner/mock_repo/issues/1",
        "repository_change": "Deprecate legacy API in favor of modern API",
        "changed_symbols": ["legacy_api", "modern_api"],
        "existing_tests": "tests/test_mock.py"
    }

    report = verifier.verify_candidate(candidate)
    assert report["overall_status"] == "REJECTED"
    assert report["commit_verification"] == "FAIL"
    assert any("failed" in r for r in report["rejection_reasons"])


def test_transition_verifier_accepts_verified_candidate(monkeypatch):
    """Verifies that candidate with genuine repository, commits, and PR returns overall_status='VERIFIED'."""
    verifier = TransitionVerifier(token="dummy_test_token")

    def mock_http_get(url, **kwargs):
        if "compare" in url:
            return 200, {
                "status": "ahead",
                "ahead_by": 1,
                "behind_by": 0,
                "total_commits": 1,
                "files": [{"filename": "src/module.py"}]
            }
        if "/commits/" in url:
            return 200, {
                "sha": "abcdef1234567890abcdef1234567890abcdef12",
                "commit": {
                    "message": "Deprecate legacy API",
                    "author": {"date": "2026-01-01T00:00:00Z"}
                },
                "parents": [{"sha": "parent1234567890"}]
            }
        if "/pulls/1" in url:
            return 200, {
                "number": 1,
                "title": "Deprecate legacy API helper",
                "body": "This PR deprecates legacy_api in favor of modern_api.",
                "state": "closed",
                "merged": True,
                "merge_commit_sha": "abcdef1234567890abcdef1234567890abcdef12",
                "base": {"sha": "base123"},
                "head": {"sha": "head123"}
            }
        if "/issues/1" in url:
            return 200, {
                "number": 1,
                "title": "Deprecate legacy API",
                "body": "Legacy API should be replaced.",
                "state": "closed"
            }
        if "repos/mock_owner/mock_repo" in url:
            return 200, {
                "id": 12345,
                "full_name": "mock_owner/mock_repo",
                "language": "Python",
                "license": {"spdx_id": "MIT"},
                "default_branch": "main",
                "fork": False,
                "archived": False
            }
        return 404, None

    monkeypatch.setattr(verifier, "_http_get", mock_http_get)

    candidate = {
        "transition_id": "trans_test_verified",
        "repo_name": "mock_owner/mock_repo",
        "base_commit": "abcdef1234567890abcdef1234567890abcdef12",
        "history_commit": "abcdef1234567890abcdef1234567890abcdef12",
        "transition_commit": "abcdef1234567890abcdef1234567890abcdef12",
        "target_commit": "abcdef1234567890abcdef1234567890abcdef12",
        "pr_url": "https://github.com/mock_owner/mock_repo/pull/1",
        "issue_url": "https://github.com/mock_owner/mock_repo/issues/1",
        "repository_change": "Deprecate legacy API in favor of modern API",
        "changed_symbols": ["legacy_api", "modern_api"],
        "existing_tests": "tests/test_mock.py",
        "generated_tests": None,
        "test_evidence_source": "PR #1"
    }

    report = verifier.verify_candidate(candidate)
    assert report["overall_status"] == "VERIFIED"
    assert report["commit_verification"] == "PASS"
    assert report["semantic_evidence_match"] == "PASS"
    assert report["test_verification"] == "PASS"
