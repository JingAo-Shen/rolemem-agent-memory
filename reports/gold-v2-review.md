# Pilot-v1.2b Gold V2 Transition Review & Benchmark Status Report

## Executive Summary

- **Evaluation Stage**: Pilot-v1.2b Repository-State Grounding & Gold Transition Correction
- **Benchmark Freeze**: **NO (STRICTLY SUSPENDED)**
- **Audit Decision**: **8 ACCEPTED (PROVISIONAL_GOLD_V2), 2 NEEDS_ENV_RECONSTRUCTION**
- **Reviewer Type**: `automated_self_review`
- **Review Status**: `AUTO_REVIEWED`
- **Peer Review Status**: **PENDING INDEPENDENT HUMAN / PEER AUDIT**
- **Core Milestone**: Completely decoupled benchmark evaluation from synthetic templates. All 8 accepted tasks are now 100% grounded in authentic Git repository commit states and execute inside kernel-isolated Bubblewrap sandboxes.

---

## 1. Review Governance & Transparency Notice

> [!WARNING]
> **PROVISIONAL STATUS DECLARATION**
> 
> The transitions in `data/gold/gold_transitions_v2.jsonl` are classified strictly as **`PROVISIONAL_GOLD_V2`**.
> - Formal Benchmark Freeze is **STRICTLY PROHIBITED** at this stage.
> - No formal claim of model superiority (e.g. "RoleMem outperforms Baseline by X%") may be asserted in publications or public reports based on this dataset.
> - The review records in `data/reviewed/review_records_v2.jsonl` were conducted via automated self-review (`reviewer_type: automated_self_review`). Formal peer review by external contributors remains required before benchmark freezing.

---

## 2. Layered Dataset Architecture

The project now maintains three clean, traceable data layers under `data/`:

```text
data/
├── verified/
│   └── auto_verified_v2.jsonl         # All 10 candidates with Git commit, AST causality, and sandbox control results
├── reviewed/
│   └── review_records_v2.jsonl        # 10 formal review records (decision: ACCEPT or NEEDS_ENV_RECONSTRUCTION)
└── gold/
    ├── gold_transitions.jsonl         # Historical 10 candidates (marked PROVISIONAL_GOLD)
    └── gold_transitions_v2.jsonl      # Pinned 8 accepted transitions (PROVISIONAL_GOLD_V2)
```

---

## 3. Transition Decisions and Audit Summary

### 3.1 Accepted Transitions (8 / 10)

All 8 accepted transitions satisfy the following 4 hard gates:
1. All 4 commits (`base`, `history`, `transition`, `target`) verified in local Git object database (`git cat-file -e`).
2. AST causality verified change in window with non-empty diff and targeted symbol alteration.
3. Bubblewrap sandbox execution of `stale_solution.py` confirmed 100% failure / deprecation detection.
4. Bubblewrap sandbox execution of `valid_solution.py` confirmed 100% pass with zero warnings.

| Transition ID | Track | Repository | Target File | Target Symbol | Sandbox Stale Control | Sandbox Valid Control | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `trans_gold_werkzeug_01_cached_property` | Track A | `pallets/werkzeug` | `property_helper.py` | `reset_cached_attribute` | **FAIL** (`DeprecationWarning`) | **PASS** | **ACCEPT** |
| `trans_gold_werkzeug_02_environ_properties` | Track A | `pallets/werkzeug` | `wsgi_helper.py` | `extract_wsgi_header` | **FAIL** (`DeprecationWarning`) | **PASS** | **ACCEPT** |
| `trans_gold_flask_02_should_ignore_error` | Track B | `pallets/flask` | `error_policy.py` | `configure_error_policy` | **FAIL** (`DeprecationWarning`) | **PASS** | **ACCEPT** |
| `trans_gold_urllib3_02_empty_allowed_methods` | Track B | `urllib3/urllib3` | `retry_factory.py` | `create_all_verbs_retry` | **FAIL** (`FutureWarning`) | **PASS** | **ACCEPT** |
| `trans_gold_click_01_option_parser` | Track A | `pallets/click` | `cli_helper.py` | `parse_command_args` | **FAIL** (`UserWarning`) | **PASS** | **ACCEPT** |
| `trans_gold_click_02_isolated_filesystem` | Track B | `pallets/click` | `test_isolation.py` | `run_in_isolated_dir` | **FAIL** (`DeprecationWarning`) | **PASS** | **ACCEPT** |
| `trans_gold_requests_01_tls_context_adapter` | Track A | `psf/requests` | `adapter_helper.py` | `get_adapter_connection` | **FAIL** (`DeprecationWarning`) | **PASS** | **ACCEPT** |
| `trans_gold_requests_02_pool_key_overrides` | Track C | `psf/requests` | `pool_config.py` | `get_pool_key_attributes` | **FAIL** (Assertion on tuple) | **PASS** | **ACCEPT** |

---

### 3.2 Excluded Transitions Requiring Environment Reconstruction (2 / 10)

| Transition ID | Track | Repository | Root Cause for Exclusion | Action Taken |
| :--- | :--- | :--- | :--- | :--- |
| `trans_gold_flask_01_context_stack_removal` | Track A | `pallets/flask` | Flask 2.2 requires Werkzeug < 3.0 (imports `url_quote` from `werkzeug.urls`). The host environment contains Werkzeug 3.2 where `url_quote` was deprecated/removed. | Marked `NEEDS_ENV_RECONSTRUCTION`. Excluded from `gold_transitions_v2.jsonl` until dedicated pin-locked venvs are provisioned. |
| `trans_gold_urllib3_01_retry_allowed_methods` | Track A | `urllib3/urllib3` | Urllib3 1.26 bundled legacy `six 1.12.0` (from 2020), whose dynamic `sys.meta_path` import hooks are incompatible with Python 3.13. | Marked `NEEDS_ENV_RECONSTRUCTION`. Excluded from `gold_transitions_v2.jsonl` until Python 3.9/3.10 sandbox runner is provisioned. |

> [!NOTE]
> **Scientific Integrity Decision**: Neither failed transition was "fixed" using synthetic shims or artificial mocks. They were excluded honestly and transparently, adhering to the principle that a benchmark suite must report true counts rather than forcing an arbitrary quota of 10 items.

---

## 4. Answers to the 7 Mandatory Audit Questions

### Q1: 10 条 Provisional Gold 中，经 repository-state + causality audit 后，最终几条通过？
- **最终 8 条完全通过**。全部 10 条在 Git commit 和 AST 因果性层面均通过（CAUSALITY_PASS），但在真实沙箱控制组执行测试中，8 条完全通过，2 条因宿主 Python 3.13 与历史包依赖冲突标记为 `NEEDS_ENV_RECONSTRUCTION`。

### Q2: 几条因 PR/语义错误被删除或修改？具体原因？
- **4 条修改，0 条删除**：
  1. `trans_gold_werkzeug_01_cached_property`: PR 编号更正为 #2084（原 #2085 为相关讨论 issue）；修正 base_commit 为 PR 合并前的真实 commit `25ca9cd...`。
  2. `trans_gold_werkzeug_02_environ_properties`: 修正 `changed_files` 为实际的 `src/werkzeug/utils.py` 和 `wrappers/request.py`（原路径 `sansio/utils.py` 在该 commit 上不存在）。
  3. `trans_gold_requests_02_pool_key_overrides`: 修正 `changed_symbols` 为真实新增的 `HTTPAdapter.build_connection_pool_key_attributes`。
  4. `trans_gold_flask_02_should_ignore_error`: 修正语义约定为 `@app.teardown_request`。

### Q3: 几条真实 repository snapshots 能在 sandbox 内成功重建并运行 pytest？
- **全部 10 条均成功提取真实 Git tree 源码**。
- 在当前宿主沙箱环境下，**8 条** 成功执行 pytest 并完成断言；2 条触发底层 Python 3.13 / Werkzeug 3.2 依赖缺失错误。

### Q4: 真实 repo snapshot 下，stale control 是否全部 FAIL？
- **是**。在 8 条合格 fixture 中，`stale_solution.py` 100% 触发失败或被告警捕获（Werkzeug `DeprecationWarning`、Click `UserWarning`、urllib3 `FutureWarning`、Requests `DeprecationWarning`）。

### Q5: 真实 repo snapshot 下，valid control 是否全部 PASS？
- **是**。在 8 条合格 fixture 中，`valid_solution.py` 100% 成功通过沙箱内 hidden pytest 测试，无任何告警或异常。

### Q6: Qwen2.5-Coder-7B 真实 E2E 验证是否成功？输出指标为何？
- **是**。端到端验证执行成功，完整遥测日志记录于 `reports/real-7b-e2e-smoke.md`（及 `reports/real-0.5b-e2e-smoke.md`），验证了 `Memory Retrieval -> LLM Generation -> AST Stale Analysis -> Bubblewrap Sandbox -> Hidden Pytest -> Telemetry` 全链路无断点。

### Q7: 当前是否达到 BENCHMARK FREEZE 标准？
- **NO (绝对未达到)**。
  - 当前合格样本数为 8 条，未扩充至 40–80 条标准规模；
  - 仍有 2 条历史任务因跨版本环境不匹配需要虚拟环境隔离；
  - 评审状态仍为 `automated_self_review`，未经过独立第三方或人工双盲评审。
  - 严格保持 `PROVISIONAL_GOLD_V2`，继续禁止冻结基准与生成论文正式结论。
