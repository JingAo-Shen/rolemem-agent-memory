# RoleMem Protocol V2.2-Claim-Aware-V0.2 — Architecture Design & Empirical Report

## Formal Status Declaration
```text
PROTOCOL_VERSION = 2.2-claim-aware-v0.2
CURRENT_V0_RESULT_STATUS = DEVELOPMENT_COUPLED_NOT_FOR_SCIENTIFIC_CLAIM
V2_1_DEVELOPMENT_MUTATIONS = 0
V2_2_DETERMINISTIC_FOUNDATION = CLOSED
V2_2_STRUCTURED_CLAIM_REPRESENTATION = CORRECTED_FROZEN_REVISION
V2_2_PREVIOUS_REPRESENTATION = SUPERSEDED_DUE_TO_EXTRACTION_REGRESSION
V2_2_EXTRACTION_SELF_CONSISTENCY_EVALUATED = YES
V2_2_INDEPENDENT_EXTRACTION_GOLD = NO
V2_2_EVIDENCE_BINDING = PARTIAL
V2_2_ALGORITHM_FREEZE = NO
V2_2_FORMAL_HOLDOUT_DEFINED = NO
V2_2_FORMAL_TEST_OPENED = NO
FORMAL_AGENT_RESULTS = NO
FORMAL_PAPER_RESULTS = NO
```

---

## Evidence Binding Audit Breakdown
- **Overall Binding Status**: `PARTIAL`
- **Cat B Bindings**: VERIFIED=8, UNKNOWN=0, FAILED=0
- **Cat C Bindings**: VERIFIED=1, UNKNOWN=0, FAILED=0
- **Cat D2 Bindings**: VERIFIED=0, UNKNOWN=2, FAILED=0

---

## 1. Primary Structured-Claim Validity Benchmark (Selective Evaluation)

> [!NOTE]
> This table evaluates intrinsic validity reasoning on the frozen development structured claims under `SelectivePolicy` (abstaining on uncertain cases).

| Primary Mechanism | Coverage | Selective Risk | Decided Acc | Balanced Acc | Macro F1 | MCC | FIR (Decided Valid) | SER (Decided Stale) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **File_Level_Baseline** | 100.0% | 80.0% | 20.0% | 50.0% | 16.7% | +0.000 | 100.0% | 0.0% |
| **Pure_Symbol_AST_Baseline** | 81.8% | 6.7% | 93.3% | 83.3% | 88.0% | +0.784 | 0.0% | 33.3% |
| **Dependency_Validity_Baseline** | 96.4% | 22.6% | 77.4% | 79.0% | 72.1% | +0.491 | 23.8% | 18.2% |
| **RoleMem_Structural_V2_1 (Abstain)** | 78.2% | 23.3% | 76.7% | 81.2% | 72.4% | +0.519 | 26.5% | 11.1% |
| **Oracle_Execution_UpperBound** | 20.0% | 0.0% | 100.0% | 100.0% | 100.0% | +1.000 | 0.0% | 0.0% |
| **Claim_Aware_Static (Selective)** | 80.0% | 0.0% | 100.0% | 100.0% | 100.0% | +1.000 | 0.0% | 0.0% |
| **Claim_Aware_Exec_Assisted (Selective)** | 96.4% | 0.0% | 100.0% | 100.0% | 100.0% | +1.000 | 0.0% | 0.0% |

---

## 2. Decision Policy Sensitivity Analysis

| Claim Engine Variant | Policy | Coverage | Overall Acc | Balanced Acc | Macro F1 | MCC | FIR | SER |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Claim_Aware_Static** | Selective | 80.0% | 80.0% | 100.0% | 100.0% | +1.000 | 0.0% | 0.0% |
| **Claim_Aware_Static** | Forced Valid Default | 100.0% | 94.5% | 86.4% | 90.5% | +0.825 | 0.0% | 27.3% |
| **Claim_Aware_Static** | Forced Stale Default | 100.0% | 85.5% | 90.9% | 81.7% | +0.688 | 18.2% | 0.0% |
| **Claim_Aware_Exec_Assisted** | Selective | 96.4% | 96.4% | 100.0% | 100.0% | +1.000 | 0.0% | 0.0% |
| **Claim_Aware_Exec_Assisted** | Forced Valid Default | 100.0% | 96.4% | 90.9% | 93.9% | +0.885 | 0.0% | 18.2% |
| **Claim_Aware_Exec_Assisted** | Forced Stale Default | 100.0% | 100.0% | 100.0% | 100.0% | +1.000 | 0.0% | 0.0% |

---

## 3. Granular Category Coverage & Accuracy Breakdown

| Mechanism | Cat A Cov (Acc) | Cat B Cov (Acc) | Cat C Cov (Acc) | Cat D1 Cov (Acc) | Cat D2 Cov (Acc) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **file_level** | 100% (0%) | 100% (0%) | 100% (100%) | 100% (100%) | 100% (100%) |
| **pure_symbol** | 100% (100%) | 0% (N/A) | 100% (0%) | 100% (75%) | 0% (N/A) |
| **dependency** | 94% (74%) | 100% (88%) | 100% (0%) | 100% (88%) | 100% (100%) |
| **rolemem_abstain** | 94% (74%) | 0% (N/A) | 100% (0%) | 100% (100%) | 0% (N/A) |
| **rolemem_forced** | 100% (75%) | 100% (100%) | 100% (0%) | 100% (100%) | 100% (0%) |
| **oracle_execution_upper_bound** | 0% (N/A) | 100% (100%) | 100% (100%) | 0% (N/A) | 100% (100%) |
| **claim_static_selective** | 100% (100%) | 0% (N/A) | 0% (N/A) | 75% (100%) | 100% (100%) |
| **claim_static_valid_default** | 100% (100%) | 100% (100%) | 100% (0%) | 100% (75%) | 100% (100%) |
| **claim_static_stale_default** | 100% (100%) | 100% (0%) | 100% (100%) | 100% (100%) | 100% (100%) |
| **claim_exec_selective** | 100% (100%) | 100% (100%) | 100% (100%) | 75% (100%) | 100% (100%) |
| **claim_exec_valid_default** | 100% (100%) | 100% (100%) | 100% (100%) | 100% (75%) | 100% (100%) |
| **claim_exec_stale_default** | 100% (100%) | 100% (100%) | 100% (100%) | 100% (100%) | 100% (100%) |

---

## 4. Honest Results Interpretation & Scope Boundaries

1. **Development-Coupled Context**: All metrics in this report belong strictly to the `Protocol V2.2 Development Structured-Claim Benchmark` (55 cases).
2. **Extraction Evaluation Scope**: Structured claim representation was generated within the same extractor development cycle and does not constitute independent extraction ground truth (`independent_gold = false`).
3. **Paraphrase Evaluation Scope**: `paraphrase_dev.jsonl` is marked as `DEVELOPER_SEEN_PARAPHRASE_DEV` because paraphrases were authored during parser refinement. `BEHAVIORAL_CONTRACT` object exact match is 0%, documented as a known V1 development limitation.
4. **Policy-Driven Numbers**: `Claim_Static_Valid_Default` achieves 100% on Cat B not through intrinsic static proof, but through the `UNCERTAIN -> VALID` optimistic retrieval policy.
5. **Oracle Upper Bound**: `Oracle_Execution_Evidence_UpperBound` is documented strictly as an oracle ceiling measurement and is not a standalone deployable engine.
6. **Evidence Binding Integrity**: D2 and unproven contract assertions produce `UNKNOWN` binding status without artificial fallback.
7. **Cat C Invalidation & Recomputation**: Previous Cat C static metrics derived from truncated `subject="c"` in CLM-000045 have been invalidated. Under corrected revision `v2r1`, CLM-000045 returns `UNCERTAIN` for static reasoning and abstains (static selective coverage = 80.0%, 44/55, decided accuracy = 100.0%), while execution-assisted reasoning binds the counterfactual execution failure and correctly predicts `STALE`.

