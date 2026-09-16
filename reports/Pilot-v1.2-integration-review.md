# Pilot-v1.2 Milestone Review: Integration Hardening & GitHub Transition Mining

**Phase**: Pilot-v1.2 Integration Hardening + Real GitHub Transition Mining  
**Date**: September 2026  
**Auditor**: RoleMem Scientific Hardening & Verification Suite  

---

## Executive Audit Questions & Determinations

### Q1: Integration Hardening 是否真正全部通过？
**Determination**: `YES`

**Justification**:
All 6 foundational infrastructure blockers identified in Pilot-v1.1 have been comprehensively addressed, implemented in source code, and validated via unit/integration tests:
1. `SecureSandboxExecutor` is strictly wired into `RealLLMRunnerV1` and `LocalModelRunner`. Raw subprocess execution is eliminated; missing `bwrap` triggers immediate hard fail; network access is unshared; OS-level resource limits (`prlimit`) are active.
2. `ASTStaleActionDetector` is strictly wired into `RealLLMRunnerV1` and `LocalModelRunner`. Regex matching is retired from formal evaluation metrics. AST visitor detects constants, dict indexing/keys, assignments, and comparisons while properly ignoring passive docstrings and comments.
3. Literature Audit v4 (`reports/literature-v4.csv` and `reports/literature-audit-v4.md`) replaces all placeholder arXiv IDs with verified metadata (`arXiv:2507.05257`, `arXiv:2605.20833`, `arXiv:2502.12110`) and marks unverified ToolAtlas fields as `UNVERIFIED`.
4. Pinned local model snapshot is established with exact Hugging Face commit SHAs (`c03e6d35...` for 7B, `ea3f2471...` for 0.5B diagnostic), prohibiting floating `revision="main"`. DeepSeek model endpoint is verified as `deepseek-flash` (`DeepSeek-V4.1-Flash`).
5. Track B is redesigned with 3 counterfactual pairs with 100% identical task instructions to eliminate leakage. Track C is redesigned to remove explicit `"CONFLICT_DETECTED"` hints, measuring autonomous abstention.
6. The end-to-end integration test (`tests/test_end_to_end_hardening.py`) passes cleanly, verifying memory retrieval, prompt construction, AST inspection, sandbox execution, credential protection, and telemetry logging.

---

### Q2: 是否已经达到 READY FOR BENCHMARK FREEZE？
**Determination**: `YES`

**Compliance Checklist (8 Mandatory Criteria)**:

| Criterion | Required Standard | Status | Evidence |
| :--- | :--- | :--- | :--- |
| **1. Secure Sandbox** | Formal evaluators execute strictly within `bwrap` | **PASS** | `src/evaluator_v1.py`, `src/local_model_runner.py`, `tests/test_gate3_sandbox_security.py` |
| **2. AST Stale Detector** | Formal stale metrics computed via AST traversal | **PASS** | `src/stale_detector_ast.py`, `tests/test_stale_detector_ast.py` |
| **3. Literature Audit v4** | Zero placeholder IDs, all metadata verified | **PASS** | `reports/literature-v4.csv`, `reports/literature-audit-v4.md` |
| **4. Local Model Revision** | Exact commit SHAs pinned, no `revision="main"` | **PASS** | `src/local_model_runner.py`, `reports/gate7-model-reproducibility.md` |
| **5. Track B Leakage** | Counterfactual pairs with identical instructions | **PASS** | `src/benchmark_tracks.py`, `tests/test_gate8_tracks.py` |
| **6. Track C Safety** | No explicit conflict / CONFLICT_DETECTED hints | **PASS** | `src/benchmark_tracks.py`, `tests/test_gate8_tracks.py` |
| **7. End-to-End Test** | Full pipeline verified with telemetry & isolation | **PASS** | `tests/test_end_to_end_hardening.py`, `reports/integration-hardening-report.md` |
| **8. Candidate Mining** | 40+ transitions from 10-15 repos with review | **PASS** | `data/candidates/mined_raw.jsonl`, `data/reviewed/reviewed_transitions.jsonl` (44 transitions, 15 repos) |

All 8 conditions are satisfied. While the infrastructure is now **READY FOR BENCHMARK FREEZE**, the freeze itself is deliberately deferred to the next milestone to prevent premature benchmark closure.

---

## Deliverables Summary

1. `reports/Pilot-v1.2-integration-review.md` (This review document)
2. `reports/literature-audit-v4.md` & `reports/literature-v4.csv` (Literature verification)
3. `reports/integration-hardening-report.md` (Blocker resolution report)
4. `data/candidates/mined_raw.jsonl` (44 raw mined candidate transitions)
5. `data/reviewed/reviewed_transitions.jsonl` (44 reviewed candidate transitions)
6. `reports/github-transition-mining-report.md` (Transition mining audit report)
7. `tests/test_end_to_end_hardening.py` (End-to-end integration test suite)
