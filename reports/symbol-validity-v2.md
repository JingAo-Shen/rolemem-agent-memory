# Symbol-Level Validity Evaluation Report V2

## Executive Summary
- **Total Multi-Repo Empirical Cases**: 102
- **Total Repositories Represented**: 21
- **Valid Preservation Ground Truth**: 63
- **Genuine Stale Ground Truth**: 39

## Formal Comparison: File-Level Baseline vs. Symbol-Level Mechanism

| Metric | File-Level Baseline ($F_{file}$) | Symbol-Level Mechanism ($F_{symbol}$) | RoleMem Advantage |
| :--- | :---: | :---: | :---: |
| **False Invalidation Rate (FIR)** | 100.0% (63/63) | 0.0% (0/63) | **-100.0% (Zero False Invalidation)** |
| **Valid Memory Recall (VMR)** | 0.0% (0/63) | 100.0% (63/63) | **+100.0% Perfect Retention** |
| **Stale Exposure Rate (SER)** | 0.0% (0/39) | 0.0% (0/39) | **0.0% (Zero Leakage)** |
| **Stale Memory Recall** | 100.0% | 100.0% | **100.0% Complete Invalidation** |

## Dataset Diversity & Multi-Repository Distribution

| Repository | Cases |
| :--- | :---: |
| `attrs` | 5 |
| `cachelib` | 5 |
| `celery` | 4 |
| `click` | 5 |
| `dateutil` | 4 |
| `fastapi` | 5 |
| `flask` | 5 |
| `httpx` | 5 |
| `iniconfig` | 5 |
| `markupsafe` | 4 |
| `more-itertools` | 5 |
| `packaging` | 5 |
| `pluggy` | 5 |
| `requests` | 5 |
| `rich` | 5 |
| `starlette` | 5 |
| `tqdm` | 5 |
| `urllib3` | 5 |
| `uvicorn` | 5 |
| `virtualenv` | 5 |
| `werkzeug` | 5 |

### Symbol Type Breakdown

| Symbol Type | Count |
| :--- | :---: |
| `assignment` | 23 |
| `class` | 29 |
| `function` | 7 |
| `method` | 43 |
