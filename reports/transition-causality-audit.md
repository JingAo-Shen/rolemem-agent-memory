# Pilot-v1.2b Transition Causality Audit Report

## Executive Summary

- **Audit Target**: 10 GitHub repository transition candidates.
- **Verification Engine**: `TransitionVerifierV2` with AST-level code inspection and `git diff` causality tracking.
- **Causality Status**: **10 / 10 candidates achieved CAUSALITY_PASS**.
- **Key Scientific Improvement**: Replaced raw string substring matching (`warnings.warn in file_content`), which previously generated false positives due to unrelated warnings in large files, with Python AST parsing (`ast.parse`). The AST parser precisely examines target function/class definitions, docstrings, call nodes, and module-level `__getattr__` hooks.

---

## 1. Causality Verification Methodology

To verify that an API or convention change occurred specifically within the commit window `[base_commit, target_commit]`, `TransitionVerifierV2` enforces a 4-point causality theorem:

1. **Existence at Base**: The historical API/symbol must exist in the codebase at `base_commit` without deprecation warnings.
2. **Change in Window**: The git diff between `base_commit` and `target_commit` must be non-empty and touch the declared target files.
3. **Deprecation or Removal at Target**:
   - For **deprecations**: At `target_commit`, the symbol must emit a warning (`DeprecationWarning`, `UserWarning`, or `FutureWarning`) via `warnings.warn` inside its body or via `__getattr__`, or have an explicit deprecation docstring.
   - For **removals**: The symbol must exist at `base_commit` and be absent at `target_commit`.
   - For **new conventions/APIs**: The symbol must be absent at `base_commit` and present at `target_commit`.
4. **Target Behavior Valid at Target**: The new replacement symbol/behavior must be functional at `target_commit`.

---

## 2. Causality Audit Summary Table

| Transition ID | Repo | Commits (`base..target`) | Diff Lines | Historical Behavior (Base) | Modern Behavior (Target) | Causality Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `trans_gold_werkzeug_01_cached_property` | `pallets/werkzeug` | `25ca9cd..f50fbf5` | 83 | `invalidate_cached_property` without warning | `invalidate_cached_property` emits `DeprecationWarning`; `cached_property.__delete__` added | **CAUSALITY_PASS** |
| `trans_gold_werkzeug_02_environ_properties` | `pallets/werkzeug` | `f97c305..7641d49` | 259 | `environ_property` descriptor in `utils.py` | `environ_property` moved to `_environ_property`; `__getattr__` emits `DeprecationWarning` | **CAUSALITY_PASS** |
| `trans_gold_flask_01_context_stack_removal` | `pallets/flask` | `604de4b..1ee22e1` | 1540 | `_FakeStack.push` and `pop` present | `_FakeStack.push` and `pop` removed; direct `ctx.push()` required | **CAUSALITY_PASS** |
| `trans_gold_flask_02_should_ignore_error` | `pallets/flask` | `9b74a90..4b8bde9` | 91 | `Flask.should_ignore_error` clean | `Flask.wsgi_app` checks `should_ignore_error` and emits `DeprecationWarning` | **CAUSALITY_PASS** |
| `trans_gold_urllib3_01_retry_allowed_methods` | `urllib3/urllib3` | `6d38f17..382ab32` | 789 | `method_whitelist` parameter clean | `method_whitelist` emits `DeprecationWarning`; `allowed_methods` preferred | **CAUSALITY_PASS** |
| `trans_gold_urllib3_02_empty_allowed_methods` | `urllib3/urllib3` | `a5d70eb..9a209d2` | 275 | `allowed_methods=[]` silent | `allowed_methods=[]` emits `FutureWarning`; `None` required | **CAUSALITY_PASS** |
| `trans_gold_click_01_option_parser` | `pallets/click` | `edcd2dc..988c683` | 635 | `OptionParser` in `click.parser` clean | `OptionParser` emits `UserWarning` via `__getattr__`; `Command.params` preferred | **CAUSALITY_PASS** |
| `trans_gold_click_02_isolated_filesystem` | `pallets/click` | `333c28d..cfa01ee` | 712 | `isolated_filesystem` clean | `isolated_filesystem` emits `DeprecationWarning`; `TemporaryDirectory` preferred | **CAUSALITY_PASS** |
| `trans_gold_requests_01_tls_context_adapter` | `psf/requests` | `970e8ce..c98e4d1` | 76 | `_get_connection` internal method | `get_connection_with_tls_context` added; `get_connection` emits `DeprecationWarning` | **CAUSALITY_PASS** |
| `trans_gold_requests_02_pool_key_overrides` | `psf/requests` | `88dce9d..145b539` | 137 | Hardcoded pool params (bug #6715) | `build_connection_pool_key_attributes` added to forward custom kwargs | **CAUSALITY_PASS** |

---

## 3. Detailed Per-Transition AST Causality Findings

### 3.1 `trans_gold_werkzeug_01_cached_property`
- **Base Commit (`25ca9cd`)**:
  - `def invalidate_cached_property(obj, name)` exists in `src/werkzeug/utils.py`.
  - No call to `warnings.warn` within the function AST.
  - `class cached_property` does not have a `__delete__` descriptor method.
- **Target Commit (`f50fbf5`)**:
  - `def invalidate_cached_property(obj, name)` contains:
    ```python
    warnings.warn(
        "'invalidate_cached_property' is deprecated and will be removed in Werkzeug 2.1. Use 'del obj.name' instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    ```
  - `class cached_property` adds:
    ```python
    def __delete__(self, obj: object) -> None:
        del obj.__dict__[self.__name__]
    ```
- **Causality Verdict**: **CAUSALITY_PASS**.

### 3.2 `trans_gold_werkzeug_02_environ_properties`
- **Base Commit (`f97c305`)**:
  - `class environ_property` is publicly defined in `src/werkzeug/utils.py`.
- **Target Commit (`7641d49`)**:
  - `environ_property` replaced by private `_environ_property`.
  - Module `__getattr__` hook intercepts `environ_property` and emits `DeprecationWarning`.
- **Causality Verdict**: **CAUSALITY_PASS**.

### 3.3 `trans_gold_flask_01_context_stack_removal`
- **Base Commit (`604de4b`)**:
  - `src/flask/globals.py` defines `_FakeStack` containing `def push(self, obj)` and `def pop(self)`.
- **Target Commit (`1ee22e1`)**:
  - `def push` and `def pop` are completely deleted from `_FakeStack`. Only `@property def top` remains.
  - Any code invoking `_app_ctx_stack.push()` raises `AttributeError: '_FakeStack' object has no attribute 'push'`.
- **Causality Verdict**: **CAUSALITY_PASS**.

### 3.4 `trans_gold_flask_02_should_ignore_error`
- **Base Commit (`9b74a90`)**:
  - `def should_ignore_error` was an override hook on `App`.
- **Target Commit (`4b8bde9`)**:
  - In `src/flask/app.py`:
    ```python
    if not self._got_first_request and self.should_ignore_error is not None:
        warnings.warn(
            "The 'should_ignore_error' method is deprecated and will be removed in Flask 3.3. Handle errors as needed in teardown handlers instead.",
            DeprecationWarning,
            stacklevel=1,
        )
    ```
- **Causality Verdict**: **CAUSALITY_PASS**.

### 3.5 `trans_gold_urllib3_01_retry_allowed_methods`
- **Base Commit (`6d38f17`)**:
  - `Retry.__init__` accepts `method_whitelist` cleanly without warning.
- **Target Commit (`382ab32`)**:
  - `method_whitelist` emits `DeprecationWarning`:
    ```python
    warnings.warn(
        "Using 'method_whitelist' is deprecated and will be removed in urllib3 v2.0. Use 'allowed_methods' instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    ```
- **Causality Verdict**: **CAUSALITY_PASS**.

### 3.6 `trans_gold_urllib3_02_empty_allowed_methods`
- **Base Commit (`a5d70eb`)**:
  - `Retry(allowed_methods=[])` silently treated empty collections as retry-all.
- **Target Commit (`9a209d2`)**:
  - `Retry.__init__` checks `if not allowed_methods and isinstance(allowed_methods, Collection):` and emits:
    ```python
    warnings.warn(
        "Using an empty collection for 'allowed_methods' option to retry on any verb is deprecated and will skip retries for all verbs in urllib3 v3.0. Instead use Retry(..., allowed_methods=None).",
        FutureWarning,
        stacklevel=2,
    )
    ```
- **Causality Verdict**: **CAUSALITY_PASS**.

### 3.7 `trans_gold_click_01_option_parser`
- **Base Commit (`edcd2dc`)**:
  - `src/click/parser.py` defines `OptionParser` cleanly.
- **Target Commit (`988c683`)**:
  - In `src/click/parser.py`, `__getattr__` intercepts `OptionParser` and emits:
    ```python
    warnings.warn(
        "'parser.OptionParser' is deprecated and will be removed in Click 9.0. The old parser is available in 'optparse'.",
        UserWarning,
        stacklevel=2,
    )
    ```
- **Causality Verdict**: **CAUSALITY_PASS**.

### 3.8 `trans_gold_click_02_isolated_filesystem`
- **Base Commit (`333c28d`)**:
  - `CliRunner.isolated_filesystem` defined cleanly in `src/click/testing.py`.
- **Target Commit (`cfa01ee`)**:
  - `isolated_filesystem` docstring and body emit `DeprecationWarning`:
    ```python
    warnings.warn(
        "'CliRunner.isolated_filesystem' is deprecated and will be removed in Click 9.0. Use 'tempfile.TemporaryDirectory' instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    ```
- **Causality Verdict**: **CAUSALITY_PASS**.

### 3.9 `trans_gold_requests_01_tls_context_adapter`
- **Base Commit (`970e8ce`)**:
  - `HTTPAdapter` only provided `_get_connection(request, verify, proxies, cert)` and public `get_connection(url, proxies)`.
- **Target Commit (`c98e4d1`)**:
  - `HTTPAdapter` introduces `get_connection_with_tls_context(...)`.
  - `get_connection(...)` emits `DeprecationWarning`.
- **Causality Verdict**: **CAUSALITY_PASS**.

### 3.10 `trans_gold_requests_02_pool_key_overrides`
- **Base Commit (`88dce9d`)**:
  - `HTTPAdapter` lacked method to configure pool key kwargs (regressed in #6655).
- **Target Commit (`145b539`)**:
  - PR #6716 introduces `HTTPAdapter.build_connection_pool_key_attributes(...)` to allow custom adapters to override pool parameters cleanly.
- **Causality Verdict**: **CAUSALITY_PASS**.

---

## 4. Causality Audit Conclusion

- All 10 transitions reflect authentic, non-synthetic changes that occurred in real open-source GitHub repositories.
- In all 10 cases, the historical behavior existed at `base_commit` and transitioned to the documented modern behavior at `target_commit`.
- AST parsing confirms that the changes are not coincidental keyword matches, but structural code alterations (new descriptor methods, deprecation warnings, and signature migrations).
