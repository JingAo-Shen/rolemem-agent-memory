# Multi-Seed Benchmark Sanity V2 Report

> [!IMPORTANT]
> **Evaluation Protocol**: 3 independent seeds (`42`, `123`, `999`), temperature `0.2`, sampling generation with `Qwen/Qwen2.5-Coder-7B-Instruct`.
> Authentic SHA-256 base/target hashes bound to memory artifacts; strict Bubblewrap sandbox verification.

## 1. Classification Rules (Pilot-v1.2d)
- **`TASK_TOO_HARD`**: `max(TSR_S0, TSR_S2, TSR_S3) == 0` (Task unresolvable by 7B model even with oracle memory).
- **Track B (`TRACK_B_MEMORY_REQUIRED`)**: `TSR_S2 - TSR_S0 >= 0.33` (Oracle memory delivers >= 1 extra seed pass over no memory).
- **`NOT_MEMORY_REQUIRED`**: `TSR_S0 == 1.0` and `TSR_S2 == 1.0` (Model solves task without memory; does not isolate memory capability).
- **Track A (`TRACK_A_STALE_SENSITIVE`)**: `TSR_S0 - TSR_S1 >= 0.33` (Raw stale memory causes >= 1 seed regression compared to clean).
- **Track A (`TRACK_A_API_EVOLUTION`)**: Solvable task (`max > 0`), model reflects new API state without full seed regression.

## 2. Multi-Seed TSR Matrix (4 Tasks x 4 Conditions x 3 Seeds = 48 Runs)

| Task ID | Track | S0 (No Mem) | S1 (Stale Mem) | S2 (Oracle Mem) | S3 (RoleMem Full) | Stale Degradation (S0-S1) | Memory Lift (S2-S0) | Final Classification |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `trans_gold_werkzeug_01_cached_property` | A | 0.33 | 0.00 | 1.00 | 1.00 | +0.33 | +0.67 | **TRACK_A_STALE_SENSITIVE** |
| `trans_gold_flask_02_should_ignore_error` | B | 1.00 | 1.00 | 1.00 | 1.00 | +0.00 | +0.00 | **NOT_MEMORY_REQUIRED** |
| `trans_gold_urllib3_01_retry_allowed_methods` | A | 1.00 | 1.00 | 0.00 | 0.00 | +0.00 | -1.00 | **TRACK_A_API_EVOLUTION** |
| `trans_gold_urllib3_02_empty_allowed_methods` | B | 0.00 | 0.00 | 0.00 | 0.00 | +0.00 | +0.00 | **TASK_TOO_HARD** |

## 3. Detailed Scientific Findings per Task

### `trans_gold_werkzeug_01_cached_property` (A)
- **Repository**: `pallets/werkzeug`
- **Condition Breakdown**:
  - S0 (No Memory): TSR = 0.33 (1/3)
  - S1 (Raw Stale): TSR = 0.0 (0/3)
  - S2 (Oracle Valid): TSR = 1.0 (3/3)
  - S3 (RoleMem Full): TSR = 1.0 (3/3)
- **Classification Rationale**: `TRACK_A_STALE_SENSITIVE`

### `trans_gold_flask_02_should_ignore_error` (B)
- **Repository**: `pallets/flask`
- **Condition Breakdown**:
  - S0 (No Memory): TSR = 1.0 (3/3)
  - S1 (Raw Stale): TSR = 1.0 (3/3)
  - S2 (Oracle Valid): TSR = 1.0 (3/3)
  - S3 (RoleMem Full): TSR = 1.0 (3/3)
- **Classification Rationale**: `NOT_MEMORY_REQUIRED`

### `trans_gold_urllib3_01_retry_allowed_methods` (A)
- **Repository**: `urllib3/urllib3`
- **Condition Breakdown**:
  - S0 (No Memory): TSR = 1.0 (3/3)
  - S1 (Raw Stale): TSR = 1.0 (3/3)
  - S2 (Oracle Valid): TSR = 0.0 (0/3)
  - S3 (RoleMem Full): TSR = 0.0 (0/3)
- **Classification Rationale**: `TRACK_A_API_EVOLUTION`

### `trans_gold_urllib3_02_empty_allowed_methods` (B)
- **Repository**: `urllib3/urllib3`
- **Condition Breakdown**:
  - S0 (No Memory): TSR = 0.0 (0/3)
  - S1 (Raw Stale): TSR = 0.0 (0/3)
  - S2 (Oracle Valid): TSR = 0.0 (0/3)
  - S3 (RoleMem Full): TSR = 0.0 (0/3)
- **Classification Rationale**: `TASK_TOO_HARD`

