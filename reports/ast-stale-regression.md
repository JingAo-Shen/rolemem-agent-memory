# AST Stale Action Detector Regression & Correction Report (Pilot-v1.2d-r1)

> **Status**: RESOLVED & FORMALLY CORRECTED  
> **Module**: `src/stale_detector_ast.py`  
> **Unit Tests**: `tests/test_stale_detector_ast.py` (11/11 PASSED)  
> **Timestamp**: 2026-09-17  

---

## 1. Formal Retraction of "AST Clean 4/4"

In Pilot-v1.2d, it was erroneously reported that the Qwen2.5-Coder-7B E2E run achieved:
$$\text{AST Clean Rate} = 4/4 \quad (100\%)$$

**This claim is formally retracted.**  
Upon rigorous auditing of the raw generated code for `trans_gold_urllib3_01_retry_allowed_methods`, the 7B model generated:
```python
def build_custom_retry(methods):
    return Retry(
        total=5,
        backoff_factor=0.2,
        status_forcelist=[500, 502, 503, 504],
        method_whitelist=methods
    )
```
The model actively invoked the deprecated keyword `method_whitelist` instead of modern `allowed_methods`. The earlier detector failed to catch this due to an AST inspection blindspot.

With the corrected detector:
$$\text{True AST Clean Rate} = 3/4 \quad (75.0\%)$$

---

## 2. Root Cause Analysis of the False Negative

### 2.1 The AST Inspection Blindspot
In Python AST, function call arguments have two distinct forms:
- Positional arguments (`args: list[expr]`)
- Keyword arguments (`keywords: list[keyword]`), where each `keyword` has `arg: str` and `value: expr`.

The legacy `detect_stale_actions_ast()` only inspected:
- `ast.Name(id=...)`
- `ast.Attribute(attr=...)`
- `ast.Import` and `ast.ImportFrom`

When a function call passed a deprecated parameter name (e.g. `Retry(method_whitelist=methods)`), `method_whitelist` appeared as `keyword.arg` (a raw Python string on the AST keyword node), **not** as an `ast.Name` or `ast.Attribute`. Consequently, the detector visited the identifier as an AST keyword container and never compared `keyword.arg` against `deprecated_symbols`!

### 2.2 The Fix in `src/stale_detector_ast.py`
The AST detector was overhauled to support:
1. **Direct Keyword Argument Inspection**:
   ```python
   for kw in node.keywords:
       if kw.arg and kw.arg in self.deprecated_symbols:
           self.active_stale_nodes.append({
               "type": "KeywordArg",
               "lineno": kw.lineno,
               "symbol": kw.arg,
               "name": kw.arg
           })
   ```
2. **Declarative Pattern Matcher (`stale_action_patterns`)**:
   Matches complex syntactic idioms such as:
   - Keyword argument presence: `{"node_type": "keyword", "name": "method_whitelist"}`
   - Deprecated empty collection values: `{"node_type": "call_kw_value", "name": "allowed_methods", "value_type": "empty_collection"}`
3. **Symbol Digest Decoupling**:
   Distinguishes comments and docstrings (`stale_mention: true`, `stale_active_use: false`) from active invocation (`stale_active_use: true`).

---

## 3. Regression Test Verification (11/11 PASSED)

`tests/test_stale_detector_ast.py` verifies all regression scenarios:
1. `test_comment_only_is_mention_not_active_use`: Mention in comment does NOT trigger active use.
2. `test_docstring_only_is_mention_not_active_use`: Mention in docstring does NOT trigger active use.
3. `test_active_import_is_flagged`: `from werkzeug.utils import invalidate_cached_property` -> FLAGGED.
4. `test_active_variable_assignment_is_flagged`: Assignment to deprecated symbol -> FLAGGED.
5. `test_active_attribute_access_is_flagged`: `app._app_ctx_stack` -> FLAGGED.
6. `test_active_keyword_argument_is_flagged`: Keyword argument in function call -> FLAGGED.
7. `test_active_dict_subscript_and_string_literal_is_flagged`: Deprecated key in dict -> FLAGGED.
8. `test_active_assignment_string_literal_is_flagged`: String literal assignment -> FLAGGED.
9. `test_active_comparison_literal_is_flagged`: String literal in comparison -> FLAGGED.
10. `test_urllib3_method_whitelist_keyword_is_flagged_active`: `Retry(method_whitelist=methods)` -> FLAGGED.
11. `test_urllib3_empty_allowed_methods_pattern`: `Retry(allowed_methods=[])` -> FLAGGED.

---

## 4. Re-Evaluation of Qwen2.5-Coder-7B E2E Generation

| Task ID | Deprecated Symbol Tested | Generated AST Status | Detected Stale Nodes |
| :--- | :--- | :---: | :--- |
| `trans_gold_werkzeug_01_cached_property` | `invalidate_cached_property` | **CLEAN** | None (`delattr(instance, attr_name)`) |
| `trans_gold_click_02_isolated_filesystem` | `isolated_filesystem` | **CLEAN** | None (`tmp_path.as_posix()`) |
| `trans_gold_requests_01_tls_context_adapter` | `HTTPAdapter.get_connection` | **CLEAN** | None (uses modern PoolManager) |
| `trans_gold_urllib3_01_retry_allowed_methods` | `method_whitelist` | **STALE ACTIVE USE** | Line 13: `KeywordArg: method_whitelist` |

**Final Retracted Tally**:
- Clean: **3 / 4 (75.0%)**
- Stale Active Use: **1 / 4 (25.0%)**
- Zero False Negatives.
