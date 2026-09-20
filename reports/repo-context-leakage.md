# RoleMem Pilot-v1.4-r1 — Repository Context Leakage Audit Report (V3)

## 1. Executive Summary

- **Total Transitions Audited**: 30
- **REPO_CONTEXT_NONTRIVIAL**: **14 / 30 (46.7%)**
- **REPO_CONTEXT_HINTED**: **16 / 30 (53.3%)**
- **REPO_CONTEXT_NEAR_SOLUTION**: **0 / 30 (0.0%)**
- **REPO_CONTEXT_TRIVIALIZES_TASK**: **0 / 30 (0.0%)**

---

## 2. Leakage Classification Matrix

| Transition ID | Repository | Target Wrapper Found | Near-Solution Found | Replacement Hint | Leakage Classification |
| :--- | :--- | :---: | :---: | :---: | :--- |
| `trans_track_a_01_click_stream_deprecations` | `click` | NO | NO | YES | **REPO_CONTEXT_HINTED** |
| `trans_track_a_02_flask_should_ignore_error` | `flask` | NO | NO | NO | **REPO_CONTEXT_NONTRIVIAL** |
| `trans_track_a_03_werkzeug_environ_property` | `werkzeug` | NO | NO | NO | **REPO_CONTEXT_NONTRIVIAL** |
| `trans_track_a_04_jinja_version_deprecation` | `jinja` | NO | NO | YES | **REPO_CONTEXT_HINTED** |
| `trans_track_a_05_itsdangerous_version_removal` | `itsdangerous` | NO | NO | NO | **REPO_CONTEXT_NONTRIVIAL** |
| `trans_track_a_06_markupsafe_version_removal` | `markupsafe` | NO | NO | NO | **REPO_CONTEXT_NONTRIVIAL** |
| `trans_track_a_07_pluggy_varnames_noself` | `pluggy` | NO | NO | YES | **REPO_CONTEXT_HINTED** |
| `trans_track_a_08_attrs_py313_replace_control` | `attrs` | NO | NO | YES | **REPO_CONTEXT_HINTED** |
| `trans_track_a_09_virtualenv_drop_py38_control` | `virtualenv` | NO | NO | YES | **REPO_CONTEXT_HINTED** |
| `trans_track_a_10_httpx_client_proxies_deprecation` | `httpx` | NO | NO | NO | **REPO_CONTEXT_NONTRIVIAL** |
| `trans_track_a_11_requests_json_decode_error` | `requests` | NO | NO | YES | **REPO_CONTEXT_HINTED** |
| `trans_track_a_12_urllib3_getheaders_removal` | `urllib3` | NO | NO | YES | **REPO_CONTEXT_HINTED** |
| `trans_track_a_13_starlette_weak_etag_removeprefix` | `starlette` | NO | NO | YES | **REPO_CONTEXT_HINTED** |
| `trans_track_a_14_fastapi_on_event_compatibility` | `fastapi` | NO | NO | NO | **REPO_CONTEXT_NONTRIVIAL** |
| `trans_track_a_15_more_itertools_zip_equal_removal` | `more-itertools` | NO | NO | NO | **REPO_CONTEXT_NONTRIVIAL** |
| `trans_track_a_16_rich_file_proxy_isatty` | `rich` | NO | NO | NO | **REPO_CONTEXT_NONTRIVIAL** |
| `trans_track_a_17_celery_task_module_cleanup` | `celery` | NO | NO | YES | **REPO_CONTEXT_HINTED** |
| `trans_track_a_18_marshmallow_pprint_export_removal` | `marshmallow` | NO | NO | YES | **REPO_CONTEXT_HINTED** |
| `trans_track_a_19_flake8_doctest_options_removal` | `flake8` | NO | NO | NO | **REPO_CONTEXT_NONTRIVIAL** |
| `trans_track_a_20_iniconfig_strip_inline_comments` | `iniconfig` | NO | NO | YES | **REPO_CONTEXT_HINTED** |
| `trans_track_a_21_packaging_legacy_version_removal` | `packaging` | NO | NO | YES | **REPO_CONTEXT_HINTED** |
| `trans_track_a_22_dateutil_unknown_timezone_warning` | `dateutil` | NO | NO | YES | **REPO_CONTEXT_HINTED** |
| `trans_track_a_23_tqdm_asyncio_gather_return_exceptions` | `tqdm` | NO | NO | YES | **REPO_CONTEXT_HINTED** |
| `trans_track_a_24_cachelib_timeout_timedelta` | `cachelib` | NO | NO | YES | **REPO_CONTEXT_HINTED** |
| `trans_track_a_25_uvicorn_wsgi_middleware_deprecation` | `uvicorn` | NO | NO | NO | **REPO_CONTEXT_NONTRIVIAL** |
| `trans_track_a_26_rich_render_group_to_group` | `rich` | NO | NO | YES | **REPO_CONTEXT_HINTED** |
| `trans_track_a_27_marshmallow_ipaddress_type_mapping` | `marshmallow` | NO | NO | NO | **REPO_CONTEXT_NONTRIVIAL** |
| `trans_track_a_28_starlette_exceptions_middleware_removal` | `starlette` | NO | NO | NO | **REPO_CONTEXT_NONTRIVIAL** |
| `trans_track_a_29_pluggy_static_hook_attr_discovery` | `pluggy` | NO | NO | NO | **REPO_CONTEXT_NONTRIVIAL** |
| `trans_track_a_30_fastapi_pydantic_v1_deprecation` | `fastapi` | NO | NO | NO | **REPO_CONTEXT_NONTRIVIAL** |

---

## 3. Methodological Criteria

- `NONTRIVIAL`: Context provides zero leakage of replacement symbols, comments, or AST structures.
- `HINTED`: Context contains generic mention of library identifiers, but no runnable solutions or invocations.
- `NEAR_SOLUTION`: Context contains migration comments or direct replacement symbol invocations that make solution trivial without memory.
- `TRIVIALIZES_TASK`: Context includes the exact wrapper function implementation required by the task.

