# Gate 1 Report: Unified Memory Token Budget

**Gate Status**: `PASSED`  
**Date**: September 2026  
**Auditor**: RoleMem Hardening Suite

---

## 1. Objectives & Policy
To eliminate unfair information advantages caused by asymmetric memory length (e.g., retrieving unbounded history vs arbitrary top-k limits), Gate 1 introduces a centralized `MemoryBudgeter`:
- **Default Budget**: `max_memory_tokens = 512`
- **Tokenizer**: `tiktoken` (`cl100k_base`) with character-ratio fallback.
- **Budget Sensitivity Levels**: `[128, 256, 512, 1024, 2048]`.
- **Constraint**: Every non-B0 baseline must strictly guarantee:
  $$\text{memory\_tokens} \le \text{max\_memory\_tokens}$$
- **B0 Policy**: Zero historical memory tokens, but current task and current repository remain 100% complete and uncurtailed.
- **B2 Designation**: Formally designated as `B2_chronological_history` (rather than rolling summary) to accurately describe its factual operation without claiming external summarization.

---

## 2. Modified & Created Files
- `src/budgeter.py`: Implemented `MemoryBudgeter` with `count_tokens` and `format_and_budget`.
- `src/baselines_v1.py`: Integrated `MemoryBudgeter` into all baseline routines (`run_B1_recent_raw_history`, `run_B2_chronological_history`, `run_B3_bm25_unscoped`, `run_B4_bm25_temporal`, `run_B5_memstrata_temporal_supersession`, `run_F_rolemem_full`).
- `tests/test_gate1_budget.py`: Comprehensive test suite verifying budget compliance across all methods for budgets `[128, 256, 512, 1024]`.

---

## 3. Verification Evidence
```bash
pytest -v tests/test_gate1_budget.py
```
Output:
```text
tests/test_gate1_budget.py::test_all_baselines_comply_with_token_budget[128] PASSED [ 20%]
tests/test_gate1_budget.py::test_all_baselines_comply_with_token_budget[256] PASSED [ 40%]
tests/test_gate1_budget.py::test_all_baselines_comply_with_token_budget[512] PASSED [ 60%]
tests/test_gate1_budget.py::test_all_baselines_comply_with_token_budget[1024] PASSED [ 80%]
tests/test_gate1_budget.py::test_b0_returns_zero_tokens PASSED           [100%]
============================== 5 passed in 2.51s ===============================
```
All baselines strictly enforce the token budget without memory leakage or overflow.
