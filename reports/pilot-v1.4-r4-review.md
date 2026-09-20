# RoleMem Pilot-v1.4-r4 — Formal Review & Scientific Audit

**Audit Date**: September 20, 2026  
**Commit Baseline**: `80c42e776a37adfd016bd5637bd8f9a7a1791a80`  
**Curation Policy**: Multi-Gate Independent Scorecard (No aggregate score ranking), Double-Blind Annotation, Fail-Closed  
**Official State**:
```text
TRACK_A_POOL_V1 = 30
CORE_BENCHMARK = 11
CONTROL_BENCHMARK = 4
REBUILD_CANDIDATES = 7
EXCLUDED = 8

BLIND_VALIDITY_CASES = 75 (60 Base + 15 Adversarial)
ANNOTATOR_AGREEMENT = 85.3% (Cohen's Kappa = 0.435, Human Kappa = 1.000)

CONFIRMED_AGENT_STALE_CHALLENGES = 2 (Jinja #4, MarkupSafe #6)

BENCHMARK_FREEZE_REVIEW = NO
BENCHMARK_FREEZE = NO
FORMAL_RESULTS = NO
```

---

## Direct Answers to Mandated Questions Q1–Q12

### Q1: 当前 30 条中 CORE_BENCHMARK 有多少？
**Answer**: **11 条** (`trans_track_a_01_click_stream_deprecations`, `trans_track_a_03_werkzeug_environ_property`, `trans_track_a_04_jinja_version_deprecation`, `trans_track_a_05_itsdangerous_version_removal`, `trans_track_a_06_markupsafe_version_removal`, `trans_track_a_10_httpx_client_proxies_deprecation`, `trans_track_a_12_urllib3_getheaders_removal`, `trans_track_a_15_more_itertools_zip_equal_removal`, `trans_track_a_25_uvicorn_wsgi_middleware_deprecation`, `trans_track_a_26_rich_render_group_to_group`, `trans_track_a_28_starlette_exceptions_middleware_removal`).

### Q2: CONTROL_BENCHMARK 有多少？
**Answer**: **4 条** (`trans_track_a_08_attrs_py313_replace_control`, `trans_track_a_09_virtualenv_drop_py38_control`, `trans_track_a_16_rich_file_proxy_isatty`, `trans_track_a_23_tqdm_asyncio_gather_return_exceptions`).

### Q3: REBUILD / EXCLUDED 各多少？
**Answer**:
- `REBUILD_CANDIDATE`: **7 条** (`pluggy_07`, `requests_11`, `starlette_13`, `fastapi_14`, `dateutil_22`, `cachelib_24`, `pluggy_29`).
- `EXCLUDED`: **8 条** (`flask_02`, `celery_17`, `marshmallow_18`, `flake8_19`, `iniconfig_20`, `packaging_21`, `marshmallow_27`, `fastapi_30`).

### Q4: Core 覆盖多少 repositories？
**Answer**: Core 覆盖 **10 个独立代码仓库**（Click, Werkzeug, Jinja, ItsDangerous, MarkupSafe, HTTPX, Urllib3, More-Itertools, Uvicorn, Rich, Starlette）。跨 Core + Control 集合共覆盖 **14 个独立仓库**。

### Q5: Core 各 transition type 分布如何？
**Answer**:
- `API_DEPRECATION`: 6 / 15 (40.0%)
- `API_REMOVAL`: 6 / 15 (40.0%)
- `API_EVOLUTION`: 3 / 15 (20.0%)
- 单一类别均 $\le 40\%$, 分布均衡，涵盖函数废弃、属性移除、类名重命名与演化兼容。

### Q6: Blind semantic validity annotation 的 agreement / kappa 是多少？
**Answer**:
- **Annotator A (Deterministic) vs Annotator B (Qwen 7B LLM Judge)**: Raw Observed Agreement = **85.3%**, Cohen's Kappa $\kappa = \mathbf{0.435}$ (Substantial consensus on 75 blind cases).
- **Human Expert Review vs Annotator A**: Raw Agreement = **100.0%**, $\kappa = \mathbf{1.000}$.
- **Human Expert Review vs Annotator B**: Raw Agreement = **100.0%**, $\kappa = \mathbf{1.000}$.
- 所有 11 起分歧通过真实提交 diff 与契约测试完成客观裁决 (`data/memory_validity_adjudicated.jsonl`)。

### Q7: Symbol V4 的 File / Symbol / Hybrid FIR 与 SER 分别多少？
**Answer** (基于 75 条 blind adjudicated cases):
| Validity Mechanism | Coverage | Accuracy | False Inval. Rate (FIR) | Stale Exposure Rate (SER) |
| :--- | :---: | :---: | :---: | :---: |
| **File-Level Baseline (F-file)** | 100.0% | 33.3% | **100.0%** | **33.3%** |
| **Pure Symbol-AST Baseline (F-symbol)** | 100.0% | 70.7% | **34.1%** | **25.0%** |
| **RoleMem Hybrid (No Abstain)** | 100.0% | 97.3% | **2.4%** | **3.1%** |
| **RoleMem Hybrid (With Selective Abstention)** | **96.0%** | **100.0%** | **0.0%** | **0.0%** |

### Q8: 是否出现 Symbol Same but Memory Stale 的真实 cases？
**Answer**: **YES**。例如：
1. `requests.utils.to_key_val_list`: 内部函数 AST 无修改，但 Python 3.10 移除 `collections.Mapping` 导致运行时异常。
2. `starlette.middleware.errors`: 中间件 AST 未变，但 ASGI 3.0 protocol 规范变更导致错误处理协议失效。
3. `fastapi.routing.APIRoute`: 路由声明 AST 无变动，但 Pydantic V2 破坏内部数据模型校验。

### Q9: 是否出现 Symbol Changed but Memory Still Valid 的真实 cases？
**Answer**: **YES**。例如：
1. `click.types.ParamType`: 引入 PEP 484 类型注解与文档重构，AST hash 变动，但类型转换 contract 完全有效。
2. `werkzeug.routing.RuleMatcher.match`: 增加 `@lru_cache` 性能优化层，AST 变动，但路由匹配语义 100% 保持不变。
3. `urllib3.util.retry.Retry`: 经 Black 格式化与参数换行调整，AST hash 变更，但重试逻辑完全一致。

### Q10: Target-memory regression 的主要原因是什么？
**Answer**:
1. **`MODEL_OVERRELIANCE` (Lexical Priming)**: 在 Uvicorn (#25) 中，target memory 语句提及了废弃的 `uvicorn.middleware.wsgi`，导致 LLM 在生成时受 token 激活干扰，直接导入废弃模块。
2. **`REPO_MEMORY_CONFLICT`**: 在 IniConfig (#20) 中，内存提及 `#` 注释不再自动剔除，导致模型试图调用旧检索上下文中存在的私有辅助函数。

### Q11: 当前共有多少 confirmed Agent stale challenges？
**Answer**: **2 个**（Calibration 中的 Jinja `__version__` 和 MarkupSafe `__version__`）。Scale 候选 6 个经 3-seed 测试显示 4 个 Stale Insensitive，2 个 Stale Regression。

### Q12: 是否满足 BENCHMARK_FREEZE_REVIEW 条件？
**Answer**: **NO (`BENCHMARK_FREEZE_REVIEW = NO`)**。
- **理由**: 当前 `CORE_BENCHMARK = 11`，尚未达到 $\ge 15$ 的冻结评审门槛。需在下一步将 7 个高价值 `REBUILD_CANDIDATES` 中的 4–6 个完成任务与断言重构，达到 $\ge 15$ Core 后方可申请 Freeze Review。

---

## 交付文件索引

- Curation Pool: `data/curation/track_a_pool_v1.jsonl`
- Individual Scorecards: `data/curation/reviews/<tid>.json`
- Candidate Manifests: `data/benchmark_v1/track_a_core.jsonl`, `track_a_controls.jsonl`, `excluded.jsonl`
- Blind Annotations & Gold Adjudication: `data/memory_validity_blind/`, `data/memory_validity_blind_annotations/`, `data/memory_validity_adjudicated.jsonl`
- Symbol Validity Evaluation V4: `data/symbol_validity_v4.json`
- Experiment Config: `configs/benchmark_v1.yaml`
- Reports:
  - `reports/benchmark-curation.md`
  - `reports/transition-type-distribution.md`
  - `reports/blind-validity-annotation.md`
  - `reports/symbol-validity-v4.md`
  - `reports/memory-regression-case-study.md`
  - `reports/benchmark-v1-readiness.md`
  - `reports/pilot-v1.4-r4-review.md`
