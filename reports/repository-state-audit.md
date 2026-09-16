# Pilot-v1.2b Repository-State Grounding Audit Report

## Executive Summary

- **Audit Phase**: Pilot-v1.2b Repository-State Grounding & Gold Transition Correction
- **Status**: **INSPECTION COMPLETE — PROVISIONAL GOLD V2 ESTABLISHED**
- **Benchmark Freeze**: **NO (STRICTLY SUSPENDED)**
- **Audit Target**: 10 candidate transitions in `data/gold/gold_transitions.jsonl`
- **Core Transformation**: Completely eliminated synthetic micro-mock fixtures (`FIXTURE_TEMPLATES`). All repository files in `fixtures_v2/` are now extracted directly from local Git commit objects (`/code/repo_cache/{werkzeug, flask, urllib3, click, requests}`) via `git archive`.

---

## 1. Local Repository Object Grounding

All 5 core repositories were cloned into `/code/repo_cache/` with remote blob-fetching enabled:

| Repository | Local Cache Path | Upstream URL | Default Branch |
| :--- | :--- | :--- | :--- |
| `pallets/werkzeug` | `/code/repo_cache/werkzeug` | `https://github.com/pallets/werkzeug.git` | `main` |
| `pallets/flask` | `/code/repo_cache/flask` | `https://github.com/pallets/flask.git` | `main` |
| `urllib3/urllib3` | `/code/repo_cache/urllib3` | `https://github.com/urllib3/urllib3.git` | `main` |
| `pallets/click` | `/code/repo_cache/click` | `https://github.com/pallets/click.git` | `main` |
| `psf/requests` | `/code/repo_cache/requests` | `https://github.com/psf/requests.git` | `main` |

Every commit SHA across `base_commit`, `history_commit`, `transition_commit`, and `target_commit` was verified directly against local Git object storage (`git cat-file -e <sha>`).

---

## 2. Transition Metadata Corrections

During local Git verification, several critical metadata discrepancies were identified and corrected:

1. **`trans_gold_werkzeug_01_cached_property`**:
   - *Previous Metadata*: PR #2085, `base_commit`: `f50fbf5...`, `target_commit`: `38d859b...`.
   - *Audit Finding*: `f50fbf5...` is actually the merge commit for **PR #2084** ("Merge pull request #2084 from pallets/delete-cached-property"), not the base commit. The true base commit prior to PR #2084 is `25ca9cd92956e48a38f7a32c837e0f8a54c8ae31`.
   - *Correction*: Updated PR URL to #2084, `base_commit` to `25ca9cd...`, `target_commit` to `f50fbf5...`, and `transition_commit` to `004b446...`.

2. **`trans_gold_werkzeug_02_environ_properties`**:
   - *Previous Metadata*: `changed_files: ["src/werkzeug/sansio/utils.py"]`.
   - *Audit Finding*: `src/werkzeug/sansio/utils.py` does not contain `environ_property`. The descriptor was historically defined in `src/werkzeug/utils.py` and `src/werkzeug/wrappers/request.py`. PR #3276 deprecated it via module `__getattr__` in `src/werkzeug/utils.py`.
   - *Correction*: Updated `changed_files` to `["src/werkzeug/utils.py", "src/werkzeug/wrappers/request.py"]`.

3. **`trans_gold_requests_02_pool_key_overrides`**:
   - *Previous Metadata*: `changed_symbols: ["HTTPAdapter.init_poolmanager", "poolmanager.PoolManager"]`.
   - *Audit Finding*: PR #6716 resolved issue #6715 specifically by adding `HTTPAdapter.build_connection_pool_key_attributes` to allow custom adapters to override pool parameters.
   - *Correction*: Updated `changed_symbols` to `["HTTPAdapter.build_connection_pool_key_attributes"]`.

4. **`trans_gold_flask_02_should_ignore_error`**:
   - *Audit Finding*: PR #5899 deprecates `should_ignore_error` on the Flask application instance, with the docstring and `CHANGES.rst` explicitly stating: *"The `should_ignore_error` method is deprecated and will be removed in Flask 3.3. Handle errors as needed in teardown handlers instead."*
   - *Correction*: Re-grounded convention migration to `@app.teardown_request`.

---

## 3. Ground-Truth Fixture Construction (`fixtures_v2/`)

All formal benchmark fixtures are now created via `scripts/build_real_repo_fixture.py`.
- **Synthetic Templates Demoted**: The legacy `FIXTURE_TEMPLATES` in `scripts/build_transition_fixture.py` have been archived to `tests/synthetic_fixtures/` labeled `SYNTHETIC — UNIT TEST ONLY`.
- **Pristine Git Snapshots**: `before/` and `after/` directories in `fixtures_v2/<transition_id>/` contain authentic Python package files extracted via `git archive <sha> <pkg_path> | tar -x`.

### Directory Layout per Fixture:
```text
fixtures_v2/{transition_id}/
├── metadata.json                 # Pinned repository metadata and commit SHAs
├── environment.json              # Sandbox execution specification (bwrap, python version)
├── before/                       # Genuine package tree at base_commit
│   └── src/{package}/...
├── after/                        # Genuine package tree at target_commit
│   └── src/{package}/...
├── hidden_tests/
│   └── test_evaluation.py       # Hidden evaluation test
└── controls/
    ├── stale_solution.py         # Solution using deprecated/removed pattern
    ├── valid_solution.py         # Solution using modern pattern
    ├── stale_result.json         # Output of stale control execution in bwrap
    └── valid_result.json         # Output of valid control execution in bwrap
```

---

## 4. Sandbox Control Execution & Fidelity Audit

Using `scripts/run_fixture_controls.py`, both `stale_solution.py` and `valid_solution.py` were executed inside `SecureSandboxExecutor` (Bubblewrap namespace isolation, no network access, memory limits):

| Transition ID | Repo | Stale Control Result | Valid Control Result | Overall Status |
| :--- | :--- | :--- | :--- | :--- |
| `trans_gold_werkzeug_01_cached_property` | `pallets/werkzeug` | **FAIL** (`DeprecationWarning` caught) | **PASS** | **PASS** |
| `trans_gold_werkzeug_02_environ_properties` | `pallets/werkzeug` | **FAIL** (`DeprecationWarning` caught) | **PASS** | **PASS** |
| `trans_gold_flask_01_context_stack_removal` | `pallets/flask` | FAIL (`ImportError: url_quote`) | FAIL (`ImportError: url_quote`) | **NEEDS_ENV_RECONSTRUCTION** |
| `trans_gold_flask_02_should_ignore_error` | `pallets/flask` | **FAIL** (`DeprecationWarning` caught) | **PASS** | **PASS** |
| `trans_gold_urllib3_01_retry_allowed_methods` | `urllib3/urllib3` | FAIL (`ModuleNotFoundError: six.moves`) | FAIL (`ModuleNotFoundError: six.moves`) | **NEEDS_ENV_RECONSTRUCTION** |
| `trans_gold_urllib3_02_empty_allowed_methods` | `urllib3/urllib3` | **FAIL** (`FutureWarning` caught) | **PASS** | **PASS** |
| `trans_gold_click_01_option_parser` | `pallets/click` | **FAIL** (`UserWarning` caught) | **PASS** | **PASS** |
| `trans_gold_click_02_isolated_filesystem` | `pallets/click` | **FAIL** (`DeprecationWarning` caught) | **PASS** | **PASS** |
| `trans_gold_requests_01_tls_context_adapter` | `psf/requests` | **FAIL** (`DeprecationWarning` caught) | **PASS** | **PASS** |
| `trans_gold_requests_02_pool_key_overrides` | `psf/requests` | **FAIL** (AssertionError on attrs) | **PASS** | **PASS** |

### Environment Findings:
- **8 Fixtures Passed Completely**: 8 out of 10 fixtures achieved 100% control fidelity. Stale solutions were definitively caught by pytest deprecation/assertion checks, and valid solutions passed with zero warnings.
- **2 Fixtures Encountered Environment Mismatches**:
  - `trans_gold_flask_01_context_stack_removal`: Flask 2.2 requires Werkzeug < 3.0 (for `url_quote`). Running against host Werkzeug 3.2 triggered an import failure.
  - `trans_gold_urllib3_01_retry_allowed_methods`: Urllib3 1.26 bundled `six 1.12`, whose legacy dynamic import hooks are incompatible with Python 3.13.
  - **Scientific Decision**: Neither was forced or patched with synthetic mocks. Both are classified strictly as `NEEDS_ENV_RECONSTRUCTION` pending virtual environment pin locking.

---

## 5. Answers to Core Audit Questions

1. **Q1: 10 条 Provisional Gold 中，经 repository-state + causality audit 后，最终几条通过？**
   - **8 条通过**，2 条因宿主 Python 3.13 / 跨包版本不匹配标记为 `NEEDS_ENV_RECONSTRUCTION`。
2. **Q2: 几条因 PR/语义错误被删除或修改？**
   - **4 条修改**：
     - `werkzeug_01`: 修正为 PR #2084，修正 base commit SHA。
     - `werkzeug_02`: 修正 changed_files 真实路径。
     - `requests_02`: 修正 changed_symbols 为新增的 pool key 方法。
     - `flask_02`: 修正语义约定为 teardown handlers。
3. **Q3: 几条真实 repository snapshots 能在 sandbox 内成功重建并运行 pytest？**
   - 10 条均成功从真实 Git tree 提取；在当前宿主环境沙箱下，**8 条** 成功执行 pytest，2 条需专用 pin-locked venv。
4. **Q4: 真实 repo snapshot 下，stale control 是否全部 FAIL？**
   - **是**。在 8 条合格 fixture 中，stale control 全部判定为 FAIL（100% 成功捕获过时代码和告警）。
5. **Q5: 真实 repo snapshot 下，valid control 是否全部 PASS？**
   - **是**。在 8 条合格 fixture 中，valid control 全部判定为 PASS（100% 成功通过测试且零告警）。
6. **Q6: Qwen2.5-Coder-7B 真实 E2E 验证是否成功？**
   - **是**。全流程在 RTX 2080 Ti GPU 上执行，结果详见 `reports/real-7b-e2e-smoke.md`。
7. **Q7: 当前是否达到 BENCHMARK FREEZE 标准？**
   - **NO (绝对未达到)**。当前通过规模为 8 条，未扩充至 40–80 条，仍有 2 条需环境重建，保持 `PROVISIONAL_GOLD_V2`。
