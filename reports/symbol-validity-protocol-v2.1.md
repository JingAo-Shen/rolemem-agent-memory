# Memory Validity Protocol V2.1-R3 — Empirical Mechanism Evaluation Report

## 1. Protocol V2.1 Development Benchmark Composition (100% Real Git Commits)
- **Total Empirical Cases**: 61
- **Valid Cases (True Negative for Stale)**: 44 (72.1%)
- **Stale Cases (True Positive for Stale)**: 17 (27.9%)

### Empirical Taxonomy Breakdown
- **Category A** (File Modified / Target Symbol Unchanged / Memory Valid): 36 cases
- **Category B** (Target Symbol Modified Internally / Valid Contract Assertions): 8 cases
- **Category C** (Target Symbol Unchanged / Verified Dependency Linkage Broken): 1 cases
- **Category D1** (Target Symbol Removed / Memory Stale): 8 cases
- **Category D2** (Target Symbol Modified / Verified Behavioral Break): 8 cases

---

## 2. Mechanism Benchmark Comparison (General AST & Dependency Logic)

| Mechanism | Coverage | Overall Acc | Balanced Acc | Macro F1 | MCC | Selective Risk | Stale Prec | Stale Rec | Stale F1 | FIR (False Inval) | SER (Stale Exposure) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **File_Level_Baseline** | 100.0% | 27.9% | 50.0% | 21.8% | +0.000 | 72.1% | 27.9% | 100.0% | 43.6% | 100.0% | 0.0% |
| **Pure_Symbol_AST_Baseline** | 100.0% | 78.7% | 76.2% | 74.8% | +0.501 | 21.3% | 60.0% | 70.6% | 64.9% | 18.2% | 29.4% |
| **Dependency_Validity_Baseline** | 100.0% | 60.7% | 60.1% | 57.3% | +0.182 | 39.3% | 37.0% | 58.8% | 45.5% | 38.6% | 41.2% |
| **RoleMem_Validity_Engine** | 100.0% | 85.2% | 77.1% | 79.6% | +0.612 | 14.8% | 83.3% | 58.8% | 69.0% | 4.5% | 41.2% |
| **RoleMem_Validity_Engine_Abstain** | 36.1% | 31.1% | 86.4% | 86.3% | +0.730 | 13.6% | 83.3% | 90.9% | 87.0% | 18.2% | 9.1% |

---

## 3. Per-Category Granular Accuracy

| Mechanism | Cat A (File Chg / Sym Same / Valid) | Cat B (Sym Chg / Valid) | Cat C (Sym Same / Stale) | Cat D1 (Sym Rem / Stale) | Cat D2 (Sym Chg / Stale) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **File_Level_Baseline** | 0.0% | 0.0% | 100.0% | 100.0% | 100.0% |
| **Pure_Symbol_AST_Baseline** | 97.2% | 12.5% | 0.0% | 62.5% | 87.5% |
| **Dependency_Validity_Baseline** | 69.4% | 25.0% | 0.0% | 62.5% | 62.5% |
| **RoleMem_Validity_Engine** | 94.4% | 100.0% | 0.0% | 62.5% | 62.5% |
| **RoleMem_Validity_Engine_Abstain** | 25.0% | 0.0% | 0.0% | 62.5% | 62.5% |

---

## 4. Scientific Findings
1. **Zero Heuristics Guarantee**: Evaluator contains 0 hardcoded benchmark keywords or symbol literals.
2. **Strict Phase Separation**: Phase 1 blind prediction outputs to `predictions_<mech>.jsonl` before Phase 2 scoring reads `gold_labels.jsonl`.
3. **De-leaked Case IDs**: All blind input case IDs follow `MV21-XXXXXX` without category or outcome leakage.
4. **Verified Causal & Dependency Linkage**: Cat B cases validated with historical commit executions; Cat C verified with 2-hop AST dependency call graphs; Cat D2 validated with concrete behavioral breaks.
