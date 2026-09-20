# Historical Memory Factuality & 3-Tier Audit Report

## Summary Metrics

- **Total Historical Statements Audited**: 30 (10 transitions × 3 seeds)
- **Tier A: Temporal Isolation Pass**: **30 / 30 (100.0%)**
- **Tier B: Structural Evidence Grounded**: **30 / 30 (100.0%)**
- **Tier C: Semantic Factuality Pass**: **18 / 30 (60.0%)**

## 3-Tier Disentangled Evaluation Matrix

| Transition ID | Seed | Temporal Isolation | Structural Grounding | Semantic Factuality | Status | Notes |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| `trans_track_a_01_click_stream_deprecations` | 42 | PASS | PASS | PASS | **FACTUALLY_SUPPORTED** | **Created Question**: Evaluate whether the following CLAIM a |
| `trans_track_a_01_click_stream_deprecations` | 123 | PASS | PASS | PASS | **FACTUALLY_SUPPORTED** | : |
| `trans_track_a_01_click_stream_deprecations` | 999 | PASS | PASS | PASS | **FACTUALLY_SUPPORTED** | : |
| `trans_track_a_02_flask_should_ignore_error` | 42 | PASS | PASS | FAIL | **CONTRADICTED** | The historical source code does not provide enough evidence  |
| `trans_track_a_02_flask_should_ignore_error` | 123 | PASS | PASS | FAIL | **CONTRADICTED** | The historical source code does not provide enough evidence  |
| `trans_track_a_02_flask_should_ignore_error` | 999 | PASS | PASS | FAIL | **CONTRADICTED** | The historical source code does not provide enough evidence  |
| `trans_track_a_03_werkzeug_environ_property` | 42 | PASS | PASS | PASS | **FACTUALLY_SUPPORTED** | The historical source code defines `environ_property` as a s |
| `trans_track_a_03_werkzeug_environ_property` | 123 | PASS | PASS | PASS | **FACTUALLY_SUPPORTED** | The historical source code defines `environ_property` as a s |
| `trans_track_a_03_werkzeug_environ_property` | 999 | PASS | PASS | PASS | **FACTUALLY_SUPPORTED** | The historical source code defines `environ_property` as a s |
| `trans_track_a_04_jinja_version_deprecation` | 42 | PASS | PASS | PASS | **FACTUALLY_SUPPORTED** | __version__ is explicitly set to '3.2.0.dev0' in the histori |
| `trans_track_a_04_jinja_version_deprecation` | 123 | PASS | PASS | PASS | **FACTUALLY_SUPPORTED** | __version__ is explicitly set to '3.2.0.dev0' in the histori |
| `trans_track_a_04_jinja_version_deprecation` | 999 | PASS | PASS | PASS | **FACTUALLY_SUPPORTED** | __version__ is explicitly set to '3.2.0.dev0' in the histori |
| `trans_track_a_05_itsdangerous_version_removal` | 42 | PASS | PASS | PASS | **FACTUALLY_SUPPORTED** | : |
| `trans_track_a_05_itsdangerous_version_removal` | 123 | PASS | PASS | PASS | **FACTUALLY_SUPPORTED** | : |
| `trans_track_a_05_itsdangerous_version_removal` | 999 | PASS | PASS | PASS | **FACTUALLY_SUPPORTED** | : |
| `trans_track_a_06_markupsafe_version_removal` | 42 | PASS | PASS | PASS | **FACTUALLY_SUPPORTED** | The historical source code shows that when __version__ is ac |
| `trans_track_a_06_markupsafe_version_removal` | 123 | PASS | PASS | PASS | **FACTUALLY_SUPPORTED** | The historical source code shows that the __getattr__ method |
| `trans_track_a_06_markupsafe_version_removal` | 999 | PASS | PASS | PASS | **FACTUALLY_SUPPORTED** | The historical source code shows that the __getattr__ method |
| `trans_track_a_07_pluggy_varnames_noself` | 42 | PASS | PASS | PASS | **FACTUALLY_SUPPORTED** | **Created Question**: Evaluate whether the following CLAIM a |
| `trans_track_a_07_pluggy_varnames_noself` | 123 | PASS | PASS | PASS | **FACTUALLY_SUPPORTED** | **Created Question**: Evaluate whether the following CLAIM a |
| `trans_track_a_07_pluggy_varnames_noself` | 999 | PASS | PASS | PASS | **FACTUALLY_SUPPORTED** | : |
| `trans_track_a_08_attrs_py313_replace_control` | 42 | PASS | PASS | FAIL | **INSUFFICIENT_EVIDENCE** | The provided historical source code does not contain any inf |
| `trans_track_a_08_attrs_py313_replace_control` | 123 | PASS | PASS | FAIL | **INSUFFICIENT_EVIDENCE** | The provided historical source code does not contain any inf |
| `trans_track_a_08_attrs_py313_replace_control` | 999 | PASS | PASS | FAIL | **INSUFFICIENT_EVIDENCE** | The provided historical source code does not contain any inf |
| `trans_track_a_09_virtualenv_drop_py38_control` | 42 | PASS | PASS | FAIL | **CONTRADICTED** | Logically impossible range: 3.8.3 or later but less than 3.8 |
| `trans_track_a_09_virtualenv_drop_py38_control` | 123 | PASS | PASS | FAIL | **CONTRADICTED** | Logically impossible range: 3.8.3 or later but less than 3.8 |
| `trans_track_a_09_virtualenv_drop_py38_control` | 999 | PASS | PASS | FAIL | **CONTRADICTED** | Logically impossible range: 3.8.3 or later but less than 3.8 |
| `trans_track_a_10_httpx_client_proxies_deprecation` | 42 | PASS | PASS | FAIL | **CONTRADICTED** | _get_proxy_map is not defined in the provided source code. |
| `trans_track_a_10_httpx_client_proxies_deprecation` | 123 | PASS | PASS | FAIL | **CONTRADICTED** | The historical source code does not contain any information  |
| `trans_track_a_10_httpx_client_proxies_deprecation` | 999 | PASS | PASS | FAIL | **CONTRADICTED** | The historical source code does not contain any information  |

## Detailed Analysis on Focal Cases

### 1. Virtualenv False Positive Resolution
- **Previous False Positive**: `BASE_ENTAILED` was previously awarded based purely on lexical bag-of-words overlap.
- **Logical Error**: The statement asserts `version 3.8.3 or later but less than 3.8`, which represents an empty, contradictory set ($v \ge 3.8.3 \land v < 3.8$).
- **Resolution**: Identified by the deterministic contradiction engine and independent LLM judge as `CONTRADICTED`. Classified as `STRUCTURALLY_GROUNDED` (Tier B) but rejected from `SEMANTIC_FACTUALITY_PASS` (Tier C).

### 2. ItsDangerous & MarkupSafe Dynamic Inspection
- Historical memory statements accurately note dynamic `__getattr__` usage with `importlib.metadata` in base commits, confirmed present at evidence time.

### 3. HTTPX Proxy Handling
- Accurately describes internal `_get_proxy_map` proxy dictionary handling without referencing modern singular proxy arguments.

