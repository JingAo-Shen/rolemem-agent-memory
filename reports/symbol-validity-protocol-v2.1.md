# Memory Validity Protocol V2.1 — Empirical Mechanism Evaluation Report

## 1. Grounded Benchmark Composition (100% Real Git Commits)
- **Total Empirical Cases**: 64
- **Valid Cases (True Negative for Stale)**: 44 (68.8%)
- **Stale Cases (True Positive for Stale)**: 20 (31.2%)

### Empirical Taxonomy Breakdown
- **Category A** (File Modified / Target Symbol Unchanged / Memory Valid): 36 cases
- **Category B** (Target Symbol Modified Internally / Memory Still Semantically Valid): 8 cases
- **Category C** (Target Symbol Unchanged / External Interface Stale): 4 cases
- **Category D** (Target Symbol Modified or Removed / Memory Stale): 16 cases

---

## 2. Mechanism Benchmark Comparison (Unseen General AST Logic)

| Mechanism | Coverage | Overall Acc | Balanced Acc | Macro F1 | MCC | Stale Prec | Stale Rec | Stale F1 | FIR (False Inval) | SER (Stale Exposure) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **File_Level_Baseline** | 100.0% | 26.6% | 42.5% | 21.0% | -0.329 | 27.9% | 85.0% | 42.0% | 100.0% | 15.0% |
| **Pure_Symbol_AST_Baseline** | 100.0% | 79.7% | 68.9% | 71.0% | +0.503 | 88.9% | 40.0% | 55.2% | 2.3% | 60.0% |
| **Dependency_Validity_Baseline** | 100.0% | 57.8% | 55.7% | 54.6% | +0.107 | 37.0% | 50.0% | 42.6% | 38.6% | 50.0% |
| **RoleMem_Validity_Engine** | 100.0% | 75.0% | 64.1% | 65.2% | +0.360 | 70.0% | 35.0% | 46.7% | 6.8% | 65.0% |
| **RoleMem_Validity_Engine_Abstain** | 48.4% | 37.5% | 74.3% | 74.8% | +0.498 | 70.0% | 63.6% | 66.7% | 15.0% | 36.4% |

---

## 3. Per-Category Granular Accuracy

| Mechanism | Cat A (File Chg / Sym Same / Valid) | Cat B (Sym Chg / Valid) | Cat C (Sym Same / Stale) | Cat D (Sym Chg / Stale) |
| :--- | :--- | :--- | :--- | :--- |
| **File_Level_Baseline** | 0.0% | 0.0% | 25.0% | 100.0% |
| **Pure_Symbol_AST_Baseline** | 100.0% | 87.5% | 0.0% | 50.0% |
| **Dependency_Validity_Baseline** | 69.4% | 25.0% | 50.0% | 50.0% |
| **RoleMem_Validity_Engine** | 94.4% | 87.5% | 50.0% | 31.2% |
| **RoleMem_Validity_Engine_Abstain** | 47.2% | 0.0% | 50.0% | 31.2% |

---

## 4. Scientific Findings
1. **Zero Heuristics Guarantee**: Evaluator contains 0 hardcoded benchmark keywords or symbol literals.
2. **Strict Phase Separation**: Phase 1 blind prediction outputs to `predictions_<mech>.jsonl` before Phase 2 scoring reads `gold_labels.jsonl`.
3. **De-leaked Case IDs**: All blind input case IDs follow `MV21-XXXXXX` without category or outcome leakage.
4. **Balanced Robustness Split**: Primary split contains 64 cases (Cat A: 36, Cat B: 8, Cat C: 4, Cat D: 16) mined from 22 distinct repositories.
