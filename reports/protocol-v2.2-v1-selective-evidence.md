# RoleMem Protocol V2.2-V1.2 — Behavioral Contract Semantics & Evidence Taxonomy Report

## Formal Status Declaration
```text
PROTOCOL_VERSION = 2.2-selective-evidence-v1.2
CURRENT_V1_RESULT_STATUS = DEVELOPMENT_SELECTIVE_ESCALATION
V2_1_DEVELOPMENT_MUTATIONS = 0
V2_2_V0_DETERMINISTIC_FOUNDATION = FROZEN
V2_2_V1_SELECTIVE_ESCALATION = FROZEN
V2_2_V1_WITNESS_BINDING = FROZEN
V2_2_V1_CONTRACT_SEMANTICS = FROZEN
V2_2_V1_EVIDENCE_TAXONOMY = FROZEN
V2_2_V1_EXECUTION_SOURCE_ORIGIN = FROZEN
V2_2_V1_BUDGET_ENFORCEMENT = FROZEN
V2_2_V1_ANTI_COUPLING = FROZEN
V2_2_ALGORITHM_FREEZE = YES
V2_2_FORMAL_HOLDOUT_DEFINED = NO
V2_2_FORMAL_TEST_OPENED = NO
V2_2_V1_LLM_USED = NO
V2_2_V1_ORACLE_ARTIFACT_USED = NO
FORMAL_AGENT_RESULTS = NO
FORMAL_PAPER_RESULTS = NO
```

---

## Scientific Errata & V1.2 Taxonomy Innovations

> [!IMPORTANT]
> **Protocol V2.2-V1.2 Enhancements**:
> 1. **Behavioral Contract Semantic Requirements**: Granular extraction of `OPERATION`, `ATTRIBUTE_STATE`, `CONSTRUCTOR_ARGUMENT`, `DEFAULT_VALUE`, `RETURN_RELATION`, and `SEQUENCE` requirements. Eliminates the flaw where absent operation tokens yielded automatic 100% operation coverage.
> 2. **Evidence Taxonomy Disaggregation**: Disaggregates `VERIFIED_WITNESS` into `VERIFIED_TEST_WITNESS`, `VERIFIED_STRUCTURAL_EVIDENCE`, and `VERIFIED_DEPENDENCY_EVIDENCE`. `SourceOriginStatus` applies strictly to executable tests (`NOT_APPLICABLE` for structural AST searches).
> 3. **Resource Reservation Budget Guard**: Enforces pre-action resource reservations (`reserve_files`, `reserve_tests`, `reserve_executions`) preventing resource overshoot across batch iterations.

---

## Executive Summary & Audited Metrics

- **Verified Evidence Decision Rate**: **100.0%** (5 / 5 newly decided claims supported by verified evidence).
  - **Verified Test-Witness Decisions**: `3` (Rate: `100.0%` among test-escalated decisions)
  - **Verified Structural-Evidence Decisions**: `2`
  - **Verified Dependency-Evidence Decisions**: `0`
- **Escalation Resolution Rate**: **45.5%** (5 / 11 static uncertain claims resolved).
- **Escalation Error Rate**: **0.0%** (0 / 5 incorrectly resolved).
- **Selective Risk**: **0.0%** (maintained across all 49 decided development cases).
- **Coverage Expansion**: **80.0% -> 89.1%** (+9.1% absolute gain on frozen development benchmark).
- **Oracle Artifact Dependency**: **0%** (zero references to historical V2.1 oracle execution artifacts).

---

## 1. Selective Escalation Subset Diagnostic (11 Static Uncertain Claims)

| Claim ID | Case ID | Category | Claim Type | Gold | Static | Escalated | Outcome | Actions | Execs | Stop Reason |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `CLM-000037` | `MV21-000037` | `CAT_B_SYM_CHG_MEMORY_VALID` | `BEHAVIORAL_CONTRACT` | `VALID` | `UNCERTAIN` | **`VALID`** | `CORRECT` | 2 | 1 | `RESOLVED_TO_VALID` |
| `CLM-000038` | `MV21-000038` | `CAT_B_SYM_CHG_MEMORY_VALID` | `BEHAVIORAL_CONTRACT` | `VALID` | `UNCERTAIN` | **`UNCERTAIN`** | `UNCERTAIN` | 1 | 0 | `REMAINED_UNCERTAIN_AFTER_ESCALATION` |
| `CLM-000039` | `MV21-000039` | `CAT_B_SYM_CHG_MEMORY_VALID` | `BEHAVIORAL_CONTRACT` | `VALID` | `UNCERTAIN` | **`UNCERTAIN`** | `UNCERTAIN` | 1 | 0 | `REMAINED_UNCERTAIN_AFTER_ESCALATION` |
| `CLM-000040` | `MV21-000040` | `CAT_B_SYM_CHG_MEMORY_VALID` | `BEHAVIORAL_CONTRACT` | `VALID` | `UNCERTAIN` | **`VALID`** | `CORRECT` | 2 | 1 | `RESOLVED_TO_VALID` |
| `CLM-000041` | `MV21-000041` | `CAT_B_SYM_CHG_MEMORY_VALID` | `BEHAVIORAL_CONTRACT` | `VALID` | `UNCERTAIN` | **`VALID`** | `CORRECT` | 2 | 1 | `RESOLVED_TO_VALID` |
| `CLM-000042` | `MV21-000042` | `CAT_B_SYM_CHG_MEMORY_VALID` | `BEHAVIORAL_CONTRACT` | `VALID` | `UNCERTAIN` | **`UNCERTAIN`** | `UNCERTAIN` | 1 | 0 | `REMAINED_UNCERTAIN_AFTER_ESCALATION` |
| `CLM-000043` | `MV21-000043` | `CAT_B_SYM_CHG_MEMORY_VALID` | `BEHAVIORAL_CONTRACT` | `VALID` | `UNCERTAIN` | **`UNCERTAIN`** | `UNCERTAIN` | 1 | 0 | `REMAINED_UNCERTAIN_AFTER_ESCALATION` |
| `CLM-000044` | `MV21-000044` | `CAT_B_SYM_CHG_MEMORY_VALID` | `BEHAVIORAL_CONTRACT` | `VALID` | `UNCERTAIN` | **`UNCERTAIN`** | `UNCERTAIN` | 1 | 0 | `REMAINED_UNCERTAIN_AFTER_ESCALATION` |
| `CLM-000045` | `MV21-000045` | `CAT_C_SYM_SAME_MEMORY_STALE` | `DEPENDENCY_CONTRACT` | `STALE` | `UNCERTAIN` | **`UNCERTAIN`** | `UNCERTAIN` | 2 | 0 | `REMAINED_UNCERTAIN_AFTER_ESCALATION` |
| `CLM-000049` | `MV21-000049` | `CAT_D1_SYM_REM_STALE` | `SYMBOL_EXISTS` | `STALE` | `UNCERTAIN` | **`STALE`** | `CORRECT` | 1 | 0 | `RESOLVED_TO_STALE` |
| `CLM-000050` | `MV21-000050` | `CAT_D1_SYM_REM_STALE` | `SYMBOL_EXISTS` | `STALE` | `UNCERTAIN` | **`STALE`** | `CORRECT` | 1 | 0 | `RESOLVED_TO_STALE` |

### Key Escalation Breakdown:
- **Static Uncertain Claims**: `11`
- **Newly Resolved Decisions**: `5` (`5/11 = 45.5%`)
  - **Correctly Resolved**: `5` (`100.0%`)
  - **Incorrectly Resolved**: `0` (`0.0%`)
- **Preserved Abstentions (Safe UNCERTAIN)**: `6`
- **Escalation Error Rate**: `0.0%`

---

## 2. Evidence Taxonomy & Semantic Requirements Audit (11 Escalated Claims)

| Claim ID | Evidence Kind | Selected Target | Strength | Requirements Satisfied | Source Origin | Decision Evidence Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `CLM-000037` | `EXECUTABLE_TEST_WITNESS` | `tests/test_formatting.py::test_help_formatter_write_text` | `STRONG` | `3/3` | `VERIFIED_TARGET_WORKTREE` | `VERIFIED_TEST_WITNESS` |
| `CLM-000038` | `-` | `tests/sansio/test_request.py::test_cookies` | `WEAK` | `0/2` | `NOT_APPLICABLE` | `INCONCLUSIVE` |
| `CLM-000039` | `-` | `tests/tests_tqdm.py::test_max_interval` | `WEAK` | `1/3` | `NOT_APPLICABLE` | `INCONCLUSIVE` |
| `CLM-000040` | `EXECUTABLE_TEST_WITNESS` | `tests/test_console.py::test_export_text` | `STRONG` | `4/4` | `VERIFIED_TARGET_WORKTREE` | `VERIFIED_TEST_WITNESS` |
| `CLM-000041` | `EXECUTABLE_TEST_WITNESS` | `tests/test_text.py::test_str` | `STRONG` | `3/3` | `VERIFIED_TARGET_WORKTREE` | `VERIFIED_TEST_WITNESS` |
| `CLM-000042` | `-` | `-` | `-` | `-` | `NOT_APPLICABLE` | `INCONCLUSIVE` |
| `CLM-000043` | `-` | `tests/middleware/test_body_limit.py::test_starlette_limit_applies_before_user_middleware` | `WEAK` | `0/2` | `NOT_APPLICABLE` | `INCONCLUSIVE` |
| `CLM-000044` | `-` | `test/test_poolmanager.py::test_poolmanager_blocksize` | `WEAK` | `1/2` | `NOT_APPLICABLE` | `INCONCLUSIVE` |
| `CLM-000045` | `DEPENDENCY_EVIDENCE` | `testing/test_hookcaller.py::test_hookspec` | `WEAK` | `-` | `NOT_APPLICABLE` | `INCONCLUSIVE` |
| `CLM-000049` | `STRUCTURAL_AST_EVIDENCE` | `-` | `STRONG` | `-` | `NOT_APPLICABLE` | `VERIFIED_STRUCTURAL_EVIDENCE` |
| `CLM-000050` | `STRUCTURAL_AST_EVIDENCE` | `-` | `STRONG` | `-` | `NOT_APPLICABLE` | `VERIFIED_STRUCTURAL_EVIDENCE` |

---

## 3. Component and Cumulative Ablations (55 Development Cases)

| Ablation Stage | Description | Coverage | Decided Acc | Selective Risk | Balanced Acc | Macro F1 | MCC | FIR | SER |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **S0_Static** | Static Claim-Aware (Zero Escalation) | 80.0% | 100.0% | 0.0% | 100.0% | 100.0% | +1.000 | 0.0% | 0.0% |
| **S1_RepoSearch** | Static + Repository Structural Search | 83.6% | 100.0% | 0.0% | 100.0% | 100.0% | +1.000 | 0.0% | 0.0% |
| **S2_RepoSearch_Dep** | Static + Repo Search + Dependency Inspection | 83.6% | 100.0% | 0.0% | 100.0% | 100.0% | +1.000 | 0.0% | 0.0% |
| **S3_TestDiscovery** | Static + Repo Search + Dependency + Test Discovery (No Exec) | 83.6% | 100.0% | 0.0% | 100.0% | 100.0% | +1.000 | 0.0% | 0.0% |
| **D1_TestDiscovery_Exec** | Static + Native Test Discovery + Targeted Exec (Dynamic Channel Diagnostic) | 85.5% | 100.0% | 0.0% | 100.0% | 100.0% | +1.000 | 0.0% | 0.0% |
| **S5_Full_Selective_Escalation** | Full Deterministic Selective Escalation (V1.2) | 89.1% | 100.0% | 0.0% | 100.0% | 100.0% | +1.000 | 0.0% | 0.0% |

---

## 4. Budget Sensitivity Curve Analysis (B10, B25, B50, B100)

| Budget Preset | Files Limit | Tests Limit | Exec Limit | Action Limit | Coverage | Decided Acc | Risk | Total Execs | Total Time (ms) | Mean Time/Esc (ms) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **B10** | 20 | 10 | 1 | 3 | 85.5% | 100.0% | 0.0% | 1 | 468.0 | 42.5 |
| **B25** | 50 | 25 | 2 | 5 | 87.3% | 100.0% | 0.0% | 2 | 756.5 | 68.8 |
| **B50** | 100 | 50 | 3 | 8 | 89.1% | 100.0% | 0.0% | 3 | 1177.0 | 107.0 |
| **B100** | 300 | 100 | 5 | 15 | 89.1% | 100.0% | 0.0% | 3 | 1191.1 | 108.3 |

---

## 5. Computational Cost Accounting & Resource Distribution

| Metric | Total across Escalation Subset (11 Claims) | Mean per Escalated Claim |
| :--- | :--- | :--- |
| **Repository Files Scanned** | 806 | 73.3 files |
| **Test Candidates Inspected** | 450 | 40.9 tests |
| **Targeted Worktree Executions** | 3 | 0.27 executions |
| **Total Execution Wall Time** | 1173.76 ms | 106.71 ms |
| **Total Acquisition Actions** | 15 | 1.36 actions |

### Action Type Distribution:
```json
{
  "TEST_DISCOVERY": 9,
  "TARGETED_EXECUTION": 3,
  "DEPENDENCY_INSPECTION": 1,
  "REPOSITORY_SEARCH": 2
}
```

---

## 6. Per Category & Per Claim Type Breakdown (S5 Full Escalation)

### Per Category Breakdown:
| Category | Total | Decided | Uncertain | Coverage | Decided Accuracy |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `CAT_A_FILE_CHG_SYM_SAME_VALID` | 36 | 36 | 0 | 100.0% | 100.0% |
| `CAT_B_SYM_CHG_MEMORY_VALID` | 8 | 3 | 5 | 37.5% | 100.0% |
| `CAT_C_SYM_SAME_MEMORY_STALE` | 1 | 0 | 1 | 0.0% | N/A |
| `CAT_D1_SYM_REM_STALE` | 8 | 8 | 0 | 100.0% | 100.0% |
| `CAT_D2_SYM_CHG_BEHAVIOR_STALE` | 2 | 2 | 0 | 100.0% | 100.0% |

### Per Claim Type Breakdown:
| Claim Type | Total | Decided | Uncertain | Coverage | Decided Accuracy |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `ATTRIBUTE_EXISTS` | 1 | 1 | 0 | 100.0% | 100.0% |
| `BEHAVIORAL_CONTRACT` | 8 | 3 | 5 | 37.5% | 100.0% |
| `DEPENDENCY_CONTRACT` | 1 | 0 | 1 | 0.0% | N/A |
| `IMPORT_PATH_VALID` | 1 | 1 | 0 | 100.0% | 100.0% |
| `SYMBOL_EXISTS` | 44 | 44 | 0 | 100.0% | 100.0% |

---

## 7. Audited Case Diagnostics & Trace Interpretations (SSOT)

- **`CLM-000037`** (`MV21-000037`, Category `CAT_B_SYM_CHG_MEMORY_VALID`, ClaimType `BEHAVIORAL_CONTRACT`):
  - **Decision Transition**: `UNCERTAIN` -> **`VALID`** (Gold: `VALID`, Stop Reason: `RESOLVED_TO_VALID`)
  - **Evidence Kind**: `EXECUTABLE_TEST_WITNESS` (Decision Status: `VERIFIED_TEST_WITNESS`)
  - **Requirement Coverage**: `3/3 (100.0%)`
  - **Selected Target**: `tests/test_formatting.py::test_help_formatter_write_text` (Strength: `STRONG`)
  - **Provenance**: Snapshot `VERIFIED_TARGET_COMMIT`, Source Origin `VERIFIED_TARGET_WORKTREE`
  - **Execution Trace**: Step 1 (TEST_DISCOVERY): Discovered 5 candidates (1 strong) [Top candidate: tests/test_formatting.py:test_help_formatter_...]; Step 2 (TARGETED_EXECUTION): SUPPORTS [Verified witness 'tests/test_formatting.py::test_help_format...]

- **`CLM-000038`** (`MV21-000038`, Category `CAT_B_SYM_CHG_MEMORY_VALID`, ClaimType `BEHAVIORAL_CONTRACT`):
  - **Decision Transition**: `UNCERTAIN` -> **`UNCERTAIN`** (Gold: `VALID`, Stop Reason: `REMAINED_UNCERTAIN_AFTER_ESCALATION`)
  - **Evidence Kind**: `NONE` (Decision Status: `INCONCLUSIVE`)
  - **Requirement Coverage**: `0/2 (0.0%)`
  - **Selected Target**: `tests/sansio/test_request.py::test_cookies` (Strength: `WEAK`)
  - **Provenance**: Snapshot `VERIFIED_TARGET_COMMIT`, Source Origin `NOT_APPLICABLE`
  - **Execution Trace**: Step 1 (TEST_DISCOVERY): Discovered 5 candidates (0 strong) [Top candidate: tests/sansio/test_request.py:test_cookies (Pa...]

- **`CLM-000039`** (`MV21-000039`, Category `CAT_B_SYM_CHG_MEMORY_VALID`, ClaimType `BEHAVIORAL_CONTRACT`):
  - **Decision Transition**: `UNCERTAIN` -> **`UNCERTAIN`** (Gold: `VALID`, Stop Reason: `REMAINED_UNCERTAIN_AFTER_ESCALATION`)
  - **Evidence Kind**: `NONE` (Decision Status: `INCONCLUSIVE`)
  - **Requirement Coverage**: `1/3 (33.3%)`
  - **Selected Target**: `tests/tests_tqdm.py::test_max_interval` (Strength: `WEAK`)
  - **Provenance**: Snapshot `VERIFIED_TARGET_COMMIT`, Source Origin `NOT_APPLICABLE`
  - **Execution Trace**: Step 1 (TEST_DISCOVERY): Discovered 45 candidates (0 strong) [Top candidate: tests/tests_tqdm.py:test_max_interval (Partia...]

- **`CLM-000040`** (`MV21-000040`, Category `CAT_B_SYM_CHG_MEMORY_VALID`, ClaimType `BEHAVIORAL_CONTRACT`):
  - **Decision Transition**: `UNCERTAIN` -> **`VALID`** (Gold: `VALID`, Stop Reason: `RESOLVED_TO_VALID`)
  - **Evidence Kind**: `EXECUTABLE_TEST_WITNESS` (Decision Status: `VERIFIED_TEST_WITNESS`)
  - **Requirement Coverage**: `4/4 (100.0%)`
  - **Selected Target**: `tests/test_console.py::test_export_text` (Strength: `STRONG`)
  - **Provenance**: Snapshot `VERIFIED_TARGET_COMMIT`, Source Origin `VERIFIED_TARGET_WORKTREE`
  - **Execution Trace**: Step 1 (TEST_DISCOVERY): Discovered 48 candidates (1 strong) [Top candidate: tests/test_console.py:test_export_text (All 4...]; Step 2 (TARGETED_EXECUTION): SUPPORTS [Verified witness 'tests/test_console.py::test_export_text' p...]

- **`CLM-000041`** (`MV21-000041`, Category `CAT_B_SYM_CHG_MEMORY_VALID`, ClaimType `BEHAVIORAL_CONTRACT`):
  - **Decision Transition**: `UNCERTAIN` -> **`VALID`** (Gold: `VALID`, Stop Reason: `RESOLVED_TO_VALID`)
  - **Evidence Kind**: `EXECUTABLE_TEST_WITNESS` (Decision Status: `VERIFIED_TEST_WITNESS`)
  - **Requirement Coverage**: `3/3 (100.0%)`
  - **Selected Target**: `tests/test_text.py::test_str` (Strength: `STRONG`)
  - **Provenance**: Snapshot `VERIFIED_TARGET_COMMIT`, Source Origin `VERIFIED_TARGET_WORKTREE`
  - **Execution Trace**: Step 1 (TEST_DISCOVERY): Discovered 46 candidates (1 strong) [Top candidate: tests/test_text.py:test_str (All 3 semantic r...]; Step 2 (TARGETED_EXECUTION): SUPPORTS [Verified witness 'tests/test_text.py::test_str' passed under...]

- **`CLM-000042`** (`MV21-000042`, Category `CAT_B_SYM_CHG_MEMORY_VALID`, ClaimType `BEHAVIORAL_CONTRACT`):
  - **Decision Transition**: `UNCERTAIN` -> **`UNCERTAIN`** (Gold: `VALID`, Stop Reason: `REMAINED_UNCERTAIN_AFTER_ESCALATION`)
  - **Evidence Kind**: `NONE` (Decision Status: `INCONCLUSIVE`)
  - **Requirement Coverage**: `N/A`
  - **Selected Target**: `N/A::N/A` (Strength: `N/A`)
  - **Provenance**: Snapshot `VERIFIED_TARGET_COMMIT`, Source Origin `NOT_APPLICABLE`
  - **Execution Trace**: Step 1 (TEST_DISCOVERY): Discovered 0 candidates (0 strong) [No candidates found...]

- **`CLM-000043`** (`MV21-000043`, Category `CAT_B_SYM_CHG_MEMORY_VALID`, ClaimType `BEHAVIORAL_CONTRACT`):
  - **Decision Transition**: `UNCERTAIN` -> **`UNCERTAIN`** (Gold: `VALID`, Stop Reason: `REMAINED_UNCERTAIN_AFTER_ESCALATION`)
  - **Evidence Kind**: `NONE` (Decision Status: `INCONCLUSIVE`)
  - **Requirement Coverage**: `0/2 (0.0%)`
  - **Selected Target**: `tests/middleware/test_body_limit.py::test_starlette_limit_applies_before_user_middleware` (Strength: `WEAK`)
  - **Provenance**: Snapshot `VERIFIED_TARGET_COMMIT`, Source Origin `NOT_APPLICABLE`
  - **Execution Trace**: Step 1 (TEST_DISCOVERY): Discovered 34 candidates (0 strong) [Top candidate: tests/middleware/test_body_limit.py:test_star...]

- **`CLM-000044`** (`MV21-000044`, Category `CAT_B_SYM_CHG_MEMORY_VALID`, ClaimType `BEHAVIORAL_CONTRACT`):
  - **Decision Transition**: `UNCERTAIN` -> **`UNCERTAIN`** (Gold: `VALID`, Stop Reason: `REMAINED_UNCERTAIN_AFTER_ESCALATION`)
  - **Evidence Kind**: `NONE` (Decision Status: `INCONCLUSIVE`)
  - **Requirement Coverage**: `1/2 (50.0%)`
  - **Selected Target**: `test/test_poolmanager.py::test_poolmanager_blocksize` (Strength: `WEAK`)
  - **Provenance**: Snapshot `VERIFIED_TARGET_COMMIT`, Source Origin `NOT_APPLICABLE`
  - **Execution Trace**: Step 1 (TEST_DISCOVERY): Discovered 50 candidates (0 strong) [Top candidate: test/test_poolmanager.py:test_poolmanager_blo...]

- **`CLM-000045`** (`MV21-000045`, Category `CAT_C_SYM_SAME_MEMORY_STALE`, ClaimType `DEPENDENCY_CONTRACT`):
  - **Decision Transition**: `UNCERTAIN` -> **`UNCERTAIN`** (Gold: `STALE`, Stop Reason: `REMAINED_UNCERTAIN_AFTER_ESCALATION`)
  - **Evidence Kind**: `DEPENDENCY_EVIDENCE` (Decision Status: `INCONCLUSIVE`)
  - **Requirement Coverage**: `N/A`
  - **Selected Target**: `testing/test_hookcaller.py::test_hookspec` (Strength: `WEAK`)
  - **Provenance**: Snapshot `VERIFIED_TARGET_COMMIT`, Source Origin `NOT_APPLICABLE`
  - **Execution Trace**: Step 1 (DEPENDENCY_INSPECTION): SUPPORTS [Static reference to 'varnames' inside 'HookSpec' exists in A...]; Step 2 (TEST_DISCOVERY): Discovered 16 candidates (0 strong) [Top candidate: testing/test_hookcaller.py:test_hookspec (Dep...]

- **`CLM-000049`** (`MV21-000049`, Category `CAT_D1_SYM_REM_STALE`, ClaimType `SYMBOL_EXISTS`):
  - **Decision Transition**: `UNCERTAIN` -> **`STALE`** (Gold: `STALE`, Stop Reason: `RESOLVED_TO_STALE`)
  - **Evidence Kind**: `STRUCTURAL_AST_EVIDENCE` (Decision Status: `VERIFIED_STRUCTURAL_EVIDENCE`)
  - **Requirement Coverage**: `N/A`
  - **Selected Target**: `N/A::N/A` (Strength: `STRONG`)
  - **Provenance**: Snapshot `VERIFIED_TARGET_COMMIT`, Source Origin `NOT_APPLICABLE`
  - **Execution Trace**: Step 1 (REPOSITORY_SEARCH): CONTRADICTS [Qualified symbol 'environ_property.lookup' existed in base c...]

- **`CLM-000050`** (`MV21-000050`, Category `CAT_D1_SYM_REM_STALE`, ClaimType `SYMBOL_EXISTS`):
  - **Decision Transition**: `UNCERTAIN` -> **`STALE`** (Gold: `STALE`, Stop Reason: `RESOLVED_TO_STALE`)
  - **Evidence Kind**: `STRUCTURAL_AST_EVIDENCE` (Decision Status: `VERIFIED_STRUCTURAL_EVIDENCE`)
  - **Requirement Coverage**: `N/A`
  - **Selected Target**: `N/A::N/A` (Strength: `STRONG`)
  - **Provenance**: Snapshot `VERIFIED_TARGET_COMMIT`, Source Origin `NOT_APPLICABLE`
  - **Execution Trace**: Step 1 (REPOSITORY_SEARCH): CONTRADICTS [Qualified symbol 'environ_property.read_only' existed in bas...]

