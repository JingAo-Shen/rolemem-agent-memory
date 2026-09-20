# Repository Context Leakage Audit V4 Report

## Executive Summary
- **Total Transitions Audited**: 30
- **REPO_CONTEXT_NONTRIVIAL**: 7 / 30 (23.3%)
- **REPO_CONTEXT_HINTED**: 23 / 30 (76.7%)
- **REPO_CONTEXT_NEAR_SOLUTION**: 0 / 30 (0.0%)
- **REPO_CONTEXT_TRIVIALIZES_TASK**: 0 / 30 (0.0%)

## Detailed Leakage Classification

| Transition ID | Retrieved Tokens | Files Retrieved | Hinted Terms | Leakage Level |
| :--- | :---: | :---: | :---: | :--- |
| `trans_track_a_01_click_stream_deprecations` | 1200 | 0 files | `buffer, deprecated` | **REPO_CONTEXT_HINTED** |
| `trans_track_a_02_flask_should_ignore_error` | 1185 | 0 files | `deprecated` | **REPO_CONTEXT_HINTED** |
| `trans_track_a_03_werkzeug_environ_property` | 1200 | 0 files | `environ, deprecated` | **REPO_CONTEXT_HINTED** |
| `trans_track_a_04_jinja_version_deprecation` | 1200 | 0 files | `metadata, version, deprecated` | **REPO_CONTEXT_HINTED** |
| `trans_track_a_05_itsdangerous_version_removal` | 1200 | 0 files | `version` | **REPO_CONTEXT_HINTED** |
| `trans_track_a_06_markupsafe_version_removal` | 1168 | 0 files | `None` | **REPO_CONTEXT_NONTRIVIAL** |
| `trans_track_a_07_pluggy_varnames_noself` | 1200 | 0 files | `self` | **REPO_CONTEXT_HINTED** |
| `trans_track_a_08_attrs_py313_replace_control` | 1200 | 0 files | `replace, deprecated` | **REPO_CONTEXT_HINTED** |
| `trans_track_a_09_virtualenv_drop_py38_control` | 1200 | 0 files | `False` | **REPO_CONTEXT_HINTED** |
| `trans_track_a_10_httpx_client_proxies_deprecation` | 1173 | 0 files | `proxy` | **REPO_CONTEXT_HINTED** |
| `trans_track_a_11_requests_json_decode_error` | 1193 | 0 files | `RequestException` | **REPO_CONTEXT_HINTED** |
| `trans_track_a_12_urllib3_getheaders_removal` | 1200 | 0 files | `headers` | **REPO_CONTEXT_HINTED** |
| `trans_track_a_13_starlette_weak_etag_removeprefix` | 1200 | 0 files | `is_not_modified, StaticFiles` | **REPO_CONTEXT_HINTED** |
| `trans_track_a_14_fastapi_on_event_compatibility` | 1146 | 0 files | `routing, deprecated` | **REPO_CONTEXT_HINTED** |
| `trans_track_a_15_more_itertools_zip_equal_removal` | 1194 | 0 files | `zip` | **REPO_CONTEXT_HINTED** |
| `trans_track_a_16_rich_file_proxy_isatty` | 1200 | 0 files | `None` | **REPO_CONTEXT_NONTRIVIAL** |
| `trans_track_a_17_celery_task_module_cleanup` | 1200 | 0 files | `None` | **REPO_CONTEXT_NONTRIVIAL** |
| `trans_track_a_18_marshmallow_pprint_export_removal` | 1200 | 0 files | `fields` | **REPO_CONTEXT_HINTED** |
| `trans_track_a_19_flake8_doctest_options_removal` | 1115 | 0 files | `None` | **REPO_CONTEXT_NONTRIVIAL** |
| `trans_track_a_20_iniconfig_strip_inline_comments` | 1117 | 0 files | `strip_inline_comments, parse` | **REPO_CONTEXT_HINTED** |
| `trans_track_a_21_packaging_legacy_version_removal` | 1200 | 0 files | `Version` | **REPO_CONTEXT_HINTED** |
| `trans_track_a_22_dateutil_unknown_timezone_warning` | 1156 | 0 files | `UnknownTimezoneWarning, deprecated` | **REPO_CONTEXT_HINTED** |
| `trans_track_a_23_tqdm_asyncio_gather_return_exceptions` | 1175 | 0 files | `return_exceptions` | **REPO_CONTEXT_HINTED** |
| `trans_track_a_24_cachelib_timeout_timedelta` | 1200 | 0 files | `_normalize_timeout` | **REPO_CONTEXT_HINTED** |
| `trans_track_a_25_uvicorn_wsgi_middleware_deprecation` | 1200 | 0 files | `WSGIMiddleware, deprecated` | **REPO_CONTEXT_HINTED** |
| `trans_track_a_26_rich_render_group_to_group` | 1200 | 0 files | `Group` | **REPO_CONTEXT_HINTED** |
| `trans_track_a_27_marshmallow_ipaddress_type_mapping` | 1200 | 0 files | `None` | **REPO_CONTEXT_NONTRIVIAL** |
| `trans_track_a_28_starlette_exceptions_middleware_removal` | 1200 | 0 files | `ExceptionMiddleware, deprecated` | **REPO_CONTEXT_HINTED** |
| `trans_track_a_29_pluggy_static_hook_attr_discovery` | 1116 | 0 files | `None` | **REPO_CONTEXT_NONTRIVIAL** |
| `trans_track_a_30_fastapi_pydantic_v1_deprecation` | 1173 | 0 files | `None` | **REPO_CONTEXT_NONTRIVIAL** |
