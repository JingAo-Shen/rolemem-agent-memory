# Scale Agent Challenge Evaluation Report V2

## Executive Summary

- **Evaluated Candidates**: 6
- **Condition Structure**: S0 (No memory) vs S2 (Agent-A Historical) vs S3 (Verified Target Memory)
- **Constraint Validation**: SolutionConstraintEvaluatorV2 fail-closed integration

## Classification Distribution

- `STALE_INSENSITIVE_FOR_QWEN7B`: 4 / 6 (66.7%)
- `TARGET_MEMORY_STALE_REGRESSION`: 2 / 6 (33.3%)

## Candidate Performance Breakdown

| Transition ID | Category | S0 TSR | S2 Stale Rate | S2 TSR | S3 Stale Rate | S3 TSR |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| `trans_track_a_15_more_itertools_zip_equal_removal` | **`STALE_INSENSITIVE_FOR_QWEN7B`** | 0/3 | 0/3 | 0/3 | 0/3 | 0/3 |
| `trans_track_a_16_rich_file_proxy_isatty` | **`STALE_INSENSITIVE_FOR_QWEN7B`** | 0/3 | 0/3 | 0/3 | 0/3 | 0/3 |
| `trans_track_a_20_iniconfig_strip_inline_comments` | **`TARGET_MEMORY_STALE_REGRESSION`** | 0/3 | 1/3 | 0/3 | 3/3 | 0/3 |
| `trans_track_a_24_cachelib_timeout_timedelta` | **`STALE_INSENSITIVE_FOR_QWEN7B`** | 0/3 | 0/3 | 0/3 | 0/3 | 0/3 |
| `trans_track_a_25_uvicorn_wsgi_middleware_deprecation` | **`TARGET_MEMORY_STALE_REGRESSION`** | 0/3 | 0/3 | 0/3 | 3/3 | 0/3 |
| `trans_track_a_26_rich_render_group_to_group` | **`STALE_INSENSITIVE_FOR_QWEN7B`** | 0/3 | 0/3 | 0/3 | 0/3 | 0/3 |

