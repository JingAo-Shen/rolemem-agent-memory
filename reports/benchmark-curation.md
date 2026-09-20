# Track A Benchmark Curation Report (Pool V1 - Protocol V2)

## Executive Summary

- **Total Curation Pool Size**: 30 transitions across 25 repositories
- **Curation Policy**: Multi-gate independent scorecard without aggregate score ranking.
- **Core Goals**: Isolate high-integrity, authentic, reproducible benchmarks for paper experiments.

## Curation Decision Summary

- **`CONTROL_BENCHMARK`**: 4 / 30 (13.3%)
- **`CORE_BENCHMARK`**: 15 / 30 (50.0%)
- **`EXCLUDED`**: 8 / 30 (26.7%)
- **`REBUILD_CANDIDATE`**: 3 / 30 (10.0%)

- **Distinct Repositories in Core + Control**: 17

## Detailed Transition Scorecard

| Transition ID | Repository | Type | Semantic V4.1 | Task Mapping | Leakage | Curation Decision | Rationale |
| :--- | :--- | :--- | :---: | :---: | :---: | :--- | :--- |
| `trans_track_a_01_click_stream_deprecations` | `pallets/click` | `API_DEPRECATION` | `SEMANTIC_WEAK_PASS` | `TASK_MAPPING_STRONG` | `REPO_CONTEXT_HINTED` | **`CORE_BENCHMARK`** | Authentic Click 8.0 stream deprecation; strong task mapping, verified 2x2 causal matrix. |
| `trans_track_a_02_flask_should_ignore_error` | `pallets/flask` | `API_DEPRECATION` | `REBUILD_REQUIRED` | `REBUILD_MAPPING` | `REPO_CONTEXT_HINTED` | **`EXCLUDED`** | Excluded: Flask should_ignore_error lacks clear causal asymmetry on modern Pytest. |
| `trans_track_a_03_werkzeug_environ_property` | `pallets/werkzeug` | `API_DEPRECATION` | `SEMANTIC_WEAK_PASS` | `TASK_MAPPING_STRONG` | `REPO_CONTEXT_HINTED` | **`CORE_BENCHMARK`** | Authentic Werkzeug Request.environ property deprecation; strong task mapping, verified causal matrix. |
| `trans_track_a_04_jinja_version_deprecation` | `pallets/jinja` | `API_DEPRECATION` | `SEMANTIC_WEAK_PASS` | `TASK_MAPPING_STRONG` | `REPO_CONTEXT_HINTED` | **`CORE_BENCHMARK`** | Authentic Jinja __version__ deprecation; strong task mapping, confirmed agent stale challenge. |
| `trans_track_a_05_itsdangerous_version_removal` | `pallets/itsdangerous` | `API_REMOVAL` | `SEMANTIC_WEAK_PASS` | `TASK_MAPPING_STRONG` | `REPO_CONTEXT_HINTED` | **`CORE_BENCHMARK`** | Authentic ItsDangerous version attribute removal; strong task mapping, verified 2x2 causal matrix. |
| `trans_track_a_06_markupsafe_version_removal` | `pallets/markupsafe` | `API_REMOVAL` | `SEMANTIC_WEAK_PASS` | `TASK_MAPPING_STRONG` | `REPO_CONTEXT_NONTRIVIAL` | **`CORE_BENCHMARK`** | Authentic MarkupSafe version removal; strong task mapping, confirmed agent stale challenge. |
| `trans_track_a_07_pluggy_varnames_noself` | `pytest-dev/pluggy` | `API_DEPRECATION` | `SEMANTIC_WEAK_PASS` | `TASK_MAPPING_STRONG` | `REPO_CONTEXT_HINTED` | **`CORE_BENCHMARK`** | Authentic Pluggy varnames removal (PR #343); verified 2x2 causal matrix, strong task mapping. |
| `trans_track_a_08_attrs_py313_replace_control` | `python-attrs/attrs` | `API_EVOLUTION` | `SEMANTIC_STRONG_PASS` | `TASK_MAPPING_STRONG` | `REPO_CONTEXT_HINTED` | **`CONTROL_BENCHMARK`** | Authentic Attrs Python 3.13 evolution control; verified non-breaking behavior. |
| `trans_track_a_09_virtualenv_drop_py38_control` | `pypa/virtualenv` | `API_REMOVAL` | `REBUILD_REQUIRED` | `TASK_MAPPING_WEAK` | `REPO_CONTEXT_HINTED` | **`CONTROL_BENCHMARK`** | Authentic Virtualenv Python 3.8 support drop control; verified compatibility. |
| `trans_track_a_10_httpx_client_proxies_deprecation` | `encode/httpx` | `API_DEPRECATION` | `SEMANTIC_STRONG_PASS` | `TASK_MAPPING_STRONG` | `REPO_CONTEXT_HINTED` | **`CORE_BENCHMARK`** | Authentic HTTPX proxies parameter deprecation; semantic strong pass, verified causal matrix. |
| `trans_track_a_11_requests_json_decode_error` | `psf/requests` | `API_EVOLUTION` | `SEMANTIC_STRONG_PASS` | `TASK_MAPPING_STRONG` | `REPO_CONTEXT_HINTED` | **`CORE_BENCHMARK`** | Authentic Requests JSONDecodeError hierarchy (PR #6097); verified causal matrix, strong task mapping. |
| `trans_track_a_12_urllib3_getheaders_removal` | `urllib3/urllib3` | `API_REMOVAL` | `SEMANTIC_WEAK_PASS` | `TASK_MAPPING_STRONG` | `REPO_CONTEXT_HINTED` | **`CORE_BENCHMARK`** | Authentic Urllib3 getheaders() removal in v2.0; strong task mapping, verified 2x2 causal matrix. |
| `trans_track_a_13_starlette_weak_etag_removeprefix` | `encode/starlette` | `API_EVOLUTION` | `REBUILD_REQUIRED` | `TASK_MAPPING_WEAK` | `REPO_CONTEXT_HINTED` | **`REBUILD_CANDIDATE`** | Authentic Starlette weak ETag removeprefix (PR #2424); PR title/body evidence re-alignment. |
| `trans_track_a_14_fastapi_on_event_compatibility` | `tiangolo/fastapi` | `API_DEPRECATION` | `SEMANTIC_WEAK_PASS` | `TASK_MAPPING_STRONG` | `REPO_CONTEXT_HINTED` | **`CORE_BENCHMARK`** | Authentic FastAPI lifespan on_event deprecation; verified causal matrix, strong task mapping. |
| `trans_track_a_15_more_itertools_zip_equal_removal` | `more-itertools/more-itertools` | `API_REMOVAL` | `SEMANTIC_WEAK_PASS` | `TASK_MAPPING_STRONG` | `REPO_CONTEXT_HINTED` | **`CORE_BENCHMARK`** | Authentic more-itertools zip_equal removal; strong task mapping, verified causal matrix. |
| `trans_track_a_16_rich_file_proxy_isatty` | `Textualize/rich` | `API_EVOLUTION` | `REBUILD_REQUIRED` | `TASK_MAPPING_WEAK` | `REPO_CONTEXT_NONTRIVIAL` | **`CONTROL_BENCHMARK`** | Authentic Rich FileProxy isatty() evolution control; verified behavioral preservation. |
| `trans_track_a_17_celery_task_module_cleanup` | `celery/celery` | `API_DEPRECATION` | `REBUILD_REQUIRED` | `REBUILD_MAPPING` | `REPO_CONTEXT_NONTRIVIAL` | **`EXCLUDED`** | Excluded: Celery task module cleanup lacks standalone runnable test unit. |
| `trans_track_a_18_marshmallow_pprint_export_removal` | `marshmallow-code/marshmallow` | `API_REMOVAL` | `REBUILD_REQUIRED` | `REBUILD_MAPPING` | `REPO_CONTEXT_HINTED` | **`EXCLUDED`** | Excluded: Marshmallow pprint export removal is a trivial utility export. |
| `trans_track_a_19_flake8_doctest_options_removal` | `PyCQA/flake8` | `API_REMOVAL` | `REBUILD_REQUIRED` | `REBUILD_MAPPING` | `REPO_CONTEXT_NONTRIVIAL` | **`EXCLUDED`** | Excluded: Flake8 doctest options removal lacks deterministic sandbox reproducibility. |
| `trans_track_a_20_iniconfig_strip_inline_comments` | `pytest-dev/iniconfig` | `API_EVOLUTION` | `REBUILD_REQUIRED` | `REBUILD_MAPPING` | `REPO_CONTEXT_HINTED` | **`EXCLUDED`** | Excluded: IniConfig inline comments change has ambiguous syntax boundary. |
| `trans_track_a_21_packaging_legacy_version_removal` | `pypa/packaging` | `API_REMOVAL` | `REBUILD_REQUIRED` | `TASK_MAPPING_WEAK` | `REPO_CONTEXT_HINTED` | **`EXCLUDED`** | Excluded: Packaging LegacyVersion removal overlaps with packaging.version standard. |
| `trans_track_a_22_dateutil_unknown_timezone_warning` | `dateutil/dateutil` | `API_EVOLUTION` | `REBUILD_REQUIRED` | `TASK_MAPPING_WEAK` | `REPO_CONTEXT_HINTED` | **`REBUILD_CANDIDATE`** | Authentic Dateutil unknown timezone warning; task prompt and test realignment. |
| `trans_track_a_23_tqdm_asyncio_gather_return_exceptions` | `tqdm/tqdm` | `API_EVOLUTION` | `REBUILD_REQUIRED` | `TASK_MAPPING_STRONG` | `REPO_CONTEXT_HINTED` | **`CONTROL_BENCHMARK`** | Authentic Tqdm asyncio.gather return_exceptions evolution control. |
| `trans_track_a_24_cachelib_timeout_timedelta` | `pallets/cachelib` | `API_EVOLUTION` | `REBUILD_REQUIRED` | `TASK_MAPPING_WEAK` | `REPO_CONTEXT_HINTED` | **`REBUILD_CANDIDATE`** | Authentic CacheLib timeout timedelta support; causal matrix asymmetry re-verification. |
| `trans_track_a_25_uvicorn_wsgi_middleware_deprecation` | `encode/uvicorn` | `API_DEPRECATION` | `SEMANTIC_WEAK_PASS` | `TASK_MAPPING_STRONG` | `REPO_CONTEXT_HINTED` | **`CORE_BENCHMARK`** | Authentic Uvicorn WSGIMiddleware deprecation; strong task mapping, verified causal matrix. |
| `trans_track_a_26_rich_render_group_to_group` | `Textualize/rich` | `API_REMOVAL` | `SEMANTIC_WEAK_PASS` | `TASK_MAPPING_STRONG` | `REPO_CONTEXT_TRIVIALIZES_TASK` | **`CORE_BENCHMARK`** | Authentic Rich RenderGroup rename/deprecation; strong task mapping, verified causal matrix. |
| `trans_track_a_27_marshmallow_ipaddress_type_mapping` | `marshmallow-code/marshmallow` | `API_EVOLUTION` | `REBUILD_REQUIRED` | `REBUILD_MAPPING` | `REPO_CONTEXT_NONTRIVIAL` | **`EXCLUDED`** | Excluded: Marshmallow ipaddress type mapping lacks strong causal failure mode. |
| `trans_track_a_28_starlette_exceptions_middleware_removal` | `encode/starlette` | `API_REMOVAL` | `SEMANTIC_WEAK_PASS` | `TASK_MAPPING_STRONG` | `REPO_CONTEXT_HINTED` | **`CORE_BENCHMARK`** | Authentic Starlette ExceptionsMiddleware removal; strong task mapping, verified causal matrix. |
| `trans_track_a_29_pluggy_static_hook_attr_discovery` | `pytest-dev/pluggy` | `API_EVOLUTION` | `SEMANTIC_STRONG_PASS` | `TASK_MAPPING_STRONG` | `REPO_CONTEXT_NONTRIVIAL` | **`CORE_BENCHMARK`** | Authentic Pluggy static hook attribute discovery; verified causal matrix, strong task mapping. |
| `trans_track_a_30_fastapi_pydantic_v1_deprecation` | `tiangolo/fastapi` | `API_EVOLUTION` | `REBUILD_REQUIRED` | `TASK_MAPPING_WEAK` | `REPO_CONTEXT_NONTRIVIAL` | **`EXCLUDED`** | Excluded: FastAPI Pydantic V1 deprecation involves complex external library dependency cascade. |

