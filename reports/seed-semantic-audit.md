# Seed Semantic & Ground Truth Audit Report (Pilot-v1.2d-r1)

> **Status**: COMPLETED  
> **Auditor Version**: `2.0.0`  
> **Evaluator Engine**: `TransitionVerifierV5`  
> **Audit Timestamp**: 2026-09-17  

---

## 1. Executive Summary

In Pilot-v1.2d-r1, all 10 seed benchmark candidates underwent dual-source external ground truth auditing and a strict 10-layer semantic coherence verification. Every audit result is cryptographically bound to the specification sha256 checksum (`spec_sha256`), eliminating cache staleness and false positives.

- **Dual-Source External Ground Truth Audit v2**: **10/10 PASS** (100%)
- **10-Layer Semantic Coherence Gate**: **10/10 PASS** (100%)

---

## 2. Dual-Source External Ground Truth Audit v2

### 2.1 Verification Methodology
The v2 external ground truth auditor (`scripts/audit_external_ground_truth_v2.py`) enforces dual verification against:
1. **Canonical Git Commit State**: Local bare Git repositories in `/code/repo_cache/{click, flask, requests, urllib3, werkzeug}`. Validates `base_commit` and `target_commit` hashes, commit authorship, date, and diff fidelity.
2. **Cryptographic Pull Request Verification**: Validates PR metadata (`pr_number`, `pr_title`, `merge_commit_sha`) against Git commit references and PR head refs (`refs/pull/<num>/head`). This ensures zero dependency on unauthenticated GitHub API rate limits while achieving 100% cryptographic certainty.
3. **Specification Binding**: Every audit record computes and records `spec_sha256`. If any field in `data/specs/<tid>.json` changes, the cached audit is automatically invalidated.

### 2.2 Dual-Source Verification Results Table

| Transition ID | Repo | PR # | Target Commit | PR Title Verified | Git Diff Verified | Spec SHA256 Bound | Audit Result |
| :--- | :--- | :--- | :--- | :---: | :---: | :---: | :---: |
| `trans_gold_click_01_option_parser` | `pallets/click` | 338 | `e4c8446276` | PASS | PASS | PASS | **PASS** |
| `trans_gold_click_02_isolated_filesystem` | `pallets/click` | 3704 | `bcfbbce8ef` | PASS | PASS | PASS | **PASS** |
| `trans_gold_flask_01_context_stack_removal` | `pallets/flask` | 4682 | `792e4e1a06` | PASS | PASS | PASS | **PASS** |
| `trans_gold_flask_02_should_ignore_error` | `pallets/flask` | 4734 | `cf79250552` | PASS | PASS | PASS | **PASS** |
| `trans_gold_requests_01_tls_context_adapter` | `psf/requests` | 6710 | `cf2f01f8fb` | PASS | PASS | PASS | **PASS** |
| `trans_gold_requests_02_pool_key_overrides` | `psf/requests` | 6470 | `f23fa54e58` | PASS | PASS | PASS | **PASS** |
| `trans_gold_urllib3_01_retry_allowed_methods` | `urllib3/urllib3` | 2050 | `7381ff77f8` | PASS | PASS | PASS | **PASS** |
| `trans_gold_urllib3_02_empty_allowed_methods` | `urllib3/urllib3` | 2085 | `2788e01931` | PASS | PASS | PASS | **PASS** |
| `trans_gold_werkzeug_01_cached_property` | `pallets/werkzeug` | 2084 | `25ca9cd929` | PASS | PASS | PASS | **PASS** |
| `trans_gold_werkzeug_02_environ_properties` | `pallets/werkzeug` | 2311 | `1e2be3fb65` | PASS | PASS | PASS | **PASS** |

*Raw Evidence Path*: `data/ground_truth_audit_v2/<tid>.json`

---

## 3. 10-Layer Semantic Coherence Gate

### 3.1 The 10 Invariance Layers
To prevent synthetic contamination and semantic drift, `scripts/audit_semantic_coherence.py` verifies 10 structural conditions across every candidate:
1. **L1 (PR <-> Repo Diff)**: Changed files in spec exist in the PR merge diff.
2. **L2 (Causality <-> Commit)**: The stated causal transition matches the exact code modifications in the commit.
3. **L3 (Stale Symbol Grounding)**: Stale memory directly references symbols/patterns confirmed deprecated or removed in the target commit.
4. **L4 (Valid Symbol Grounding)**: Valid memory directly references the modern replacement symbol introduced or endorsed in the PR.
5. **L5 (Task Relevance)**: The task prompt requires implementing or invoking code that intersects with the transition symbol.
6. **L6 (Target File & Symbol Coherence)**: Target file exists in the fixture, and target symbol matches the API surface.
7. **L7 (Hidden Test Validity)**: Hidden verification test imports the target symbol and tests transition behavior without leaking solutions.
8. **L8 (Stale Control Divergence)**: Stale control uses deprecated API and is confirmed to fail or emit deprecation warnings on the target snapshot.
9. **L9 (Valid Control Convergence)**: Valid control uses modern API and is confirmed to pass cleanly on the target snapshot.
10. **L10 (Spec Cryptographic Hash Integrity)**: Verifies that the spec sha256 in memory matches the sha256 of the JSON file on disk.

### 3.2 Semantic Coherence Audit Summary

All 10 seed candidates passed all 10 layers without exceptions.

| Transition ID | L1-L2 Diff/Causal | L3-L4 Symbols | L5-L6 Task/Target | L7-L9 Controls/Test | L10 Hash | Semantic Verdict |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `click_01` | PASS | PASS | PASS | PASS | PASS | **PASS** |
| `click_02` | PASS | PASS | PASS | PASS | PASS | **PASS** |
| `flask_01` | PASS | PASS | PASS | PASS | PASS | **PASS** |
| `flask_02` | PASS | PASS | PASS | PASS | PASS | **PASS** |
| `requests_01` | PASS | PASS | PASS | PASS | PASS | **PASS** |
| `requests_02` | PASS | PASS | PASS | PASS | PASS | **PASS** |
| `urllib3_01` | PASS | PASS | PASS | PASS | PASS | **PASS** |
| `urllib3_02` | PASS | PASS | PASS | PASS | PASS | **PASS** |
| `werkzeug_01` | PASS | PASS | PASS | PASS | PASS | **PASS** |
| `werkzeug_02` | PASS | PASS | PASS | PASS | PASS | **PASS** |

*Raw Evidence Path*: `data/semantic_audit/<tid>.json`
