# Semantic Transition Audit Report V4.1

## Executive Summary

- **Total Transitions Audited**: 30
- **Evaluation Policy**: Fail-closed, strict schema validation, zero-boolean default fallbacks
- **Semantic Pass Rate**: 12 / 30 (40.0%)
  - `SEMANTIC_STRONG_PASS`: 2 (6.7%)
  - `SEMANTIC_WEAK_PASS`: 10 (33.3%)
  - `REBUILD_REQUIRED`: 18 (60.0%)

## Task Mapping Classifications

- `REBUILD_MAPPING`: 6 / 30 (20.0%)
- `TASK_MAPPING_STRONG`: 15 / 30 (50.0%)
- `TASK_MAPPING_WEAK`: 9 / 30 (30.0%)

## Six-Question Semantic Gate Audit

| Question | Gate Name | Passed | Pass Rate | Requirement |
| :--- | :--- | :--- | :--- | :--- |
| Q1 | PR/Diff Cross-Support | 26/30 | 86.7% | Entailed code evidence & cross-support |
| Q2 | Base Memory Entailment | 18/30 | 60.0% | Entailed code evidence & cross-support |
| Q3 | Target Memory Entailment | 22/30 | 73.3% | Entailed code evidence & cross-support |
| Q4 | Task Capability Alignment | 30/30 | 100.0% | Entailed code evidence & cross-support |
| Q5 | Stale Solution Asymmetry | 19/30 | 63.3% | Entailed code evidence & cross-support |
| Q6 | Valid Solution Target Pass | 30/30 | 100.0% | Entailed code evidence & cross-support |

## Transition Breakdown

| Transition ID | Verdict | Task Mapping | Q1 | Q2 | Q3 | Q4 | Q5 | Q6 |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `trans_track_a_01_click_stream_deprecations` | `SEMANTIC_WEAK_PASS` | `TASK_MAPPING_STRONG` | PASS | PASS | PASS | PASS | PASS | PASS |
| `trans_track_a_02_flask_should_ignore_error` | `REBUILD_REQUIRED` | `REBUILD_MAPPING` | PASS | FAIL | FAIL | PASS | PASS | PASS |
| `trans_track_a_03_werkzeug_environ_property` | `SEMANTIC_WEAK_PASS` | `TASK_MAPPING_STRONG` | PASS | PASS | PASS | PASS | PASS | PASS |
| `trans_track_a_04_jinja_version_deprecation` | `SEMANTIC_WEAK_PASS` | `TASK_MAPPING_STRONG` | PASS | PASS | PASS | PASS | PASS | PASS |
| `trans_track_a_05_itsdangerous_version_removal` | `SEMANTIC_WEAK_PASS` | `TASK_MAPPING_STRONG` | PASS | PASS | PASS | PASS | PASS | PASS |
| `trans_track_a_06_markupsafe_version_removal` | `SEMANTIC_WEAK_PASS` | `TASK_MAPPING_STRONG` | PASS | PASS | PASS | PASS | PASS | PASS |
| `trans_track_a_07_pluggy_varnames_noself` | `REBUILD_REQUIRED` | `TASK_MAPPING_WEAK` | PASS | PASS | FAIL | PASS | PASS | PASS |
| `trans_track_a_08_attrs_py313_replace_control` | `SEMANTIC_STRONG_PASS` | `TASK_MAPPING_STRONG` | PASS | PASS | PASS | PASS | PASS | PASS |
| `trans_track_a_09_virtualenv_drop_py38_control` | `REBUILD_REQUIRED` | `TASK_MAPPING_WEAK` | PASS | PASS | FAIL | PASS | PASS | PASS |
| `trans_track_a_10_httpx_client_proxies_deprecation` | `SEMANTIC_STRONG_PASS` | `TASK_MAPPING_STRONG` | PASS | PASS | PASS | PASS | PASS | PASS |
| `trans_track_a_11_requests_json_decode_error` | `REBUILD_REQUIRED` | `TASK_MAPPING_STRONG` | PASS | PASS | PASS | PASS | FAIL | PASS |
| `trans_track_a_12_urllib3_getheaders_removal` | `SEMANTIC_WEAK_PASS` | `TASK_MAPPING_STRONG` | PASS | PASS | PASS | PASS | PASS | PASS |
| `trans_track_a_13_starlette_weak_etag_removeprefix` | `REBUILD_REQUIRED` | `TASK_MAPPING_WEAK` | FAIL | FAIL | PASS | PASS | FAIL | PASS |
| `trans_track_a_14_fastapi_on_event_compatibility` | `REBUILD_REQUIRED` | `TASK_MAPPING_WEAK` | PASS | FAIL | PASS | PASS | FAIL | PASS |
| `trans_track_a_15_more_itertools_zip_equal_removal` | `SEMANTIC_WEAK_PASS` | `TASK_MAPPING_STRONG` | PASS | PASS | PASS | PASS | PASS | PASS |
| `trans_track_a_16_rich_file_proxy_isatty` | `REBUILD_REQUIRED` | `TASK_MAPPING_WEAK` | PASS | FAIL | PASS | PASS | FAIL | PASS |
| `trans_track_a_17_celery_task_module_cleanup` | `REBUILD_REQUIRED` | `REBUILD_MAPPING` | PASS | FAIL | FAIL | PASS | PASS | PASS |
| `trans_track_a_18_marshmallow_pprint_export_removal` | `REBUILD_REQUIRED` | `REBUILD_MAPPING` | PASS | FAIL | FAIL | PASS | PASS | PASS |
| `trans_track_a_19_flake8_doctest_options_removal` | `REBUILD_REQUIRED` | `REBUILD_MAPPING` | PASS | FAIL | FAIL | PASS | PASS | PASS |
| `trans_track_a_20_iniconfig_strip_inline_comments` | `REBUILD_REQUIRED` | `REBUILD_MAPPING` | PASS | FAIL | FAIL | PASS | FAIL | PASS |
| `trans_track_a_21_packaging_legacy_version_removal` | `REBUILD_REQUIRED` | `TASK_MAPPING_WEAK` | PASS | FAIL | PASS | PASS | PASS | PASS |
| `trans_track_a_22_dateutil_unknown_timezone_warning` | `REBUILD_REQUIRED` | `TASK_MAPPING_WEAK` | FAIL | FAIL | PASS | PASS | FAIL | PASS |
| `trans_track_a_23_tqdm_asyncio_gather_return_exceptions` | `REBUILD_REQUIRED` | `TASK_MAPPING_STRONG` | PASS | PASS | PASS | PASS | FAIL | PASS |
| `trans_track_a_24_cachelib_timeout_timedelta` | `REBUILD_REQUIRED` | `TASK_MAPPING_WEAK` | FAIL | PASS | PASS | PASS | FAIL | PASS |
| `trans_track_a_25_uvicorn_wsgi_middleware_deprecation` | `SEMANTIC_WEAK_PASS` | `TASK_MAPPING_STRONG` | PASS | PASS | PASS | PASS | PASS | PASS |
| `trans_track_a_26_rich_render_group_to_group` | `SEMANTIC_WEAK_PASS` | `TASK_MAPPING_STRONG` | PASS | PASS | PASS | PASS | PASS | PASS |
| `trans_track_a_27_marshmallow_ipaddress_type_mapping` | `REBUILD_REQUIRED` | `REBUILD_MAPPING` | PASS | FAIL | FAIL | PASS | FAIL | PASS |
| `trans_track_a_28_starlette_exceptions_middleware_removal` | `SEMANTIC_WEAK_PASS` | `TASK_MAPPING_STRONG` | PASS | PASS | PASS | PASS | PASS | PASS |
| `trans_track_a_29_pluggy_static_hook_attr_discovery` | `REBUILD_REQUIRED` | `TASK_MAPPING_STRONG` | PASS | PASS | PASS | PASS | FAIL | PASS |
| `trans_track_a_30_fastapi_pydantic_v1_deprecation` | `REBUILD_REQUIRED` | `TASK_MAPPING_WEAK` | FAIL | FAIL | PASS | PASS | FAIL | PASS |
