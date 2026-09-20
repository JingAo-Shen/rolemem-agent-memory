# Scale Agent Stale Challenge Evaluation Report

## 1. Executive Summary

- **Candidate Transitions Audited**: 6 (3 seeds = 18 runs)
- **Agent Stale Challenge Ready (Scale)**: **0**
- **All memory sources strictly agent-generated**: `AGENT_A_HISTORICAL` and `TARGET_MEMORY_VERIFIED`

---

## 2. Scale Challenge Qualification Matrix

| Transition ID | Qualification Status | Valid Hist Runs | H2 Stale Rate | H3 Stale Rate | H0 TSR | H2 TSR | H3 TSR |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `trans_track_a_15_more_itertools_zip_equal_removal` | **STALE_INSENSITIVE_FOR_QWEN7B** | 3/3 | 0/3 | 0/3 | 0/3 | 0/3 | 0/3 |
| `trans_track_a_16_rich_file_proxy_isatty` | **STALE_INSENSITIVE_FOR_QWEN7B** | 3/3 | 0/3 | 0/3 | 0/3 | 0/3 | 3/3 |
| `trans_track_a_20_iniconfig_strip_inline_comments` | **STALE_AFFECTED_WITHOUT_TARGET_REPAIR** | 3/3 | 1/3 | 3/3 | 0/3 | 0/3 | 0/3 |
| `trans_track_a_24_cachelib_timeout_timedelta` | **STALE_INSENSITIVE_FOR_QWEN7B** | 3/3 | 0/3 | 0/3 | 2/3 | 2/3 | 3/3 |
| `trans_track_a_25_uvicorn_wsgi_middleware_deprecation` | **HISTORICAL_MEMORY_UNSTABLE** | 1/3 | 0/1 | 3/3 | 0/3 | 0/1 | 0/3 |
| `trans_track_a_26_rich_render_group_to_group` | **STALE_INSENSITIVE_FOR_QWEN7B** | 3/3 | 0/3 | 0/3 | 0/3 | 2/3 | 3/3 |
