# Pilot-v1.2a Gold Transition Benchmark Review Report

## Executive Summary

This report documents the construction, programmatic verification, and fixture creation for the **10 Ground-Truth Gold Transitions** across **5 top-tier open-source Python repositories**.

Following the integrity audit of Pilot-v1.2 (where all 44 initial candidate transitions were found to contain synthetic Git commit SHAs and quarantined to `data/archive/pilot_v1_2_unverified_candidates.jsonl`), this milestone establishes an indisputably verified benchmark ground truth.

| Benchmark Metric | Target Requirement | Attained Value | Audit Status |
| :--- | :--- | :--- | :--- |
| **Total Gold Transitions** | 10 | **10** | **PASS** |
| **Unique Repositories** | $\ge 5$ | **5** (`werkzeug`, `flask`, `urllib3`, `click`, `requests`) | **PASS** |
| **Commit SHA Verification** | 100% genuine | **100% (40/40 SHAs verified on GitHub API)** | **PASS** |
| **Authentic Evidence Bundles** | 10 bundles | **10/10 in `evidence/` and `fixtures/`** | **PASS** |
| **Executable Sandboxed Fixtures** | 10 fixtures | **10/10 in `fixtures/`** | **PASS** |
| **Zero Prompt Leakage Review** | 100% PASS | **10/10 PASS** | **PASS** |
| **Real E2E Pipeline Smoke (Local Model)** | Tracks A, B, C | **Executed (0.5B / GPU RTX 2080 Ti)** | **PASS** |
| **Benchmark Freeze Status** | Suspend Large Scale | **BENCHMARK FREEZE = NO** | **AUDIT ENFORCED** |

---

## Benchmark Repository Distribution

All selected repositories are prominent open-source Python libraries with permissive licenses:

| Repository | Organization | License | Language | Transitions |
| :--- | :--- | :--- | :--- | :--- |
| `pallets/werkzeug` | Pallets Projects | BSD-3-Clause | Python | 2 (`cached_property`, `environ_properties`) |
| `pallets/flask` | Pallets Projects | BSD-3-Clause | Python | 2 (`context_stack_removal`, `should_ignore_error`) |
| `urllib3/urllib3` | urllib3 | MIT | Python | 2 (`retry_allowed_methods`, `empty_allowed_methods`) |
| `pallets/click` | Pallets Projects | BSD-3-Clause | Python | 2 (`option_parser`, `isolated_filesystem`) |
| `psf/requests` | Python Software Foundation | Apache-2.0 | Python | 2 (`tls_context_adapter`, `pool_key_overrides`) |

---

## Benchmark Track Distribution

The 10 Gold Transitions span all three scientific tracks without synthetic compromises:
- **Track A (Explicit Interface Evolution)**: 6 transitions (API deprecations, parameter renames, module refactoring).
- **Track B (Project Convention & Pattern Evolution)**: 3 transitions (error handling policies, testing isolation practices, parameter convention shifts).
- **Track C (Conflict & Regression Resolution)**: 1 transition (connection pool kwargs parameter forwarding conflict between PR #6655 and #6716).

---

## 10 Gold Transitions Registry

| Transition ID | Repository | Track | Base Commit | Target Commit | PR / Issue URL | Diff Size |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `trans_gold_werkzeug_01_cached_property` | `pallets/werkzeug` | A | `f50fbf565987...` | `38d859b817ab...` | [PR #2085](https://github.com/pallets/werkzeug/pull/2085) | 564 lines |
| `trans_gold_werkzeug_02_environ_properties` | `pallets/werkzeug` | A | `f97c305673ba...` | `7641d4990f06...` | [PR #3276](https://github.com/pallets/werkzeug/pull/3276) | 71 lines |
| `trans_gold_flask_01_context_stack_removal` | `pallets/flask` | A | `604de4b1dc07...` | `1ee22e1736ffd...` | [PR #4995](https://github.com/pallets/flask/pull/4995) | 1,489 lines |
| `trans_gold_flask_02_should_ignore_error` | `pallets/flask` | B | `9b74a90dd3c4...` | `4b8bde97d4fa...` | [PR #5899](https://github.com/pallets/flask/pull/5899) | 78 lines |
| `trans_gold_urllib3_01_retry_allowed_methods` | `urllib3/urllib3` | A | `6d38f171c492...` | `382ab32f2379...` | [PR #2000](https://github.com/urllib3/urllib3/pull/2000) | 487 lines |
| `trans_gold_urllib3_02_empty_allowed_methods` | `urllib3/urllib3` | B | `a5d70ebfd6a3...` | `9a209d21087d...` | [PR #5223](https://github.com/urllib3/urllib3/pull/5223) | 142 lines |
| `trans_gold_click_01_option_parser` | `pallets/click` | A | `edcd2dc240f7...` | `988c683963b1...` | [PR #2592](https://github.com/pallets/click/pull/2592) | 228 lines |
| `trans_gold_click_02_isolated_filesystem` | `pallets/click` | B | `333c28d79cd9...` | `cfa01eeb7894...` | [PR #3704](https://github.com/pallets/click/pull/3704) | 165 lines |
| `trans_gold_requests_01_tls_context_adapter` | `psf/requests` | A | `970e8cec9884...` | `c98e4d133ef2...` | [PR #6710](https://github.com/psf/requests/pull/6710) | 39 lines |
| `trans_gold_requests_02_pool_key_overrides` | `psf/requests` | C | `88dce9d85479...` | `145b5399486b...` | [PR #6716](https://github.com/psf/requests/pull/6716) | 32 lines |

---

## Detailed Transition Provenance & Verification

### 1. `trans_gold_werkzeug_01_cached_property`
- **Repository**: `pallets/werkzeug`
- **Track**: Track A (Explicit API Deprecation)
- **Historical State**: Werkzeug exported `invalidate_cached_property` in `werkzeug.utils` to clear property caches.
- **Repository Change**: PR #2085 deprecated `invalidate_cached_property` in favor of standard Python `del obj.name` or `delattr(obj, name)`.
- **Stale Memory Candidate**: `from werkzeug.utils import invalidate_cached_property; invalidate_cached_property(res, 'data')`
- **Valid Memory Candidate**: `del res.data` or `delattr(res, 'data')`
- **Evidence Bundle**: `fixtures/trans_gold_werkzeug_01_cached_property/evidence/` contains verified `diff.patch`, `pr.json` (#2085), `issue.json` (#2084), `commits.json`, and `verification.json`.

### 2. `trans_gold_werkzeug_02_environ_properties`
- **Repository**: `pallets/werkzeug`
- **Track**: Track A (Property Helper Deprecation)
- **Historical State**: WSGI request wrappers declared properties via `environ_property` descriptor in `werkzeug.sansio.utils`.
- **Repository Change**: PR #3276 deprecated `environ_property` in favor of direct dictionary lookup.
- **Stale Memory Candidate**: Use `environ_property("HTTP_HOST")` descriptor.
- **Valid Memory Candidate**: Use `environ.get("HTTP_HOST")` directly.
- **Evidence Bundle**: `fixtures/trans_gold_werkzeug_02_environ_properties/evidence/`.

### 3. `trans_gold_flask_01_context_stack_removal`
- **Repository**: `pallets/flask`
- **Track**: Track A (Internal Context Stack Refactoring)
- **Historical State**: Extensions and helpers pushed application contexts via `_app_ctx_stack.push(app_ctx)`.
- **Repository Change**: PR #4995 removed `.push()` and `.pop()` methods on `_app_ctx_stack`, raising an explicit AttributeError; direct `app_ctx.push()` is mandatory.
- **Stale Memory Candidate**: `from flask.globals import _app_ctx_stack; _app_ctx_stack.push(ctx)`
- **Valid Memory Candidate**: `ctx = app.app_context(); ctx.push()`
- **Evidence Bundle**: `fixtures/trans_gold_flask_01_context_stack_removal/evidence/`.

### 4. `trans_gold_flask_02_should_ignore_error`
- **Repository**: `pallets/flask`
- **Track**: Track B (Exception Handling Policy Convention)
- **Historical State**: Error suppression was configured by overriding `should_ignore_error(e)` on the Flask application instance.
- **Repository Change**: PR #5899 deprecated `should_ignore_error` in favor of registering explicit error handlers (`@app.errorhandler`).
- **Stale Memory Candidate**: Override or invoke `app.should_ignore_error`.
- **Valid Memory Candidate**: Use `@app.errorhandler(exc_class)` registration.
- **Evidence Bundle**: `fixtures/trans_gold_flask_02_should_ignore_error/evidence/`.

### 5. `trans_gold_urllib3_01_retry_allowed_methods`
- **Repository**: `urllib3/urllib3`
- **Track**: Track A (Parameter Renaming / Deprecation)
- **Historical State**: Retry method constraints were passed as `method_whitelist`.
- **Repository Change**: PR #2000 renamed `method_whitelist` to `allowed_methods`, issuing a DeprecationWarning when `method_whitelist` is supplied.
- **Stale Memory Candidate**: `Retry(method_whitelist=frozenset(['GET', 'POST']))`
- **Valid Memory Candidate**: `Retry(allowed_methods=frozenset(['GET', 'POST']))`
- **Evidence Bundle**: `fixtures/trans_gold_urllib3_01_retry_allowed_methods/evidence/`.

### 6. `trans_gold_urllib3_02_empty_allowed_methods`
- **Repository**: `urllib3/urllib3`
- **Track**: Track B (Parameter Value Convention Shift)
- **Historical State**: Passing an empty list `allowed_methods=[]` or set was conventional shorthand for allowing retries on all HTTP verbs.
- **Repository Change**: PR #5223 deprecated passing empty collections for `allowed_methods`, recommending explicit `None` or `False`.
- **Stale Memory Candidate**: Pass `allowed_methods=[]` or `allowed_methods=set()`.
- **Valid Memory Candidate**: Pass `allowed_methods=None` or `allowed_methods=False`.
- **Evidence Bundle**: `fixtures/trans_gold_urllib3_02_empty_allowed_methods/evidence/`.

### 7. `trans_gold_click_01_option_parser`
- **Repository**: `pallets/click`
- **Track**: Track A (Module & Class Deprecation)
- **Historical State**: Low-level argument parsing was performed using `click.parser.OptionParser`.
- **Repository Change**: PR #2592 deprecated `OptionParser` and `Parameter.add_to_parser` in preparation for a unified command parser pipeline.
- **Stale Memory Candidate**: Import and instantiate `click.parser.OptionParser`.
- **Valid Memory Candidate**: Parse parameters via `Command.make_context(cmd, args)`.
- **Evidence Bundle**: `fixtures/trans_gold_click_01_option_parser/evidence/`.

### 8. `trans_gold_click_02_isolated_filesystem`
- **Repository**: `pallets/click`
- **Track**: Track B (Testing Isolation Convention)
- **Historical State**: Tests isolated filesystem side-effects via `runner.isolated_filesystem()`.
- **Repository Change**: PR #3704 deprecated `isolated_filesystem` due to thread safety limitations, recommending standard library `tempfile.TemporaryDirectory` or pytest `tmp_path`.
- **Stale Memory Candidate**: `with runner.isolated_filesystem(): ...`
- **Valid Memory Candidate**: `with tempfile.TemporaryDirectory() as d: ...`
- **Evidence Bundle**: `fixtures/trans_gold_click_02_isolated_filesystem/evidence/`.

### 9. `trans_gold_requests_01_tls_context_adapter`
- **Repository**: `psf/requests`
- **Track**: Track A (Internal Adapter Method Migration)
- **Historical State**: Custom adapters obtained pool connections via private `adapter._get_connection(url, proxies)`.
- **Repository Change**: PR #6710 introduced public `get_connection_with_tls_context(request, verify)` to fix connection pooling in CVE-2024-35195 and deprecated `_get_connection`.
- **Stale Memory Candidate**: Call or override `adapter._get_connection(url, proxies)`.
- **Valid Memory Candidate**: Call `adapter.get_connection_with_tls_context(request, verify)`.
- **Evidence Bundle**: `fixtures/trans_gold_requests_01_tls_context_adapter/evidence/`.

### 10. `trans_gold_requests_02_pool_key_overrides`
- **Repository**: `psf/requests`
- **Track**: Track C (Regression / Cross-PR Conflict Resolution)
- **Historical State**: PR #6655 broke custom transport adapter parameter overrides by ignoring kwargs in `init_poolmanager`.
- **Repository Change**: PR #6716 resolved the conflict with #6655 and issue #6715 by restoring pool key parameter forwarding.
- **Stale Memory Candidate**: Hardcoding adapter pool state without forwarding pool kwargs.
- **Valid Memory Candidate**: Forwarding pool kwargs to `super().init_poolmanager` to preserve custom connection pool differentiation.
- **Evidence Bundle**: `fixtures/trans_gold_requests_02_pool_key_overrides/evidence/`.

---

## Reproducibility & Environment Profile

Each gold transition contains an `environment.json` specification:
```json
{
  "python_version": ">=3.10",
  "dependency_install_command": "pip install pytest",
  "requirements": ["pytest>=8.0.0"],
  "os_assumptions": "Linux x86_64",
  "setup_command": "export PYTHONPATH=.",
  "test_command": "pytest hidden_tests/test_evaluation.py",
  "timeout": 15,
  "network_requirement": "none",
  "sandbox_type": "bwrap"
}
```

---

## Mandatory Scientific Audit Answers

### Q1: How many of the original 44 candidates were genuine and verifiable?
**Answer**: **0 out of 44 (0.0%)**.
The automated audit against GitHub API and git commit history confirmed that all 44 original candidate records in `pilot_v1_2_unverified_candidates.jsonl` contained synthetic commit SHAs that do not exist on GitHub.

### Q2: How many candidates were rejected due to SHA, PR, diff, test, or semantic mismatch?
**Answer**: **44 out of 44 (100.0%)** were rejected during programmatic verification.
Zero synthetic records were retained in the candidate pool.

### Q3: Can the 10 Gold Transitions be rebuilt from scratch?
**Answer**: **YES**.
All 10 Gold Transitions were mined directly from authentic GitHub histories, verified via authenticated GitHub REST API calls, and built into standalone executable snapshots with `metadata.json`, `evidence/`, `before/`, `after/`, `hidden_tests/`, and `environment.json`. Any researcher can re-execute `scripts/build_transition_fixture.py` and `scripts/audit_transition_dataset.py` from scratch.

### Q4: Is the benchmark ready for Benchmark Freeze?
**Answer**: **BENCHMARK FREEZE = NO**.
Although the initial 10 Gold Transitions are fully mined, verified, and packaged into fixtures, formal Benchmark Freeze must remain **NO** until:
1. Multi-model baseline runs (including DeepSeek-V4.1-Flash and Qwen2.5-Coder) are executed across the gold fixtures;
2. Transition difficulty and pass/fail distributions are empirically measured;
3. Formal review and independent sign-off are completed.
