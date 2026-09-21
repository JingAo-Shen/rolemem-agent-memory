# Memory Validity Protocol V2.1-R3.1 — Empirical Mechanism Evaluation Report

## 1. Protocol V2.1 Development Benchmark Composition (100% Real Git Commits)
- **Total Empirical Cases**: 55
- **Valid Cases (True Negative for Stale)**: 44 (80.0%)
- **Stale Cases (True Positive for Stale)**: 11 (20.0%)

### Empirical Taxonomy Breakdown
- **Category A** (File Modified / Target Symbol Unchanged / Memory Valid): 36 cases
- **Category B** (Target Symbol Modified Internally / Valid Contract Assertions): 8 cases
- **Category C** (Target Symbol Unchanged / Verified Dependency Linkage Broken): 1 cases
- **Category D1** (Target Symbol Removed / Memory Stale): 8 cases
- **Category D2** (Target Symbol Modified / Verified Behavioral Break): 2 cases

> [!NOTE]
> **Diagnostic Category C Scope**: Category C contains 1 verified diagnostic case (`pluggy.HookSpec`). It serves as an exploratory/diagnostic sanity check for cross-file dependency propagation, and is not used to make standalone statistical category-level superiority claims.

---

## 2. Mechanism Benchmark Comparison (General AST & Dependency Logic)

| Mechanism | Coverage | Overall Acc | Balanced Acc | Macro F1 | MCC | Selective Risk | Stale Prec | Stale Rec | Stale F1 | FIR (False Inval) | SER (Stale Exposure) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **File_Level_Baseline** | 100.0% | 20.0% | 50.0% | 16.7% | +0.000 | 80.0% | 20.0% | 100.0% | 33.3% | 100.0% | 0.0% |
| **Pure_Symbol_AST_Baseline** | 100.0% | 78.2% | 72.7% | 69.8% | +0.408 | 21.8% | 46.7% | 63.6% | 53.8% | 18.2% | 36.4% |
| **Dependency_Validity_Baseline** | 100.0% | 61.8% | 62.5% | 56.0% | +0.202 | 38.2% | 29.2% | 63.6% | 40.0% | 38.6% | 36.4% |
| **RoleMem_Validity_Engine** | 100.0% | 85.5% | 70.5% | 73.4% | +0.491 | 14.5% | 71.4% | 45.5% | 55.6% | 4.5% | 54.5% |
| **RoleMem_Validity_Engine_Abstain** | 30.9% | 25.5% | 82.6% | 81.3% | +0.633 | 17.6% | 71.4% | 83.3% | 76.9% | 18.2% | 16.7% |

### Selective Performance (Decided Subset)

- **File_Level_Baseline**: Selective Balanced Accuracy = 50.0% at Coverage = 100.0% (Selective Risk = 80.0%)
- **Pure_Symbol_AST_Baseline**: Selective Balanced Accuracy = 72.7% at Coverage = 100.0% (Selective Risk = 21.8%)
- **Dependency_Validity_Baseline**: Selective Balanced Accuracy = 62.5% at Coverage = 100.0% (Selective Risk = 38.2%)
- **RoleMem_Validity_Engine**: Selective Balanced Accuracy = 70.5% at Coverage = 100.0% (Selective Risk = 14.5%)
- **RoleMem_Validity_Engine_Abstain**: Selective Balanced Accuracy = 82.6% at Coverage = 30.9% (Selective Risk = 17.6%)

---

## 3. Per-Category Granular Accuracy

| Mechanism | Cat A (File Chg / Sym Same / Valid) | Cat B (Sym Chg / Valid) | Cat C (Sym Same / Stale) | Cat D1 (Sym Rem / Stale) | Cat D2 (Sym Chg / Stale) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **File_Level_Baseline** | 0.0% | 0.0% | 100.0% | 100.0% | 100.0% |
| **Pure_Symbol_AST_Baseline** | 97.2% | 12.5% | 0.0% | 62.5% | 100.0% |
| **Dependency_Validity_Baseline** | 69.4% | 25.0% | 0.0% | 62.5% | 100.0% |
| **RoleMem_Validity_Engine** | 94.4% | 100.0% | 0.0% | 62.5% | 0.0% |
| **RoleMem_Validity_Engine_Abstain** | 25.0% | 0.0% | 0.0% | 62.5% | 0.0% |

---

## 4. Scientific Findings
1. **Zero Heuristics Guarantee**: Evaluator contains 0 hardcoded benchmark keywords or symbol literals.
2. **Strict Phase Separation**: Phase 1 blind prediction outputs to `predictions_<mech>.jsonl` before Phase 2 scoring reads `gold_labels.jsonl`.
3. **De-leaked Case IDs**: All blind input case IDs follow `MV21-XXXXXX` without category or outcome leakage.
4. **Verified Causal & Dependency Linkage**: Cat B cases validated with historical commit executions; Cat C verified with 2-hop AST dependency call graphs; Cat D2 validated with concrete behavioral breaks.
