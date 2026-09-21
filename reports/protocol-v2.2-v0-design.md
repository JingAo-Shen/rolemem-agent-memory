# RoleMem Protocol V2.2-Claim-Aware-V0.1 — Architecture Design & Empirical Report

## Formal Status Declaration
```text
PROTOCOL_VERSION = 2.2-claim-aware-v0.1
CURRENT_V0_RESULT_STATUS = DEVELOPMENT_COUPLED_NOT_FOR_SCIENTIFIC_CLAIM
V2_1_DEVELOPMENT_MUTATIONS = 0
V2_2_V0_1_EVALUATION_INTEGRITY = COMPLETE
V2_2_ALGORITHM_FREEZE = NO
V2_2_FORMAL_TEST_OPENED = NO
V2_2_FORMAL_HOLDOUT_DEFINED = NO
FORMAL_AGENT_RESULTS = NO
FORMAL_PAPER_RESULTS = NO
```

---

## 1. Integrity Hardening & Decoupling in V0.1

- **Zero Benchmark Heuristic Whitelists**: All case IDs and keyword-specific hacks eliminated from source code.
- **Unified EvaluationContext**: Whole-file SHA256 parity and identical source snapshots for all baselines and claim engines.
- **Separation of Static vs Execution Assisted**: Honest breakdown between pure static claim reasoning and execution-assisted reasoning.
- **Two-Phase Pipeline**: Complete separation of prediction generation on blind inputs and scoring against gold labels.
- **Holdout Invalidation & Contamination Registry**: Formal holdout candidate split marked INVALIDATED due to prior protocol contamination.

---

## 2. Benchmark Metrics Summary (55 Development Cases)

| Mechanism / Policy | Coverage | Overall Acc | Balanced Acc | Macro F1 | MCC | Selective Risk | FIR | SER |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **file_level** | 100.0% | 20.0% | 50.0% | 16.7% | +0.000 | 80.0% | 100.0% | 0.0% |
| **pure_symbol** | 81.8% | 76.4% | 83.3% | 88.0% | +0.784 | 6.7% | 0.0% | 33.3% |
| **dependency** | 96.4% | 74.5% | 79.0% | 72.1% | +0.491 | 22.6% | 23.8% | 18.2% |
| **rolemem_abstain** | 78.2% | 60.0% | 81.2% | 72.4% | +0.519 | 23.3% | 26.5% | 11.1% |
| **rolemem_forced** | 100.0% | 78.2% | 76.1% | 71.3% | +0.452 | 21.8% | 20.5% | 27.3% |
| **execution_only** | 20.0% | 20.0% | 100.0% | 100.0% | +1.000 | 0.0% | 0.0% | 0.0% |
| **claim_static_selective** | 80.0% | 80.0% | 100.0% | 100.0% | +1.000 | 0.0% | 0.0% | 0.0% |
| **claim_static_valid_default** | 100.0% | 94.5% | 86.4% | 90.5% | +0.825 | 5.5% | 0.0% | 27.3% |
| **claim_static_stale_default** | 100.0% | 85.5% | 90.9% | 81.7% | +0.688 | 14.5% | 18.2% | 0.0% |
| **claim_exec_selective** | 96.4% | 96.4% | 100.0% | 100.0% | +1.000 | 0.0% | 0.0% | 0.0% |
| **claim_exec_valid_default** | 100.0% | 96.4% | 90.9% | 93.9% | +0.885 | 3.6% | 0.0% | 18.2% |
| **claim_exec_stale_default** | 100.0% | 100.0% | 100.0% | 100.0% | +1.000 | 0.0% | 0.0% | 0.0% |

---

## 3. Granular Category Breakdown

| Mechanism / Policy | Cat A (Valid) | Cat B (Valid) | Cat C (Stale) | Cat D1 (Stale) | Cat D2 (Stale) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **file_level** | 0.0% | 0.0% | 100.0% | 100.0% | 100.0% |
| **pure_symbol** | 100.0% | 0.0% | 0.0% | 75.0% | 0.0% |
| **dependency** | 73.5% | 87.5% | 0.0% | 87.5% | 100.0% |
| **rolemem_abstain** | 73.5% | 0.0% | 0.0% | 100.0% | 0.0% |
| **rolemem_forced** | 75.0% | 100.0% | 0.0% | 100.0% | 0.0% |
| **execution_only** | 0.0% | 100.0% | 100.0% | 0.0% | 100.0% |
| **claim_static_selective** | 100.0% | 0.0% | 0.0% | 100.0% | 100.0% |
| **claim_static_valid_default** | 100.0% | 100.0% | 0.0% | 75.0% | 100.0% |
| **claim_static_stale_default** | 100.0% | 0.0% | 100.0% | 100.0% | 100.0% |
| **claim_exec_selective** | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| **claim_exec_valid_default** | 100.0% | 100.0% | 100.0% | 75.0% | 100.0% |
| **claim_exec_stale_default** | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
