# RoleMem Protocol V2.1-R1 — Gate-Based Benchmark Curation Report

## 1. Executive Curation Summary
- **Total Evaluated Transitions**: 30
- **Core Benchmark Candidates**: 13 provisional candidates (43.3%)
- **Control Benchmark Candidates**: 1 (3.3%)
- **Rebuild Candidates**: 12 (40.0%)
- **Excluded Transitions**: 4 (13.3%)
- **Distinct Repositories (Core)**: 13
- **Distinct Repositories (All)**: 25

---

## 2. Gate Verification Overview

| Gate | Description | Pass Count | Pass Rate |
| :--- | :--- | :--- | :--- |
| **1. Authenticity** | Real 40-char Git SHA & verified git commit | 30/30 | 100.0% |
| **2. Evidence Integrity** | Real diff hunks, PR URL & external evidence | 30/30 | 100.0% |
| **3. Causal Matrix** | Machine-generated 2x2 sandbox execution | 19/30 | 63.3% |
| **4. Stale Grounding** | Grounded historical memory | 30/30 | 100.0% |
| **5. Valid Grounding** | Grounded target memory | 30/30 | 100.0% |
| **6. Task Mapping** | Concrete pytest task mapping | 30/30 | 100.0% |
| **7. Leakage** | Non-trivial BM25 context | 29/30 | 96.7% |
| **8. Environment** | Sandbox execution 2-run reproducibility | 30/30 | 100.0% |

---

## 3. Core Benchmark Provisional Candidates

- **`trans_track_a_01_click_stream_deprecations`** (click): Passes all 8 formal gates: 100% real Git commits, machine-verified 2x2 causal matrix, and task mapping.
- **`trans_track_a_02_flask_should_ignore_error`** (flask): Passes all 8 formal gates: 100% real Git commits, machine-verified 2x2 causal matrix, and task mapping.
- **`trans_track_a_03_werkzeug_environ_property`** (werkzeug): Passes all 8 formal gates: 100% real Git commits, machine-verified 2x2 causal matrix, and task mapping.
- **`trans_track_a_04_jinja_version_deprecation`** (jinja): Passes all 8 formal gates: 100% real Git commits, machine-verified 2x2 causal matrix, and task mapping.
- **`trans_track_a_05_itsdangerous_version_removal`** (itsdangerous): Passes all 8 formal gates: 100% real Git commits, machine-verified 2x2 causal matrix, and task mapping.
- **`trans_track_a_06_markupsafe_version_removal`** (markupsafe): Passes all 8 formal gates: 100% real Git commits, machine-verified 2x2 causal matrix, and task mapping.
- **`trans_track_a_07_pluggy_varnames_noself`** (pluggy): Passes all 8 formal gates: 100% real Git commits, machine-verified 2x2 causal matrix, and task mapping.
- **`trans_track_a_09_virtualenv_drop_py38_control`** (virtualenv): Passes all 8 formal gates: 100% real Git commits, machine-verified 2x2 causal matrix, and task mapping.
- **`trans_track_a_10_httpx_client_proxies_deprecation`** (httpx): Passes all 8 formal gates: 100% real Git commits, machine-verified 2x2 causal matrix, and task mapping.
- **`trans_track_a_12_urllib3_getheaders_removal`** (urllib3): Passes all 8 formal gates: 100% real Git commits, machine-verified 2x2 causal matrix, and task mapping.
- **`trans_track_a_15_more_itertools_zip_equal_removal`** (more-itertools): Passes all 8 formal gates: 100% real Git commits, machine-verified 2x2 causal matrix, and task mapping.
- **`trans_track_a_25_uvicorn_wsgi_middleware_deprecation`** (uvicorn): Passes all 8 formal gates: 100% real Git commits, machine-verified 2x2 causal matrix, and task mapping.
- **`trans_track_a_28_starlette_exceptions_middleware_removal`** (starlette): Passes all 8 formal gates: 100% real Git commits, machine-verified 2x2 causal matrix, and task mapping.

## 4. Control Transitions

- **`trans_track_a_08_attrs_py313_replace_control`** (attrs): Verified negative evolution control passing sandbox stability criteria.