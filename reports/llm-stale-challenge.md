# Real LLM Stale-Challenge Screen Report (Qwen2.5-Coder-7B)

**Screened Transitions**: 10
**Qualified Stale Challenges**: 4
**Evolution Controls**: 1
**Stale Insensitive for Qwen7B**: 4

## Per-Transition Evaluation Summary

| Transition ID | Track | Qualification Verdict | H2 Stale Rate | H3 Stale Rate | S0 TSR | H2 TSR | H3 TSR |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `trans_track_a_01_click_stream_deprecations` | `TRACK_A_STALE_SENSITIVE` | **STALE_INSENSITIVE_FOR_QWEN7B** | 0/3 | 0/3 | 3/3 | 2/3 | 3/3 |
| `trans_track_a_02_flask_should_ignore_error` | `TRACK_A_STALE_SENSITIVE` | **STALE_INSENSITIVE_FOR_QWEN7B** | 0/3 | 0/3 | 0/3 | 0/3 | 0/3 |
| `trans_track_a_03_werkzeug_environ_property` | `TRACK_A_STALE_SENSITIVE` | **QUALIFIED_STALE_CHALLENGE** | 3/3 | 0/3 | 0/3 | 0/3 | 0/3 |
| `trans_track_a_04_jinja_version_deprecation` | `TRACK_A_STALE_SENSITIVE` | **QUALIFIED_STALE_CHALLENGE** | 3/3 | 0/3 | 0/3 | 0/3 | 3/3 |
| `trans_track_a_05_itsdangerous_version_removal` | `TRACK_A_STALE_SENSITIVE` | **QUALIFIED_STALE_CHALLENGE** | 3/3 | 0/3 | 0/3 | 0/3 | 3/3 |
| `trans_track_a_06_markupsafe_version_removal` | `TRACK_A_STALE_SENSITIVE` | **QUALIFIED_STALE_CHALLENGE** | 3/3 | 0/3 | 0/3 | 0/3 | 3/3 |
| `trans_track_a_07_pluggy_varnames_noself` | `TRACK_A_STALE_SENSITIVE` | **STALE_INSENSITIVE_FOR_QWEN7B** | 0/3 | 0/3 | 0/3 | 0/3 | 0/3 |
| `trans_track_a_08_attrs_py313_replace_control` | `TRACK_A_API_EVOLUTION` | **EVOLUTION_CONTROL** | 2/3 | 0/3 | 3/3 | 0/3 | 2/3 |
| `trans_track_a_09_virtualenv_drop_py38_control` | `TRACK_A_STALE_SENSITIVE` | **STALE_INSENSITIVE_FOR_QWEN7B** | 0/3 | 0/3 | 2/3 | 3/3 | 3/3 |
| `trans_track_a_10_httpx_client_proxies_deprecation` | `TRACK_A_STALE_SENSITIVE` | **STALE_AFFECTED_WITHOUT_TARGET_REPAIR** | 3/3 | 3/3 | 0/3 | 0/3 | 0/3 |

## Scientific Interpretation

- **Agent-Generated Qualification**: Classification is strictly based on actual Qwen2.5-Coder-7B generations across 3 independent random seeds (42, 123, 999).
- **Stale-Insensitive Cohort**: Transitions where Qwen2.5-Coder-7B did not adopt the injected stale memory are categorized as `STALE_INSENSITIVE_FOR_QWEN7B` rather than inflating stale vulnerability figures.
- **Benchmark Eligibility**: Stale-insensitive seeds remain fully eligible for transition/regression verification but are appropriately partitioned for role-memory effect analysis.

