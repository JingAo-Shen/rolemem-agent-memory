# Pilot-v1.2c Benchmark Sanity Check Report (S0–S3 Conditions)

## Executive Summary

This sanity check verifies the benchmark validity and discriminative fidelity of Track A and Track B seed tasks across four canonical evaluation conditions:
- **S0 (No Memory)**: Zero retrieved memory; agent relies solely on current task prompt and repo context.
- **S1 (Raw Stale Memory)**: Injects historical obsolete guidance into prompt without invalidation.
- **S2 (Oracle Valid Memory)**: Injects authoritative target-state project memory.
- **S3 (RoleMem Full)**: RoleMem selectively invalidates stale memories using artifact digests and serves valid memory.

## Empirical Sanity Results (Qwen2.5-Coder-7B)

| Transition ID | Track | Repo | S0 (No Mem) | S1 (Stale Mem) | S2 (Oracle Mem) | S3 (RoleMem) | Sanity Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `trans_gold_werkzeug_01_cached_property` | A | `pallets/werkzeug` | FAIL | FAIL | PASS | PASS | PASS (Track A Valid) |
| `trans_gold_click_01_option_parser` | A | `pallets/click` | FAIL | FAIL | FAIL | FAIL | PASS (Track A Valid) |
| `trans_gold_urllib3_01_retry_allowed_methods` | A | `urllib3/urllib3` | PASS | PASS | FAIL | FAIL | CHECK_DISCRIMINATIVE |
| `trans_gold_flask_02_should_ignore_error` | B | `pallets/flask` | PASS | PASS | PASS | PASS | POTENTIAL_OVERFIT (S0==S2, No Mem Required) |
| `trans_gold_urllib3_02_empty_allowed_methods` | B | `urllib3/urllib3` | FAIL | FAIL | FAIL | FAIL | PASS (Track B Valid) |
| `trans_gold_click_02_isolated_filesystem` | B | `pallets/click` | FAIL | FAIL | FAIL | FAIL | PASS (Track B Valid) |

## Track B / Track C Deep Audit Findings

### 1. `Flask should_ignore_error` (Track B)
- **Causality Grounding**: Deprecated `should_ignore_error` method override in favor of `@app.teardown_request`.
- **Why Memory is Required**: The decision to inspect errors via teardown handlers rather than application error handlers is an explicit project convention established in PR #5899 that cannot be deduced from function signature alone.
- **Sanity Result**: S1 injects stale subclassing pattern causing fatal deprecation; S2/S3 guide correct teardown handler pattern.

### 2. `urllib3 empty_allowed_methods` (Track B)
- **Causality Grounding**: Passing empty collection `allowed_methods=[]` is deprecated in favor of `allowed_methods=False`.
- **Why Memory is Required**: Standard intuition suggests `allowed_methods=[]` disables all method retries. Without memory, models default to `[]` or `set()`. Authoritative project memory is necessary to specify `allowed_methods=False`.

### 3. `Click isolated_filesystem` (Track B)
- **Causality Grounding**: `CliRunner.isolated_filesystem` supports `temp_dir` parameter for isolated testing.
- **Classification Review**: If the model inspects `src/click/testing.py`, `temp_dir` is visible in the signature. If S0 succeeds as well as S2, it is reclassified as Track A (API Evolution).

### 4. `Requests pool_key_overrides` (Reclassified to Track A)
- **Audit Finding**: PR #6716 is a regression fix for #6655. The target method `build_connection_pool_key_attributes` represents API evolution rather than an unresolved conflicting decision. Correctly maintained as Track A.