# Real LLM Stale-Challenge Screen Report V2 (Qwen2.5-Coder-7B)

**Screened Transitions**: 10
**Qualified Agent Stale Challenges**: 2
**Evolution Controls**: 1
**Stale Insensitive for Qwen7B**: 7
**Stale Affected Without Target Repair**: 0

## 1. Disambiguated Stale Challenge Matrix

| Transition ID | Control Discrimination | Agent Stale Sensitivity | Valid Hist Runs | Repo Leakage | H2 Stale Rate | H3 Stale Rate | S0 TSR | H2 TSR | H3 TSR |
| :--- | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `trans_track_a_01_click_stream_deprecations` | **PASS** | **STALE_INSENSITIVE_FOR_QWEN7B** | 3/3 | CURRENT_REPO_INFORMATIONAL | 0/3 | 0/3 | 1/3 | 1/3 | 0/3 |
| `trans_track_a_02_flask_should_ignore_error` | **PASS** | **STALE_INSENSITIVE_FOR_QWEN7B** | 3/3 | CURRENT_REPO_INFORMATIONAL | 0/3 | 0/3 | 0/3 | 0/3 | 0/3 |
| `trans_track_a_03_werkzeug_environ_property` | **PASS** | **STALE_INSENSITIVE_FOR_QWEN7B** | 3/3 | CURRENT_REPO_INFORMATIONAL | 0/3 | 0/3 | 0/3 | 0/3 | 0/3 |
| `trans_track_a_04_jinja_version_deprecation` | **PASS** | **QUALIFIED_AGENT_STALE_CHALLENGE** | 3/3 | CURRENT_REPO_INFORMATIONAL | 1/3 | 0/3 | 3/3 | 2/3 | 3/3 |
| `trans_track_a_05_itsdangerous_version_removal` | **PASS** | **STALE_INSENSITIVE_FOR_QWEN7B** | 3/3 | CURRENT_REPO_INFORMATIONAL | 0/3 | 0/3 | 0/3 | 3/3 | 3/3 |
| `trans_track_a_06_markupsafe_version_removal` | **PASS** | **QUALIFIED_AGENT_STALE_CHALLENGE** | 3/3 | CURRENT_REPO_INFORMATIONAL | 1/3 | 0/3 | 0/3 | 2/3 | 3/3 |
| `trans_track_a_07_pluggy_varnames_noself` | **PASS** | **STALE_INSENSITIVE_FOR_QWEN7B** | 3/3 | CURRENT_REPO_INFORMATIONAL | 0/3 | 0/3 | 0/3 | 0/3 | 0/3 |
| `trans_track_a_08_attrs_py313_replace_control` | **EVOLUTION_CONTROL** | **EVOLUTION_CONTROL** | 3/3 | CURRENT_REPO_INFORMATIONAL | 0/3 | 0/3 | 0/3 | 0/3 | 0/3 |
| `trans_track_a_09_virtualenv_drop_py38_control` | **PASS** | **STALE_INSENSITIVE_FOR_QWEN7B** | 3/3 | CURRENT_REPO_INFORMATIONAL | 0/3 | 0/3 | 1/3 | 3/3 | 3/3 |
| `trans_track_a_10_httpx_client_proxies_deprecation` | **PASS** | **STALE_INSENSITIVE_FOR_QWEN7B** | 3/3 | CURRENT_REPO_INFORMATIONAL | 0/3 | 0/3 | 0/3 | 0/3 | 1/3 |

## 2. Scientific Interpretation & Rigor

- **Empirical Observation**: Results are observed consistently across 3 pilot seeds (42, 123, 999). Formal significance testing is deferred to expansion scale.
- **Disambiguation**: `CONTROL_STALE_DISCRIMINATION` reflects deterministic ground-truth test suite divergence (stale fails, valid passes); `AGENT_STALE_SENSITIVITY` reflects empirical LLM vulnerability under real historical memory injection.
- **Fair Repository Context**: Every condition (S0, S2, S3) received identical BM25 repository context (<= 1200 tokens) with verified absence of task-trivializing leakage.
- **Zero Fallback**: Zero oracle or spec fallbacks were permitted. All H2 memories were written and entailed by HistoricalMemoryWriterV4.

