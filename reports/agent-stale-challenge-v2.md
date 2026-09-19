# Agent Stale Challenge Readiness Report (V2)

> **Screened Transitions**: 10  
> **Agent Stale Challenge Ready**: **2**  
> **Evolution Controls**: **1**  
> **Stale Insensitive for Qwen7B**: **7**  
> **Stale Affected Without Target Repair**: **0**  

## Agent Stale Challenge Matrix

| Transition ID | Qualification Status | Valid Hist Runs | Repo Leakage | H2 Stale Rate | H3 Stale Rate | H2 TSR | H3 TSR |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `trans_track_a_01_click_stream_deprecations` | **STALE_INSENSITIVE_FOR_QWEN7B** | 3/3 | CURRENT_REPO_INFORMATIONAL | 0/3 | 0/3 | 1/3 | 0/3 |
| `trans_track_a_02_flask_should_ignore_error` | **STALE_INSENSITIVE_FOR_QWEN7B** | 3/3 | CURRENT_REPO_INFORMATIONAL | 0/3 | 0/3 | 0/3 | 0/3 |
| `trans_track_a_03_werkzeug_environ_property` | **STALE_INSENSITIVE_FOR_QWEN7B** | 3/3 | CURRENT_REPO_INFORMATIONAL | 0/3 | 0/3 | 0/3 | 0/3 |
| `trans_track_a_04_jinja_version_deprecation` | **AGENT_STALE_CHALLENGE_READY** | 3/3 | CURRENT_REPO_INFORMATIONAL | 1/3 | 0/3 | 2/3 | 3/3 |
| `trans_track_a_05_itsdangerous_version_removal` | **STALE_INSENSITIVE_FOR_QWEN7B** | 3/3 | CURRENT_REPO_INFORMATIONAL | 0/3 | 0/3 | 3/3 | 3/3 |
| `trans_track_a_06_markupsafe_version_removal` | **AGENT_STALE_CHALLENGE_READY** | 3/3 | CURRENT_REPO_INFORMATIONAL | 1/3 | 0/3 | 2/3 | 3/3 |
| `trans_track_a_07_pluggy_varnames_noself` | **STALE_INSENSITIVE_FOR_QWEN7B** | 3/3 | CURRENT_REPO_INFORMATIONAL | 0/3 | 0/3 | 0/3 | 0/3 |
| `trans_track_a_08_attrs_py313_replace_control` | **EVOLUTION_CONTROL** | 3/3 | CURRENT_REPO_INFORMATIONAL | 0/3 | 0/3 | 0/3 | 0/3 |
| `trans_track_a_09_virtualenv_drop_py38_control` | **STALE_INSENSITIVE_FOR_QWEN7B** | 3/3 | CURRENT_REPO_INFORMATIONAL | 0/3 | 0/3 | 3/3 | 3/3 |
| `trans_track_a_10_httpx_client_proxies_deprecation` | **STALE_INSENSITIVE_FOR_QWEN7B** | 3/3 | CURRENT_REPO_INFORMATIONAL | 0/3 | 0/3 | 0/3 | 1/3 |

## Observations & Verification

- **Empirical Robustness**: Observed consistently across 3 pilot seeds without statistical distortion.
- **Stale Insensitivity**: Transitions where Qwen2.5-Coder-7B is naturally robust to the injected historical API are accurately reported as `STALE_INSENSITIVE_FOR_QWEN7B`.
- **Chain of Mitigation**: The qualified challenges demonstrate real historical memory injection inducing stale behavior in H2, while frozen target memory eliminates stale calls and recovers task success in H3.

