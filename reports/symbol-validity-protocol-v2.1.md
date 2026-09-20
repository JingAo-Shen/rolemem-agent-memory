# Memory Validity Protocol V2.1 — Empirical Mechanism Evaluation Report

## 1. Grounded Benchmark Composition (100% Real Git Commits)
- **Total Empirical Cases**: 126
- **Valid Cases (True Negative for Stale)**: 65 (51.6%)
- **Stale Cases (True Positive for Stale)**: 61 (48.4%)

### Empirical Taxonomy Breakdown
- **Category A** (File Modified / Target Symbol Unchanged / Memory Valid): 51 cases
- **Category B** (Target Symbol Modified Internally / Memory Still Semantically Valid): 14 cases
- **Category C** (Target Symbol Unchanged / External Interface Stale): 15 cases
- **Category D** (Target Symbol Modified or Removed / Memory Stale): 46 cases

---

## 2. Mechanism Benchmark Comparison (Unseen General AST Logic)

| Mechanism | Coverage | Overall Acc | Stale Prec | Stale Rec | Stale F1 | FIR (False Inval) | SER (Stale Exposure) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **File_Level_Baseline** | 100.0% | 48.4% | 48.4% | 100.0% | 65.2% | 100.0% | 0.0% |
| **Pure_Symbol_AST_Baseline** | 100.0% | 73.0% | 100.0% | 44.3% | 61.4% | 0.0% | 55.7% |
| **Dependency_Validity_Baseline** | 100.0% | 57.9% | 90.0% | 14.8% | 25.4% | 1.5% | 85.2% |
| **RoleMem_Validity_Engine** | 100.0% | 60.3% | 92.3% | 19.7% | 32.4% | 1.5% | 80.3% |
| **RoleMem_Validity_Engine_Abstain** | 43.7% | 36.5% | 92.3% | 60.0% | 72.7% | 2.9% | 40.0% |

---

## 3. Per-Category Granular Accuracy

| Mechanism | Cat A (File Chg / Sym Same / Valid) | Cat B (Sym Chg / Valid) | Cat C (Sym Same / Stale) | Cat D (Sym Chg / Stale) |
| :--- | :--- | :--- | :--- | :--- |
| **File_Level_Baseline** | 0.0% | 0.0% | 100.0% | 100.0% |
| **Pure_Symbol_AST_Baseline** | 100.0% | 100.0% | 6.7% | 56.5% |
| **Dependency_Validity_Baseline** | 98.0% | 100.0% | 6.7% | 17.4% |
| **RoleMem_Validity_Engine** | 98.0% | 100.0% | 0.0% | 26.1% |
| **RoleMem_Validity_Engine_Abstain** | 56.9% | 35.7% | 0.0% | 26.1% |

---

## 4. Scientific Findings
1. **Zero Heuristics Guarantee**: Evaluator contains 0 hardcoded benchmark keywords or symbol literals.
2. **Strict Phase Separation**: Phase 1 blind prediction outputs to `predictions_<mech>.jsonl` before Phase 2 scoring reads `gold_labels.jsonl`.
3. **De-leaked Case IDs**: All blind input case IDs follow `MV21-XXXXXX` without category or outcome leakage.
