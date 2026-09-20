# Repository Context Leakage Audit Report (V2)

## Summary Metrics

- **Total Transitions Audited**: 30
- **REPO_CONTEXT_NONTRIVIAL**: **14 / 30 (46.7%)**
- **REPO_CONTEXT_HINTED**: **16 / 30 (53.3%)**
- **REPO_CONTEXT_TRIVIALIZES_TASK**: **0 / 30 (0.0%)**

> **Core Challenge Policy**: Only tasks with `REPO_CONTEXT_NONTRIVIAL` or `REPO_CONTEXT_HINTED` qualify for `AGENT_STALE_CHALLENGE_CORE`. Any task classified as `REPO_CONTEXT_TRIVIALIZES_TASK` is strictly barred from core challenge qualification and reserved for control analysis.

## Detailed Evaluation Matrix

| Transition ID | Repo | Classification | Found Replacements | Target Impl in Context | Migration Comments | Rationale |
| :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| `trans_track_a_01_click_stream_deprecations` | `pallets/click` | **REPO_CONTEXT_HINTED** | `buffer` | Clean | None | Context contains replacement symbols ['buffer'] or migration comm |
| `trans_track_a_02_flask_should_ignore_error` | `pallets/flask` | **REPO_CONTEXT_NONTRIVIAL** | `None` | Clean | None | Retrieved repository context contains neither replacement symbols |
| `trans_track_a_03_werkzeug_environ_property` | `pallets/werkzeug` | **REPO_CONTEXT_NONTRIVIAL** | `None` | Clean | None | Retrieved repository context contains neither replacement symbols |
| `trans_track_a_04_jinja_version_deprecation` | `pallets/jinja` | **REPO_CONTEXT_HINTED** | `importlib.metadata.version, importlib.metadata` | Clean | None | Context contains replacement symbols ['importlib.metadata.version |
| `trans_track_a_05_itsdangerous_version_removal` | `pallets/itsdangerous` | **REPO_CONTEXT_NONTRIVIAL** | `None` | Clean | None | Retrieved repository context contains neither replacement symbols |
| `trans_track_a_06_markupsafe_version_removal` | `pallets/markupsafe` | **REPO_CONTEXT_NONTRIVIAL** | `None` | Clean | None | Retrieved repository context contains neither replacement symbols |
| `trans_track_a_07_pluggy_varnames_noself` | `pytest-dev/pluggy` | **REPO_CONTEXT_HINTED** | `self` | Clean | None | Context contains replacement symbols ['self'] or migration commen |
| `trans_track_a_08_attrs_py313_replace_control` | `python-attrs/attrs` | **REPO_CONTEXT_HINTED** | `copy.replace` | Clean | None | Context contains replacement symbols ['copy.replace'] or migratio |
| `trans_track_a_09_virtualenv_drop_py38_control` | `pypa/virtualenv` | **REPO_CONTEXT_HINTED** | `False` | Clean | None | Context contains replacement symbols ['False'] or migration comme |
| `trans_track_a_10_httpx_client_proxies_deprecation` | `encode/httpx` | **REPO_CONTEXT_NONTRIVIAL** | `None` | Clean | None | Retrieved repository context contains neither replacement symbols |
| `trans_track_a_11_requests_json_decode_error` | `psf/requests` | **REPO_CONTEXT_HINTED** | `RequestException` | Clean | None | Context contains replacement symbols ['RequestException'] or migr |
| `trans_track_a_12_urllib3_getheaders_removal` | `urllib3/urllib3` | **REPO_CONTEXT_HINTED** | `headers` | Clean | None | Context contains replacement symbols ['headers'] or migration com |
| `trans_track_a_13_starlette_weak_etag_removeprefix` | `encode/starlette` | **REPO_CONTEXT_HINTED** | `StaticFiles, is_not_modified` | Clean | None | Context contains replacement symbols ['StaticFiles', 'is_not_modi |
| `trans_track_a_14_fastapi_on_event_compatibility` | `tiangolo/fastapi` | **REPO_CONTEXT_NONTRIVIAL** | `None` | Clean | None | Retrieved repository context contains neither replacement symbols |
| `trans_track_a_15_more_itertools_zip_equal_removal` | `more-itertools/more-itertools` | **REPO_CONTEXT_NONTRIVIAL** | `None` | Clean | None | Retrieved repository context contains neither replacement symbols |
| `trans_track_a_16_rich_file_proxy_isatty` | `Textualize/rich` | **REPO_CONTEXT_NONTRIVIAL** | `None` | Clean | None | Retrieved repository context contains neither replacement symbols |
| `trans_track_a_17_celery_task_module_cleanup` | `celery/celery` | **REPO_CONTEXT_HINTED** | `Task` | Clean | None | Context contains replacement symbols ['Task'] or migration commen |
| `trans_track_a_18_marshmallow_pprint_export_removal` | `marshmallow-code/marshmallow` | **REPO_CONTEXT_HINTED** | `fields` | Clean | None | Context contains replacement symbols ['fields'] or migration comm |
| `trans_track_a_19_flake8_doctest_options_removal` | `PyCQA/flake8` | **REPO_CONTEXT_NONTRIVIAL** | `None` | Clean | None | Retrieved repository context contains neither replacement symbols |
| `trans_track_a_20_iniconfig_strip_inline_comments` | `pytest-dev/iniconfig` | **REPO_CONTEXT_HINTED** | `IniConfig.parse, strip_inline_comments` | Clean | None | Context contains replacement symbols ['IniConfig.parse', 'strip_i |
| `trans_track_a_21_packaging_legacy_version_removal` | `pypa/packaging` | **REPO_CONTEXT_HINTED** | `Version` | Clean | None | Context contains replacement symbols ['Version'] or migration com |
| `trans_track_a_22_dateutil_unknown_timezone_warning` | `dateutil/dateutil` | **REPO_CONTEXT_HINTED** | `UnknownTimezoneWarning` | Clean | None | Context contains replacement symbols ['UnknownTimezoneWarning'] o |
| `trans_track_a_23_tqdm_asyncio_gather_return_exceptions` | `tqdm/tqdm` | **REPO_CONTEXT_HINTED** | `return_exceptions` | Clean | None | Context contains replacement symbols ['return_exceptions'] or mig |
| `trans_track_a_24_cachelib_timeout_timedelta` | `pallets/cachelib` | **REPO_CONTEXT_HINTED** | `_normalize_timeout` | Clean | None | Context contains replacement symbols ['_normalize_timeout'] or mi |
| `trans_track_a_25_uvicorn_wsgi_middleware_deprecation` | `encode/uvicorn` | **REPO_CONTEXT_NONTRIVIAL** | `None` | Clean | None | Retrieved repository context contains neither replacement symbols |
| `trans_track_a_26_rich_render_group_to_group` | `Textualize/rich` | **REPO_CONTEXT_HINTED** | `Group` | Clean | None | Context contains replacement symbols ['Group'] or migration comme |
| `trans_track_a_27_marshmallow_ipaddress_type_mapping` | `marshmallow-code/marshmallow` | **REPO_CONTEXT_NONTRIVIAL** | `None` | Clean | None | Retrieved repository context contains neither replacement symbols |
| `trans_track_a_28_starlette_exceptions_middleware_removal` | `encode/starlette` | **REPO_CONTEXT_NONTRIVIAL** | `None` | Clean | None | Retrieved repository context contains neither replacement symbols |
| `trans_track_a_29_pluggy_static_hook_attr_discovery` | `pytest-dev/pluggy` | **REPO_CONTEXT_NONTRIVIAL** | `None` | Clean | None | Retrieved repository context contains neither replacement symbols |
| `trans_track_a_30_fastapi_pydantic_v1_deprecation` | `tiangolo/fastapi` | **REPO_CONTEXT_NONTRIVIAL** | `None` | Clean | None | Retrieved repository context contains neither replacement symbols |
