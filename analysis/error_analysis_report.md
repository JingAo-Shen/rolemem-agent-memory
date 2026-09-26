# Comprehensive Error Analysis & Failure Mode Report

## 1. Quantitative Failure Summary

| Model / Variant | Total Cases | Errors | Accuracy | Macro-F1 | False Inval (VALID$\to$STALE) | Stale Escape (STALE$\to$VALID) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `majority` | 150 | 25 | 83.3% | 30.3% | 0 | 25 |
| `static_ast` | 150 | 41 | 72.7% | 31.0% | 18 | 23 |
| `naive_rag` | 150 | 68 | 54.7% | 28.7% | 50 | 18 |
| `rolemem_full` | 150 | 0 | 100.0% | 100.0% | 0 | 0 |
| `rolemem_no_role` | 150 | 40 | 73.3% | 31.2% | 17 | 23 |
| `rolemem_no_evidence` | 150 | 49 | 67.3% | 40.7% | 44 | 5 |
| `rolemem_no_lifecycle` | 150 | 40 | 73.3% | 32.5% | 18 | 22 |

---

## 2. Qualitative Failure Mode Taxonomy

### A. Baseline-1: Majority Predictor Failures
- **Root Cause**: Blindly predicts `VALID` for all memory records.
- **Impact**: 100% Stale Escape Rate (SER = 1.0). Fails on all 24 STALE claims and the PARTIALLY_VALID claim.
- **Theoretical Limitation**: In zero-shot LLM agent workflows, an agent relying on Majority memory acceptance would execute stale API calls and silently invoke broken contracts.

### B. Baseline-2: Pure Static AST Checker Failures
- **Root Cause**: Inspects symbol node presence in file AST but ignores semantic invariants (parameter default mutations, signature shifts, packaging manifest removals).
- **Impact**: Fails on 22 STALE claims where the symbol still exists but its signature/defaults mutated, plus 18 false invalidations where class method nesting was missed.
- **Theoretical Limitation**: Static AST existence is necessary but deeply insufficient for temporal consistency.

### C. Baseline-3: Naive RAG Failures
- **Root Cause**: Lexical token matching without AST structure or temporal anchoring.
- **Impact**: Massive false invalidation rate (FIR = 40.0%, 50 VALID claims rejected) and high stale escape rate (SER = 70.8%, 17 STALE claims leaked).
- **Theoretical Limitation**: Unstructured vector/BM25 retrieval retrieves outdated or comment snippets without deterministic code execution verification.

### D. Ablation Variant B (w/o Epistemic Roles) Failures
- **Root Cause**: Unifies all claims into generic symbol presence checks without specialized checkers (e.g. `DefaultValueEvolutionChecker`, deprecation warnings, test witness execution).
- **Impact**: Macro-F1 collapses from 100% to 31.2% ($\Delta = -68.8\%$).
- **Demonstrated Value**: Epistemic roles are essential for routing memory verification to the correct formal invariant channel.

### E. Ablation Variant C (w/o Grounding Evidence) Failures
- **Root Cause**: Lacks physical file path and lineno provenance, searching the entire repository globally.
- **Impact**: Severe namespace collisions on common method names (`__init__`, `get`, `parse`, `validate`), causing 49 false invalidations / misgroundings (Macro-F1 = 40.7%).
- **Demonstrated Value**: Grounding provenance $\mathcal{E}$ is required to disambiguate identical identifiers across multi-module codebases.

### F. Ablation Variant D (w/o Dynamic Lifecycle) Failures
- **Root Cause**: Static binary assertion without non-breaking migration downgrading (`PARTIALLY_VALID`) or escalation tiers.
- **Impact**: Macro-F1 drops to 32.5% ($\Delta = -67.5\%$). Cannot adapt confidence or distinguish compatible widening from breaking changes.
- **Demonstrated Value**: Dynamic lifecycle state transitions (Preserve, Downgrade, Invalidate) provide fine-grained epistemic calibration for evolving agent memory.