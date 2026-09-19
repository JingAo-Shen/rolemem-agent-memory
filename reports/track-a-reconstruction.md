# Pilot-v1.3-r1 — Real Track A Reconstruction Report

## 1. Executive Summary

Following independent code audits during Pilot-v1.3, all 35 self-attested provisional transitions were invalidated due to lack of real sandbox verification. In Pilot-v1.3-r1, we executed a rigorous, authentic reconstruction protocol:
1. **Complete Decoupling**: Dataset builders are strictly prohibited from emitting synthetic `PASS` evidence.
2. **Noise & Dummy Commit Filtering**: AST and Git diff parsing pruned 87 raw candidates down to 21 high-confidence real transitions.
3. **Primary Reconstructed Cohort**: 10 transitions spanning 10 unique, premier Python open-source repositories (8 stale-sensitive, 2 control/evolution).
4. **100% Executed Machine Evidence**: Every single gate was verified via Bubblewrap sandboxed test execution, dual-source GitHub REST API calls, and cryptographic fingerprint checks.
5. **Formal Verification Verdict**: `TransitionVerifierV9` evaluated all 10 transitions as **10/10 ACCEPT** (8 `TRACK_A_PROVISIONAL_GOLD`, 2 `TRACK_A_CONTROL_ELIGIBLE`).

---

## 2. Invalidation & Archival of Self-Attested Data

- **Archived Location**: `data/archive/track_a_pilot_v1_3_self_attested.jsonl`
- **Spec Archive**: `data/archive/provisional_specs/`
- **Integrity Tag**: `INVALIDATED_SELF_ATTESTED_EVIDENCE`
- **Provisional Gold Count**: Successfully reset to `0` prior to new reconstruction.

---

## 3. Raw Candidate Pool Filtering (87 Candidates)

Using `scripts/analyze_transition_diff.py`, the candidate pool in `data/candidates/track_a_raw.jsonl` was comprehensively parsed with Python AST visitors and git diff inspection:

| Filter Reason | Count | Description |
| :--- | :---: | :--- |
| **Synthetic / Non-Existent Hashes** | 29 | Commit SHAs not present in actual git history |
| **Unmirrored Repositories** | 15 | Third-party repos without verified local mirror caches |
| **Formatting / Comment Diffs** | 19 | Pure whitespace, docstring, or typing diffs without behavioral change |
| **Test-Only Diffs** | 2 | Changes touching only `tests/` without package code modifications |
| **High Confidence Transitions** | **21** | Actionable architectural, deprecation, or API evolution transitions |

From the 21 validated candidates, a primary cohort of **10 high-confidence transitions** was selected for full fixture construction and empirical evaluation.

---

## 4. Reconstructed Cohort (10 Unique Repositories)

| # | Transition ID | Repository | PR # | Transition Type | Stale-Sensitive | Target Symbol |
| :-: | :--- | :--- | :-: | :---: | :-: | :--- |
| 1 | `trans_track_a_01_click_stream_deprecations` | `pallets/click` | #3695 | DEPRECATION | True | `get_binary_stream` |
| 2 | `trans_track_a_02_flask_should_ignore_error` | `pallets/flask` | #5899 | DEPRECATION | True | `should_ignore_error` |
| 3 | `trans_track_a_03_werkzeug_environ_property` | `pallets/werkzeug` | #3276 | DEPRECATION | True | `environ_property` |
| 4 | `trans_track_a_04_jinja_version_deprecation` | `pallets/jinja` | #2098 | DEPRECATION | True | `__version__` |
| 5 | `trans_track_a_05_itsdangerous_version_removal` | `pallets/itsdangerous` | #406 | API_REMOVAL | True | `__version__` |
| 6 | `trans_track_a_06_markupsafe_version_removal` | `pallets/markupsafe` | #499 | API_REMOVAL | True | `__version__` |
| 7 | `trans_track_a_07_pluggy_varnames_noself` | `pytest-dev/pluggy` | #632 | DEPRECATION | True | `varnames` |
| 8 | `trans_track_a_08_attrs_py313_replace_control` | `python-attrs/attrs` | #1383 | API_EVOLUTION | False | `replace_point` |
| 9 | `trans_track_a_09_virtualenv_drop_py38_control` | `pypa/virtualenv` | #3170 | API_REMOVAL | False | `requires_pyvenv_patch` |
| 10 | `trans_track_a_10_httpx_client_proxies_deprecation` | `encode/httpx` | #2879 | DEPRECATION | True | `build_custom_client` |

---

## 5. Machine Evidence Gate Verification Results

Each transition was evaluated against the 8 strict machine evidence gates:

```text
G1: Git Ancestry Check (git merge-base --is-ancestor)
G2: 2×2 Causal Counterfactual Matrix (Bubblewrap container execution)
G3: Test Evidence Relevance / Generated Test Verification
G4: Hidden Test Collection & Execution (Exit code 0, real pytest runner)
G5: Stale & Valid Fixture Control Differentiation
G6: Snapshot Hash Purity (Against pristine Git tree extracts)
G7: Dual-Source External Ground Truth V3 (GitHub REST API + Local Git)
G8: 10-Layer Semantic Coherence V2 (G1–G10 AST & Semantic Gates)
```

### Full Verification Matrix

| Transition ID | G1 | G2 | G3 | G4 | G5 | G6 | G7 | G8 | Verifier V9 Verdict | Eligibility |
| :--- | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :---: | :--- |
| `click_stream_deprecations` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **ACCEPT** | `TRACK_A_PROVISIONAL_GOLD` |
| `flask_should_ignore_error` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **ACCEPT** | `TRACK_A_PROVISIONAL_GOLD` |
| `werkzeug_environ_property` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **ACCEPT** | `TRACK_A_PROVISIONAL_GOLD` |
| `jinja_version_deprecation` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **ACCEPT** | `TRACK_A_PROVISIONAL_GOLD` |
| `itsdangerous_version_removal` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **ACCEPT** | `TRACK_A_PROVISIONAL_GOLD` |
| `markupsafe_version_removal` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **ACCEPT** | `TRACK_A_PROVISIONAL_GOLD` |
| `pluggy_varnames_noself` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **ACCEPT** | `TRACK_A_PROVISIONAL_GOLD` |
| `attrs_py313_replace_control` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **ACCEPT** | `TRACK_A_CONTROL_ELIGIBLE` |
| `virtualenv_drop_py38_control` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **ACCEPT** | `TRACK_A_CONTROL_ELIGIBLE` |
| `httpx_client_proxies_deprecation` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **ACCEPT** | `TRACK_A_PROVISIONAL_GOLD` |

**Overall Gate Pass Rate**: **80/80 (100.0%)**

---

## 6. Cryptographic Provenance

Every transition specification is bound to its fixture files, tests, controls, and machine evidence via the unified SHA-256 `audit_fingerprint`. Any file mutation or out-of-order execution immediately results in `STALE_AUDIT`, preventing forged evidence.
All machine evidence artifacts are archived under `data/`:
- `data/causal_counterfactual/`
- `data/hidden_test_evidence/`
- `data/fixture_controls/`
- `data/snapshot_eval/`
- `data/ground_truth_audit_v3/`
- `data/semantic_audit_v2/`
- `data/test_evidence/`
