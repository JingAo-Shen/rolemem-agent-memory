# RoleMem Protocol V2.2-V1.1 — Selective Evidence Escalation & Witness Auditing Report

## Formal Status Declaration
```text
PROTOCOL_VERSION = 2.2-selective-evidence-v1.1
CURRENT_V1_RESULT_STATUS = DEVELOPMENT_SELECTIVE_ESCALATION
V2_1_DEVELOPMENT_MUTATIONS = 0
V2_2_V0_DETERMINISTIC_FOUNDATION = FROZEN
V2_2_V1_SELECTIVE_ESCALATION = DEVELOPMENT
V2_2_V1_WITNESS_BINDING = AUDITED
V2_2_V1_EXECUTION_SOURCE_ORIGIN = AUDITED
V2_2_V1_LLM_USED = NO
V2_2_V1_ORACLE_ARTIFACT_USED = NO
V2_2_ALGORITHM_FREEZE = NO
V2_2_FORMAL_HOLDOUT_DEFINED = NO
V2_2_FORMAL_TEST_OPENED = NO
FORMAL_AGENT_RESULTS = NO
FORMAL_PAPER_RESULTS = NO
```

---

## Scientific Errata & V1.0 Result Status Demotion

> [!IMPORTANT]
> **V1.0 Scientific Demotion Note**:
> `V1_0_RESULT_STATUS = PROVISIONAL_EVIDENCE_BINDING_NOT_YET_STRICT`
> - **Reason**: In V1.0, test binding relied on raw keyword frequency (`assertion_count`), leading `CLM-000041` to select `test_divide` instead of genuine witness `test_str`, while reports contained manually drafted case descriptions.
> - **V1.1 Corrective Fix**: AST-based witness graph (`Subject -> Variable -> Operation -> Assertion`), strict dataflow binding, isolated worktree package origin preflight verification (`VERIFIED_TARGET_WORKTREE`), and 100% dynamic Single-Source-of-Truth (SSOT) reporting from execution traces.

---

## Executive Summary & Audited Metrics

- **Verified Witness Rate**: **100.0%** (5 / 5 newly decided claims grounded in audited witnesses).
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
| `CLM-000044` | `MV21-000044` | `CAT_B_SYM_CHG_MEMORY_VALID` | `BEHAVIORAL_CONTRACT` | `VALID` | `UNCERTAIN` | **`UNCERTAIN`** | `UNCERTAIN` | 2 | 1 | `REMAINED_UNCERTAIN_AFTER_ESCALATION` |
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

## 2. Witness Binding & Execution Provenance Audit (11 Escalated Claims)

| Claim ID | Selected Witness Test | Binding Strength | Test Fn SHA256 | Source Origin Status | Decision Evidence Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `CLM-000037` | `tests/test_formatting.py::test_help_formatter_write_text` | `STRONG` | `638b88fa` | `VERIFIED_TARGET_WORKTREE` | `VERIFIED_WITNESS` |
| `CLM-000038` | `tests/middleware/test_proxy_fix.py::test_proxy_fix` | `WEAK` | `96afce56` | `SOURCE_ORIGIN_UNVERIFIED` | `INCONCLUSIVE` |
| `CLM-000039` | `tests/tests_tqdm.py::test_deprecated_gui` | `WEAK` | `55664695` | `SOURCE_ORIGIN_UNVERIFIED` | `INCONCLUSIVE` |
| `CLM-000040` | `tests/test_console.py::test_export_text` | `STRONG` | `017121c2` | `VERIFIED_TARGET_WORKTREE` | `VERIFIED_WITNESS` |
| `CLM-000041` | `tests/test_text.py::test_str` | `STRONG` | `5a0099a1` | `VERIFIED_TARGET_WORKTREE` | `VERIFIED_WITNESS` |
| `CLM-000042` | `-::-` | `-` | `` | `SOURCE_ORIGIN_UNVERIFIED` | `INCONCLUSIVE` |
| `CLM-000043` | `tests/middleware/test_body_limit.py::test_starlette_limit_applies_before_user_middleware` | `WEAK` | `284bf1cb` | `SOURCE_ORIGIN_UNVERIFIED` | `INCONCLUSIVE` |
| `CLM-000044` | `test/test_poolmanager.py::test_poolmanager_blocksize` | `STRONG` | `30568f0c` | `VERIFIED_TARGET_WORKTREE` | `VERIFIED_WITNESS` |
| `CLM-000045` | `testing/test_helpers.py::test_varnames_hookspec_without_self` | `UNBOUND` | `62df7935` | `SOURCE_ORIGIN_UNVERIFIED` | `INCONCLUSIVE` |
| `CLM-000049` | `-::-` | `STRONG` | `` | `VERIFIED_TARGET_WORKTREE` | `VERIFIED_WITNESS` |
| `CLM-000050` | `-::-` | `STRONG` | `` | `VERIFIED_TARGET_WORKTREE` | `VERIFIED_WITNESS` |

---

## 3. Progressive Ablation Comparison (55 Development Cases)

| Ablation Stage | Description | Coverage | Decided Acc | Selective Risk | Balanced Acc | Macro F1 | MCC | FIR | SER |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **S0_Static** | Static Claim-Aware (Zero Escalation) | 80.0% | 100.0% | 0.0% | 100.0% | 100.0% | +1.000 | 0.0% | 0.0% |
| **S1_RepoSearch** | Static + Repository Qualified Search | 83.6% | 100.0% | 0.0% | 100.0% | 100.0% | +1.000 | 0.0% | 0.0% |
| **S2_RepoSearch_Dep** | Static + Repo Search + Dep Inspection | 83.6% | 100.0% | 0.0% | 100.0% | 100.0% | +1.000 | 0.0% | 0.0% |
| **S3_TestDiscovery** | Static + Native Test Discovery (No Exec) | 83.6% | 100.0% | 0.0% | 100.0% | 100.0% | +1.000 | 0.0% | 0.0% |
| **S4_TestDiscovery_Exec** | Static + Native Test Discovery + Targeted Exec | 85.5% | 100.0% | 0.0% | 100.0% | 100.0% | +1.000 | 0.0% | 0.0% |
| **S5_Full_Selective_Escalation** | Full Deterministic Selective Escalation (V1.1) | 89.1% | 100.0% | 0.0% | 100.0% | 100.0% | +1.000 | 0.0% | 0.0% |

---

## 4. Budget Sensitivity Curve Analysis (B10, B25, B50, B100)

| Budget Preset | Files Limit | Tests Limit | Exec Limit | Action Limit | Coverage | Decided Acc | Risk | Total Execs | Total Time (ms) | Mean Time/Esc (ms) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **B10** | 20 | 10 | 1 | 3 | 85.5% | 100.0% | 0.0% | 2 | 716.5 | 65.1 |
| **B25** | 50 | 25 | 2 | 5 | 87.3% | 100.0% | 0.0% | 3 | 1009.4 | 91.8 |
| **B50** | 100 | 50 | 3 | 8 | 89.1% | 100.0% | 0.0% | 4 | 1410.3 | 128.2 |
| **B100** | 300 | 100 | 5 | 15 | 89.1% | 100.0% | 0.0% | 4 | 1366.4 | 124.2 |

---

## 5. Computational Cost Accounting & Resource Distribution

| Metric | Total across Escalation Subset (11 Claims) | Mean per Escalated Claim |
| :--- | :--- | :--- |
| **Repository Files Scanned** | 91 | 8.3 files |
| **Test Candidates Inspected** | 450 | 40.9 tests |
| **Targeted Worktree Executions** | 4 | 0.36 executions |
| **Total Execution Wall Time** | 1368.64 ms | 124.42 ms |
| **Total Acquisition Actions** | 16 | 1.45 actions |

### Action Type Distribution:
```json
{
  "TEST_DISCOVERY": 9,
  "TARGETED_EXECUTION": 4,
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
  - **Selected Witness**: `tests/test_formatting.py::test_help_formatter_write_text` (Strength: `STRONG`)
  - **Provenance**: Origin `VERIFIED_TARGET_WORKTREE`, Decision Status `VERIFIED_WITNESS`
  - **Execution Trace**: Step 1 (TEST_DISCOVERY): Discovered 5 candidates (1 strong) [Top candidate: tests/test_formatting.py:test_help_formatter_...]; Step 2 (TARGETED_EXECUTION): SUPPORTS [Verified witness 'tests/test_formatting.py::test_help_format...]

- **`CLM-000038`** (`MV21-000038`, Category `CAT_B_SYM_CHG_MEMORY_VALID`, ClaimType `BEHAVIORAL_CONTRACT`):
  - **Decision Transition**: `UNCERTAIN` -> **`UNCERTAIN`** (Gold: `VALID`, Stop Reason: `REMAINED_UNCERTAIN_AFTER_ESCALATION`)
  - **Selected Witness**: `tests/middleware/test_proxy_fix.py::test_proxy_fix` (Strength: `WEAK`)
  - **Provenance**: Origin `SOURCE_ORIGIN_UNVERIFIED`, Decision Status `INCONCLUSIVE`
  - **Execution Trace**: Step 1 (TEST_DISCOVERY): Discovered 5 candidates (0 strong) [Top candidate: tests/middleware/test_proxy_fix.py:test_proxy...]

- **`CLM-000039`** (`MV21-000039`, Category `CAT_B_SYM_CHG_MEMORY_VALID`, ClaimType `BEHAVIORAL_CONTRACT`):
  - **Decision Transition**: `UNCERTAIN` -> **`UNCERTAIN`** (Gold: `VALID`, Stop Reason: `REMAINED_UNCERTAIN_AFTER_ESCALATION`)
  - **Selected Witness**: `tests/tests_tqdm.py::test_deprecated_gui` (Strength: `WEAK`)
  - **Provenance**: Origin `SOURCE_ORIGIN_UNVERIFIED`, Decision Status `INCONCLUSIVE`
  - **Execution Trace**: Step 1 (TEST_DISCOVERY): Discovered 45 candidates (0 strong) [Top candidate: tests/tests_tqdm.py:test_deprecated_gui (Gene...]

- **`CLM-000040`** (`MV21-000040`, Category `CAT_B_SYM_CHG_MEMORY_VALID`, ClaimType `BEHAVIORAL_CONTRACT`):
  - **Decision Transition**: `UNCERTAIN` -> **`VALID`** (Gold: `VALID`, Stop Reason: `RESOLVED_TO_VALID`)
  - **Selected Witness**: `tests/test_console.py::test_export_text` (Strength: `STRONG`)
  - **Provenance**: Origin `VERIFIED_TARGET_WORKTREE`, Decision Status `VERIFIED_WITNESS`
  - **Execution Trace**: Step 1 (TEST_DISCOVERY): Discovered 48 candidates (1 strong) [Top candidate: tests/test_console.py:test_export_text (Full ...]; Step 2 (TARGETED_EXECUTION): SUPPORTS [Verified witness 'tests/test_console.py::test_export_text' p...]

- **`CLM-000041`** (`MV21-000041`, Category `CAT_B_SYM_CHG_MEMORY_VALID`, ClaimType `BEHAVIORAL_CONTRACT`):
  - **Decision Transition**: `UNCERTAIN` -> **`VALID`** (Gold: `VALID`, Stop Reason: `RESOLVED_TO_VALID`)
  - **Selected Witness**: `tests/test_text.py::test_str` (Strength: `STRONG`)
  - **Provenance**: Origin `VERIFIED_TARGET_WORKTREE`, Decision Status `VERIFIED_WITNESS`
  - **Execution Trace**: Step 1 (TEST_DISCOVERY): Discovered 46 candidates (9 strong) [Top candidate: tests/test_text.py:test_str (Direct verified ...]; Step 2 (TARGETED_EXECUTION): SUPPORTS [Verified witness 'tests/test_text.py::test_str' passed under...]

- **`CLM-000042`** (`MV21-000042`, Category `CAT_B_SYM_CHG_MEMORY_VALID`, ClaimType `BEHAVIORAL_CONTRACT`):
  - **Decision Transition**: `UNCERTAIN` -> **`UNCERTAIN`** (Gold: `VALID`, Stop Reason: `REMAINED_UNCERTAIN_AFTER_ESCALATION`)
  - **Selected Witness**: `N/A::N/A` (Strength: `N/A`)
  - **Provenance**: Origin `SOURCE_ORIGIN_UNVERIFIED`, Decision Status `INCONCLUSIVE`
  - **Execution Trace**: Step 1 (TEST_DISCOVERY): Discovered 0 candidates (0 strong) [No candidates found...]

- **`CLM-000043`** (`MV21-000043`, Category `CAT_B_SYM_CHG_MEMORY_VALID`, ClaimType `BEHAVIORAL_CONTRACT`):
  - **Decision Transition**: `UNCERTAIN` -> **`UNCERTAIN`** (Gold: `VALID`, Stop Reason: `REMAINED_UNCERTAIN_AFTER_ESCALATION`)
  - **Selected Witness**: `tests/middleware/test_body_limit.py::test_starlette_limit_applies_before_user_middleware` (Strength: `WEAK`)
  - **Provenance**: Origin `SOURCE_ORIGIN_UNVERIFIED`, Decision Status `INCONCLUSIVE`
  - **Execution Trace**: Step 1 (TEST_DISCOVERY): Discovered 34 candidates (0 strong) [Top candidate: tests/middleware/test_body_limit.py:test_star...]

- **`CLM-000044`** (`MV21-000044`, Category `CAT_B_SYM_CHG_MEMORY_VALID`, ClaimType `BEHAVIORAL_CONTRACT`):
  - **Decision Transition**: `UNCERTAIN` -> **`UNCERTAIN`** (Gold: `VALID`, Stop Reason: `REMAINED_UNCERTAIN_AFTER_ESCALATION`)
  - **Selected Witness**: `test/test_poolmanager.py::test_poolmanager_blocksize` (Strength: `STRONG`)
  - **Provenance**: Origin `VERIFIED_TARGET_WORKTREE`, Decision Status `VERIFIED_WITNESS`
  - **Execution Trace**: Step 1 (TEST_DISCOVERY): Discovered 50 candidates (21 strong) [Top candidate: test/test_poolmanager.py:test_poolmanager_blo...]; Step 2 (TARGETED_EXECUTION): INCONCLUSIVE [Execution resulted in UNAVAILABLE (not interpreted as stalen...]

- **`CLM-000045`** (`MV21-000045`, Category `CAT_C_SYM_SAME_MEMORY_STALE`, ClaimType `DEPENDENCY_CONTRACT`):
  - **Decision Transition**: `UNCERTAIN` -> **`UNCERTAIN`** (Gold: `STALE`, Stop Reason: `REMAINED_UNCERTAIN_AFTER_ESCALATION`)
  - **Selected Witness**: `testing/test_helpers.py::test_varnames_hookspec_without_self` (Strength: `UNBOUND`)
  - **Provenance**: Origin `SOURCE_ORIGIN_UNVERIFIED`, Decision Status `INCONCLUSIVE`
  - **Execution Trace**: Step 1 (DEPENDENCY_INSPECTION): SUPPORTS [Static reference to 'varnames' inside 'HookSpec' exists in A...]; Step 2 (TEST_DISCOVERY): Discovered 16 candidates (0 strong) [Top candidate: testing/test_helpers.py:test_varnames_hookspe...]

- **`CLM-000049`** (`MV21-000049`, Category `CAT_D1_SYM_REM_STALE`, ClaimType `SYMBOL_EXISTS`):
  - **Decision Transition**: `UNCERTAIN` -> **`STALE`** (Gold: `STALE`, Stop Reason: `RESOLVED_TO_STALE`)
  - **Selected Witness**: `N/A::N/A` (Strength: `STRONG`)
  - **Provenance**: Origin `VERIFIED_TARGET_WORKTREE`, Decision Status `VERIFIED_WITNESS`
  - **Execution Trace**: Step 1 (REPOSITORY_SEARCH): CONTRADICTS [Qualified symbol 'environ_property.lookup' existed in base c...]

- **`CLM-000050`** (`MV21-000050`, Category `CAT_D1_SYM_REM_STALE`, ClaimType `SYMBOL_EXISTS`):
  - **Decision Transition**: `UNCERTAIN` -> **`STALE`** (Gold: `STALE`, Stop Reason: `RESOLVED_TO_STALE`)
  - **Selected Witness**: `N/A::N/A` (Strength: `STRONG`)
  - **Provenance**: Origin `VERIFIED_TARGET_WORKTREE`, Decision Status `VERIFIED_WITNESS`
  - **Execution Trace**: Step 1 (REPOSITORY_SEARCH): CONTRADICTS [Qualified symbol 'environ_property.read_only' existed in bas...]

