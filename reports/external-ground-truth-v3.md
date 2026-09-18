# Pilot-v1.2d-r2 External Ground Truth V3 Audit Report

**Audit Status**: **10/10 VERIFIED PASS**  
**Auditor Version**: `v3.0.0-authenticated`  
**Execution Date**: 2026-09-18  
**Authentication**: GitHub REST API PAT authenticated  
**Evidence Source**: Automatically rendered from `data/ground_truth_audit_v3/*.json`

---

## 1. Executive Summary

In compliance with Pilot-v1.2d-r3 scientific mandates, the external ground truth verification report is **100% computed from raw JSON evidence** with zero manual tables.

Every transition candidate underwent dual-source verification:
1. **GitHub REST API Verification**: Live API queries fetching PR metadata, merged commit status, commit lists, pull request diffs, and issue linkage.
2. **Local Git Ancestry Verification**: Strict merge-base ancestry validation (`git merge-base --is-ancestor <base> <target> == 0`) on bare mirrors in `/code/repo_cache`.
3. **Artifact Persistence**: Complete raw responses saved directly to `data/external_evidence/<transition_id>/`.
4. **Cryptographic Fingerprint**: Each audit report computes an immutable `audit_fingerprint` binding `canonical_spec + fixture_manifest + hidden_test + controls + auditor_version + target_git_tree`.

---

## 2. Seed Transition Audit Matrix

| Transition ID | Repo | PR | Issue Status | Commit Ancestry | Files Matched | Fingerprint Status | Overall |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `trans_gold_click_01_option_parser` | `pallets/click` | #2592 (merged) | NOT_APPLICABLE | PASS (ancestor) | 1/1 matched | PASS | **PASS** |
| `trans_gold_click_02_isolated_filesystem` | `pallets/click` | #3704 (merged) | NOT_APPLICABLE | PASS (ancestor) | 1/1 matched | PASS | **PASS** |
| `trans_gold_flask_01_context_stack_removal` | `pallets/flask` | #4995 (merged) | NOT_APPLICABLE | PASS (ancestor) | 1/1 matched | PASS | **PASS** |
| `trans_gold_flask_02_should_ignore_error` | `pallets/flask` | #5899 (merged) | PASS (#5816 closed) | PASS (ancestor) | 1/1 matched | PASS | **PASS** |
| `trans_gold_requests_01_tls_context_adapter` | `psf/requests` | #6710 (merged) | NOT_APPLICABLE | PASS (ancestor) | 1/1 matched | PASS | **PASS** |
| `trans_gold_requests_02_pool_key_overrides` | `psf/requests` | #6716 (merged) | PASS (#6715 closed) | PASS (ancestor) | 1/1 matched | PASS | **PASS** |
| `trans_gold_urllib3_01_retry_allowed_methods` | `urllib3/urllib3` | #2000 (merged) | NOT_APPLICABLE | PASS (ancestor) | 1/1 matched | PASS | **PASS** |
| `trans_gold_urllib3_02_empty_allowed_methods` | `urllib3/urllib3` | #5223 (merged) | NOT_APPLICABLE | PASS (ancestor) | 1/1 matched | PASS | **PASS** |
| `trans_gold_werkzeug_01_cached_property` | `pallets/werkzeug` | #2084 (merged) | NOT_APPLICABLE | PASS (ancestor) | 1/1 matched | PASS | **PASS** |
| `trans_gold_werkzeug_02_environ_properties` | `pallets/werkzeug` | #3276 (merged) | NOT_APPLICABLE | PASS (ancestor) | 1/1 matched | PASS | **PASS** |

---

## 3. Strict Assertions Verified
- Rendered PR number strictly matches raw GitHub JSON: `rendered_pr_number == ground_truth_json['pr_number']` (e.g. Click 01 is #2592, Flask 01 is #4995).
- Zero manual edits permitted.
