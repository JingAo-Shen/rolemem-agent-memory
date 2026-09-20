# Historical Memory Factuality & 3-Tier Audit Report

## 1. Calibration Set Historical Factuality (10 Transitions × 3 Seeds = 30 Runs)

- **Total Statements Audited**: 30
- **Tier A: Temporal Isolation Pass**: **30 / 30 (100.0%)**
- **Tier B: Structural Grounding Pass**: **30 / 30 (100.0%)**
- **Tier C: Semantic Factuality Pass**: **18 / 30 (60.0%)**

| Transition ID | Seed | Temporal Isolation | Structural Grounding | Semantic Factuality | Status |
| :--- | :---: | :---: | :---: | :---: | :--- |
| `trans_track_a_01_click_stream_deprecations` | 42 | PASS | PASS | PASS | **FACTUALLY_SUPPORTED** |
| `trans_track_a_01_click_stream_deprecations` | 123 | PASS | PASS | PASS | **FACTUALLY_SUPPORTED** |
| `trans_track_a_01_click_stream_deprecations` | 999 | PASS | PASS | PASS | **FACTUALLY_SUPPORTED** |
| `trans_track_a_02_flask_should_ignore_error` | 42 | PASS | PASS | FAIL | **CONTRADICTED** |
| `trans_track_a_02_flask_should_ignore_error` | 123 | PASS | PASS | FAIL | **CONTRADICTED** |
| `trans_track_a_02_flask_should_ignore_error` | 999 | PASS | PASS | FAIL | **CONTRADICTED** |
| `trans_track_a_03_werkzeug_environ_property` | 42 | PASS | PASS | PASS | **FACTUALLY_SUPPORTED** |
| `trans_track_a_03_werkzeug_environ_property` | 123 | PASS | PASS | PASS | **FACTUALLY_SUPPORTED** |
| `trans_track_a_03_werkzeug_environ_property` | 999 | PASS | PASS | PASS | **FACTUALLY_SUPPORTED** |
| `trans_track_a_04_jinja_version_deprecation` | 42 | PASS | PASS | PASS | **FACTUALLY_SUPPORTED** |
| `trans_track_a_04_jinja_version_deprecation` | 123 | PASS | PASS | PASS | **FACTUALLY_SUPPORTED** |
| `trans_track_a_04_jinja_version_deprecation` | 999 | PASS | PASS | PASS | **FACTUALLY_SUPPORTED** |
| `trans_track_a_05_itsdangerous_version_removal` | 42 | PASS | PASS | PASS | **FACTUALLY_SUPPORTED** |
| `trans_track_a_05_itsdangerous_version_removal` | 123 | PASS | PASS | PASS | **FACTUALLY_SUPPORTED** |
| `trans_track_a_05_itsdangerous_version_removal` | 999 | PASS | PASS | PASS | **FACTUALLY_SUPPORTED** |
| `trans_track_a_06_markupsafe_version_removal` | 42 | PASS | PASS | PASS | **FACTUALLY_SUPPORTED** |
| `trans_track_a_06_markupsafe_version_removal` | 123 | PASS | PASS | PASS | **FACTUALLY_SUPPORTED** |
| `trans_track_a_06_markupsafe_version_removal` | 999 | PASS | PASS | PASS | **FACTUALLY_SUPPORTED** |
| `trans_track_a_07_pluggy_varnames_noself` | 42 | PASS | PASS | PASS | **FACTUALLY_SUPPORTED** |
| `trans_track_a_07_pluggy_varnames_noself` | 123 | PASS | PASS | PASS | **FACTUALLY_SUPPORTED** |
| `trans_track_a_07_pluggy_varnames_noself` | 999 | PASS | PASS | PASS | **FACTUALLY_SUPPORTED** |
| `trans_track_a_08_attrs_py313_replace_control` | 42 | PASS | PASS | FAIL | **INSUFFICIENT_EVIDENCE** |
| `trans_track_a_08_attrs_py313_replace_control` | 123 | PASS | PASS | FAIL | **INSUFFICIENT_EVIDENCE** |
| `trans_track_a_08_attrs_py313_replace_control` | 999 | PASS | PASS | FAIL | **INSUFFICIENT_EVIDENCE** |
| `trans_track_a_09_virtualenv_drop_py38_control` | 42 | PASS | PASS | FAIL | **CONTRADICTED** |
| `trans_track_a_09_virtualenv_drop_py38_control` | 123 | PASS | PASS | FAIL | **CONTRADICTED** |
| `trans_track_a_09_virtualenv_drop_py38_control` | 999 | PASS | PASS | FAIL | **CONTRADICTED** |
| `trans_track_a_10_httpx_client_proxies_deprecation` | 42 | PASS | PASS | FAIL | **CONTRADICTED** |
| `trans_track_a_10_httpx_client_proxies_deprecation` | 123 | PASS | PASS | FAIL | **CONTRADICTED** |
| `trans_track_a_10_httpx_client_proxies_deprecation` | 999 | PASS | PASS | FAIL | **CONTRADICTED** |

---

## 2. Scale Candidate Historical Factuality (6 Candidate Transitions × 3 Seeds = 18 Runs)

- **Total Statements Audited**: 18
- **Tier A: Temporal Isolation Pass**: **18 / 18 (100.0%)**
- **Tier B: Structural Grounding Pass**: **18 / 18 (100.0%)**
- **Tier C: Semantic Factuality Pass**: **16 / 18 (88.9%)**

| Transition ID | Seed | Temporal Isolation | Structural Grounding | Semantic Factuality | Status |
| :--- | :---: | :---: | :---: | :---: | :--- |
| `trans_track_a_15_more_itertools_zip_equal_removal` | 42 | PASS | PASS | PASS | **FACTUALLY_SUPPORTED** |
| `trans_track_a_15_more_itertools_zip_equal_removal` | 123 | PASS | PASS | PASS | **FACTUALLY_SUPPORTED** |
| `trans_track_a_15_more_itertools_zip_equal_removal` | 999 | PASS | PASS | PASS | **FACTUALLY_SUPPORTED** |
| `trans_track_a_16_rich_file_proxy_isatty` | 42 | PASS | PASS | PASS | **FACTUALLY_SUPPORTED** |
| `trans_track_a_16_rich_file_proxy_isatty` | 123 | PASS | PASS | PASS | **FACTUALLY_SUPPORTED** |
| `trans_track_a_16_rich_file_proxy_isatty` | 999 | PASS | PASS | PASS | **FACTUALLY_SUPPORTED** |
| `trans_track_a_20_iniconfig_strip_inline_comments` | 42 | PASS | PASS | PASS | **FACTUALLY_SUPPORTED** |
| `trans_track_a_20_iniconfig_strip_inline_comments` | 123 | PASS | PASS | PASS | **FACTUALLY_SUPPORTED** |
| `trans_track_a_20_iniconfig_strip_inline_comments` | 999 | PASS | PASS | PASS | **FACTUALLY_SUPPORTED** |
| `trans_track_a_24_cachelib_timeout_timedelta` | 42 | PASS | PASS | PASS | **FACTUALLY_SUPPORTED** |
| `trans_track_a_24_cachelib_timeout_timedelta` | 123 | PASS | PASS | PASS | **FACTUALLY_SUPPORTED** |
| `trans_track_a_24_cachelib_timeout_timedelta` | 999 | PASS | PASS | PASS | **FACTUALLY_SUPPORTED** |
| `trans_track_a_25_uvicorn_wsgi_middleware_deprecation` | 42 | PASS | PASS | FAIL | **PARTIAL** |
| `trans_track_a_25_uvicorn_wsgi_middleware_deprecation` | 123 | PASS | PASS | FAIL | **PARTIAL** |
| `trans_track_a_25_uvicorn_wsgi_middleware_deprecation` | 999 | PASS | PASS | PASS | **FACTUALLY_SUPPORTED** |
| `trans_track_a_26_rich_render_group_to_group` | 42 | PASS | PASS | PASS | **FACTUALLY_SUPPORTED** |
| `trans_track_a_26_rich_render_group_to_group` | 123 | PASS | PASS | PASS | **FACTUALLY_SUPPORTED** |
| `trans_track_a_26_rich_render_group_to_group` | 999 | PASS | PASS | PASS | **FACTUALLY_SUPPORTED** |

---

## 3. Key Observations & Disentangled Metrics

- **Denominators strictly segregated**: Calibration historical factuality (18/30 = 60.0%) and Scale candidate historical factuality (16/18 = 88.9%) are reported independently.
- **Fail-closed verification**: Unparseable responses or unsupported assertions fail closed as `INSUFFICIENT_EVIDENCE` or `PARTIAL`, ensuring zero synthetic factuality.
