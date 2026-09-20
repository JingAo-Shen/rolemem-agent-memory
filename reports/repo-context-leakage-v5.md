# Repository Context Leakage Audit Report V5

## Executive Summary

- **Total Transitions Evaluated**: 30
- **Retriever**: `RepoBM25Retriever` (Deterministic Okapi BM25, max_tokens=1200)
- **Audit Metric**: Evaluates whether real retrieved workspace context gives away target solutions.

## Leakage Level Distribution

- `REPO_CONTEXT_HINTED`: 22 / 30 (73.3%)
- `REPO_CONTEXT_NONTRIVIAL`: 7 / 30 (23.3%)
- `REPO_CONTEXT_TRIVIALIZES_TASK`: 1 / 30 (3.3%)

## Detailed Audit Table

| Transition ID | Leakage Level | Files Retrieved | Tokens | Hints Found |
| :--- | :--- | :--- | :---: | :--- |
| `trans_track_a_01_click_stream_deprecations` | `REPO_CONTEXT_HINTED` | `src/click/utils.py, src/click/_compat.py (+1)` | 1200 | buffer, deprecated |
| `trans_track_a_02_flask_should_ignore_error` | `REPO_CONTEXT_HINTED` | `src/flask/app.py, src/flask/app.py (+2)` | 1185 | deprecated |
| `trans_track_a_03_werkzeug_environ_property` | `REPO_CONTEXT_HINTED` | `src/werkzeug/datastructures/csp.py, src/werkzeug/sansio/request.py (+1)` | 1200 | environ, deprecated |
| `trans_track_a_04_jinja_version_deprecation` | `REPO_CONTEXT_HINTED` | `src/jinja2/__init__.py, src/jinja2/environment.py (+2)` | 1200 | version, deprecated, metadata |
| `trans_track_a_05_itsdangerous_version_removal` | `REPO_CONTEXT_HINTED` | `src/itsdangerous/serializer.py, src/itsdangerous/signer.py (+1)` | 1200 | version |
| `trans_track_a_06_markupsafe_version_removal` | `REPO_CONTEXT_NONTRIVIAL` | `src/markupsafe/_speedups.c, src/markupsafe/_speedups.c (+2)` | 1168 | None |
| `trans_track_a_07_pluggy_varnames_noself` | `REPO_CONTEXT_HINTED` | `src/pluggy/_hooks.py, src/pluggy/_hooks.py (+1)` | 1200 | self |
| `trans_track_a_08_attrs_py313_replace_control` | `REPO_CONTEXT_HINTED` | `src/attr/_make.py, src/attr/_make.py (+2)` | 1200 | replace, deprecated |
| `trans_track_a_09_virtualenv_drop_py38_control` | `REPO_CONTEXT_HINTED` | `src/virtualenv/create/via_global_ref/builtin/pypy/pypy3.py, src/virtualenv/create/via_global_ref/venv.py (+1)` | 1200 | False |
| `trans_track_a_10_httpx_client_proxies_deprecation` | `REPO_CONTEXT_HINTED` | `httpx/_main.py, httpx/_client.py (+1)` | 1173 | proxy |
| `trans_track_a_11_requests_json_decode_error` | `REPO_CONTEXT_HINTED` | `requests/exceptions.py, requests/models.py (+2)` | 1193 | RequestException |
| `trans_track_a_12_urllib3_getheaders_removal` | `REPO_CONTEXT_HINTED` | `src/urllib3/_collections.py, src/urllib3/_collections.py (+2)` | 1200 | headers |
| `trans_track_a_13_starlette_weak_etag_removeprefix` | `REPO_CONTEXT_HINTED` | `starlette/staticfiles.py, starlette/responses.py (+1)` | 1200 | StaticFiles, is_not_modified |
| `trans_track_a_14_fastapi_on_event_compatibility` | `REPO_CONTEXT_HINTED` | `fastapi/routing.py, fastapi/routing.py (+3)` | 1146 | deprecated, routing |
| `trans_track_a_15_more_itertools_zip_equal_removal` | `REPO_CONTEXT_HINTED` | `more_itertools/more.py, more_itertools/more.py (+2)` | 1194 | zip |
| `trans_track_a_16_rich_file_proxy_isatty` | `REPO_CONTEXT_NONTRIVIAL` | `rich/console.py, rich/jupyter.py (+1)` | 1200 | None |
| `trans_track_a_17_celery_task_module_cleanup` | `REPO_CONTEXT_NONTRIVIAL` | `celery/backends/base.py, celery/backends/base.py (+2)` | 1200 | None |
| `trans_track_a_18_marshmallow_pprint_export_removal` | `REPO_CONTEXT_HINTED` | `src/marshmallow/schema.py, src/marshmallow/fields.py (+1)` | 1200 | fields |
| `trans_track_a_19_flake8_doctest_options_removal` | `REPO_CONTEXT_NONTRIVIAL` | `src/flake8/checker.py, src/flake8/plugins/finder.py (+2)` | 1115 | None |
| `trans_track_a_20_iniconfig_strip_inline_comments` | `REPO_CONTEXT_HINTED` | `src/iniconfig/__init__.py, src/iniconfig/_parse.py (+2)` | 1117 | parse, strip_inline_comments |
| `trans_track_a_21_packaging_legacy_version_removal` | `REPO_CONTEXT_HINTED` | `packaging/_manylinux.py, packaging/specifiers.py (+1)` | 1200 | Version |
| `trans_track_a_22_dateutil_unknown_timezone_warning` | `REPO_CONTEXT_HINTED` | `dateutil/zoneinfo/__init__.py, dateutil/parser/_parser.py (+2)` | 1156 | UnknownTimezoneWarning, deprecated |
| `trans_track_a_23_tqdm_asyncio_gather_return_exceptions` | `REPO_CONTEXT_HINTED` | `tqdm/asyncio.py, tqdm/asyncio.py (+3)` | 1175 | return_exceptions |
| `trans_track_a_24_cachelib_timeout_timedelta` | `REPO_CONTEXT_HINTED` | `src/cachelib/uwsgi.py, src/cachelib/base.py (+1)` | 1200 | _normalize_timeout |
| `trans_track_a_25_uvicorn_wsgi_middleware_deprecation` | `REPO_CONTEXT_HINTED` | `uvicorn/middleware/wsgi.py, uvicorn/protocols/http/httptools_impl.py (+1)` | 1200 | WSGIMiddleware, deprecated |
| `trans_track_a_26_rich_render_group_to_group` | `REPO_CONTEXT_TRIVIALIZES_TASK` | `rich/text.py, rich/console.py (+2)` | 1200 | Group |
| `trans_track_a_27_marshmallow_ipaddress_type_mapping` | `REPO_CONTEXT_NONTRIVIAL` | `src/marshmallow/fields.py, src/marshmallow/fields.py (+1)` | 1200 | None |
| `trans_track_a_28_starlette_exceptions_middleware_removal` | `REPO_CONTEXT_HINTED` | `starlette/testclient.py, starlette/applications.py (+1)` | 1200 | ExceptionMiddleware, deprecated |
| `trans_track_a_29_pluggy_static_hook_attr_discovery` | `REPO_CONTEXT_NONTRIVIAL` | `src/pluggy/_manager.py, src/pluggy/_hooks.py (+1)` | 1116 | None |
| `trans_track_a_30_fastapi_pydantic_v1_deprecation` | `REPO_CONTEXT_NONTRIVIAL` | `fastapi/security/http.py, fastapi/utils.py (+3)` | 1173 | None |

