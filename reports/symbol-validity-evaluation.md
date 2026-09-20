# RoleMem Symbol-Level Validity Evaluation Report

## 1. Executive Summary

| Metric | File-Level Baseline (`F-file`) | Symbol-Level Mechanism (`F-symbol`) | Delta / Improvement |
| :--- | :---: | :---: | :---: |
| **False Invalidation Rate (FIR)** | **100.0%** (30/30) | **0.0%** (0/30) | **-100.0% reduction** |
| **Valid Memory Recall (VMR)** | **0.0%** | **100.0%** | **+100.0% gain** |
| **Stale Exposure Rate (SER)** | **0.0%** (0) | **0.0%** (0) | **0.0% (Zero leak increase)** |

---

## 2. Definitive Answers on Validity Mechanism

### Does symbol-level validity reduce false invalidation without increasing stale exposure?
**YES**. On the 40-case empirical validity benchmark (`data/false_invalidation_cases.jsonl`), `F-file` falsely invalidates **100.0%** of valid memories whenever any line in the enclosing file is modified.
In contrast, `F-symbol` achieves **0.0% False Invalidation Rate** while maintaining **0.0% Stale Exposure Rate** on modified/deprecated target symbols.

---

## 3. Methodological Nomenclature

- **`ASTStaleActionDetector`**: Output behavior evaluator that statically inspects generated code solutions for deprecated API calls or active stale invocations.
- **`SymbolValidity`**: Memory lifecycle validity mechanism that uses canonical AST dumps (`symbol_digest`) to determine whether a stored `MemoryRecord` remains `ACTIVE` or is transitioned to `INVALID`.

---

## 4. Benchmark Sample Matrix (First 15 Cases)

| Case ID | Symbol | Ground Truth Valid | F-file Verdict | F-symbol Verdict | Outcome |
| :--- | :--- | :---: | :---: | :---: | :--- |
| `false_inval_click_R_13f075c4_7a0a3447` | `R` | True | INVALID | ACTIVE | **PRESERVED** |
| `false_inval_click__posixify_13f075c4_7a0a3447` | `_posixify` | True | INVALID | ACTIVE | **PRESERVED** |
| `false_inval_click_make_str_13f075c4_7a0a3447` | `make_str` | True | INVALID | ACTIVE | **PRESERVED** |
| `false_inval_click_echo_13f075c4_7a0a3447` | `echo` | True | INVALID | ACTIVE | **PRESERVED** |
| `false_inval_click_format_filename_13f075c4_7a0a3447` | `format_filename` | True | INVALID | ACTIVE | **PRESERVED** |
| `false_inval_click_get_app_dir_13f075c4_7a0a3447` | `get_app_dir` | True | INVALID | ACTIVE | **PRESERVED** |
| `false_inval_click__detect_program_name_13f075c4_7a0a3447` | `_detect_program_name` | True | INVALID | ACTIVE | **PRESERVED** |
| `false_inval_click__expand_args_13f075c4_7a0a3447` | `_expand_args` | True | INVALID | ACTIVE | **PRESERVED** |
| `false_inval_click_R_1ca1cea0_13f075c4` | `R` | True | INVALID | ACTIVE | **PRESERVED** |
| `false_inval_click__posixify_1ca1cea0_13f075c4` | `_posixify` | True | INVALID | ACTIVE | **PRESERVED** |
| `false_inval_click_safecall_1ca1cea0_13f075c4` | `safecall` | True | INVALID | ACTIVE | **PRESERVED** |
| `false_inval_click_make_str_1ca1cea0_13f075c4` | `make_str` | True | INVALID | ACTIVE | **PRESERVED** |
| `false_inval_click_make_default_short_help_1ca1cea0_13f075c4` | `make_default_short_help` | True | INVALID | ACTIVE | **PRESERVED** |
| `false_inval_click_LazyFile_1ca1cea0_13f075c4` | `LazyFile` | True | INVALID | ACTIVE | **PRESERVED** |
| `false_inval_click_LazyFile.__init___1ca1cea0_13f075c4` | `LazyFile.__init__` | True | INVALID | ACTIVE | **PRESERVED** |
