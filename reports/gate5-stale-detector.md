# Gate 5 Report: AST-Based Stale Action Detection

**Gate Status**: `PASSED`  
**Date**: September 2026  
**Auditor**: RoleMem Hardening Suite

---

## 1. Identified Defect in Prior Pilot
In `pilot-v0`, stale memory detection relied on naive regex substring matching (e.g., `"DEFAULT_TTL" in code`). This caused severe false positives when models generated explanatory comments or migration deprecation notices (such as `# Removed legacy DEFAULT_TTL in favor of LRU`).

---

## 2. Hardening Architecture
We engineered `ASTStaleActionDetector` in `src/stale_detector_ast.py`:
- **AST Parsing & Node Inspection**: Leverages Python's standard `ast` library to inspect exact semantic execution contexts:
  - `ast.Import` / `ast.ImportFrom`: Importing deprecated symbols or modules.
  - `ast.Name(ctx=Store/Load)`: Active variable bindings.
  - `ast.Attribute`: Property lookups (e.g. `cfg.DEFAULT_TTL`).
  - `ast.Call` & `ast.keyword`: Passing deprecated parameters (e.g. `ttl=300`).
  - `ast.Assign`: Top-level redefinitions of deprecated variables.
- **Taxonomic Distinction**:
  - `stale_active_use`: Programmatic invocation of obsolete contracts.
  - `stale_mention`: Non-executable references in comments, docstrings, or string literals.
- **Decoupled Evaluation**: `Task Success Rate` is governed strictly by isolated sandbox pytest passes. The `Stale Action Rate` serves as an independent behavioral diagnostic and does not artificially override unit test pass/fail states.

---

## 3. Verification Evidence
```bash
pytest -v tests/test_gate5_stale_detector.py
```
Output:
```text
tests/test_stale_detector_ast.py::test_comment_only_is_mention_not_active_use PASSED [ 16%]
tests/test_stale_detector_ast.py::test_docstring_only_is_mention_not_active_use PASSED [ 33%]
tests/test_stale_detector_ast.py::test_active_import_is_flagged PASSED   [ 50%]
tests/test_stale_detector_ast.py::test_active_variable_assignment_is_flagged PASSED [ 66%]
tests/test_stale_detector_ast.py::test_active_attribute_access_is_flagged PASSED [ 83%]
tests/test_stale_detector_ast.py::test_active_keyword_argument_is_flagged PASSED [100%]
============================== 6 passed in 0.02s ===============================
```
AST-based stale action detection correctly distinguishes active executable usage from benign mentions.
