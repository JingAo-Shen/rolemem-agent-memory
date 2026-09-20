# RoleMem Protocol V2.1 — Benchmark Freeze Readiness & Scientific Audit Report

## Formal Status Declaration
```text
PROTOCOL_VERSION = 2.1
ALGORITHM_FREEZE = NO
BENCHMARK_FREEZE = NO
HUMAN_VALIDATION = PENDING
FORMAL_AGENT_RESULTS = NO
FORMAL_PAPER_RESULTS = NO
```

---

## 1. Protocol V2.1 Core Audit Metrics

### A. Track A Transition Pool & Curation
- **Total Evaluated Transitions**: 30
- **Core Benchmark Transitions**: 13 (100% gate-verified across 8 criteria)
- **Control Benchmark Transitions**: 1
- **Rebuild Candidates**: 8
- **Excluded Transitions**: 8
- **Distinct Repositories (Core)**: 13
- **Distinct Repositories (All)**: 25

### B. 2x2 Causal Counterfactual Sandbox Matrix
- **Machine-Generated Causal Pass Rate**: 19/30 (63.3%)
- **Execution Method**: Real execution inside Bubblewrap containerized sandbox with SHA256 output verification.

### C. Memory Validity Benchmark V2.1
- **Total Empirical Cases**: 126
- **Category Distribution**: Cat A (51), Cat B (14), Cat C (15), Cat D (46)
- **De-leaked Case IDs**: 100% matching `^MV21-\d{6}$` (0% category leakage).
- **Benchmark-Specific Keyword Rules**: **0** (Zero heuristic whitelist).

---

## 2. Outstanding Scientific Risks & Required Next Steps
1. **External Human Annotation**: Multi-annotator blinded validation (`human_annotation_template_annotator_*.csv`) must be completed by independent annotators.
2. **Full Agent Baseline Runs**: Multi-seed agent evaluation across conditions B0-B5, F, A1-A5 with paired bootstrap 95% CIs.
3. **Rebuild Candidates**: 8 transitions currently undergoing fixture enhancement before prospective promotion to Core.
