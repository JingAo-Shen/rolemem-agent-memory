# RoleMem Benchmark v1.0 Candidate Readiness Report

**Audit Date**: September 20, 2026  
**Curation Scope**: `TRACK_A_CURATION_POOL_V1` (30 provisional transitions across 25 repositories)  
**Readiness Status**: **BENCHMARK_FREEZE_REVIEW = NO | BENCHMARK_FREEZE = NO | FORMAL_RESULTS = NO**

---

## 1. Candidate Manifest Summary

Deterministic exports generated at `data/benchmark_v1/`:

| Manifest | Transitions | Role / Purpose | File Path |
| :--- | :---: | :--- | :--- |
| **`track_a_core.jsonl`** | **11** | High-integrity, verified stale-sensitive benchmark transitions | `data/benchmark_v1/track_a_core.jsonl` |
| **`track_a_controls.jsonl`** | **4** | Authentic non-stale-sensitive / evolution controls | `data/benchmark_v1/track_a_controls.jsonl` |
| **`excluded.jsonl`** | **8** | Archived due to triviality / lack of deterministic causality | `data/benchmark_v1/excluded.jsonl` |
| **`rebuild_candidates`** | **7** | Priority candidates retained for task/claim re-grounding | `data/curation/reviews/` |

---

## 2. Core Benchmark Integrity Checklist (12-Gate Audit)

All 11 Core Benchmark transitions satisfy:
1. `[PASS]` Real GitHub transition verified with commit ancestry.
2. `[PASS]` Base / target snapshot integrity verified.
3. `[PASS]` Hidden test executable inside secure sandbox.
4. `[PASS]` Mutation strength kill rate $\ge 80\%$ with zero constant-return bypass.
5. `[PASS]` Deterministic stale and valid control fixtures.
6. `[PASS]` 2x2 counterfactual causal matrix verified.
7. `[PASS]` Dual-source external ground truth verified.
8. `[PASS]` Task Mapping classified as `TASK_MAPPING_STRONG`.
9. `[PASS]` Semantic verdict = `SEMANTIC_STRONG_PASS` or reviewed `SEMANTIC_WEAK_PASS`.
10. `[PASS]` Base memory claim entailed by base commit code excerpt.
11. `[PASS]` Valid memory claim entailed by target commit diff excerpt.
12. `[PASS]` Verified absence of critical repository-context trivialization.

---

## 3. Freeze Gate Review Verdict

- **Requirement for Freeze Review**: $\ge 15$ Core transitions, $\ge 3$ Controls, $\ge 12$ distinct repositories.
- **Current Core Transitions**: **11** Core (short of 15 threshold).
- **Readiness Conclusion**: Benchmark Freeze Review remains **BLOCKED** until 4 to 6 of the 7 high-value `REBUILD_CANDIDATES` are re-grounded and elevated to Core.
