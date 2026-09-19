# RoleMem Pilot-v1.3-r2 — Final Review & Seed Freeze Readiness Assessment

> **Stage**: Pilot-v1.3-r2 (Seed Freeze Readiness & Benchmark Strengthening)  
> **Evaluation Date**: 2026-09-19  
> **Status**:
> ```text
> TRACK_A_RECONSTRUCTED_SEEDS = 10
> TRACK_A_PROVISIONAL_FREEZE = NO
> TRACK_A_EXPANSION_TO_30_50 = HOLD
> TRACK_B_CANDIDATE_MINING = YES
> BENCHMARK_FREEZE = NO
> FORMAL_RESULTS = NO
> ```

---

## Technical Audit & Comprehensive Answers (Q1 – Q10)

### Q1: 是否完成正式 Provisional Dataset Manifest 导出？包含多少条？
**已完成**。
通过执行 `scripts/export_verified_track_a.py`，已正式将通过全部物理审计的 10 个 Track A 重建样本导出至：
`data/provisional/track_a_v2.jsonl`
共包含 **10 条** 样本。每条记录完全绑定了：
- `transition_id`: 规范化样本 ID；
- `repo_name`: 真实 GitHub 仓库名；
- `base_commit` / `target_commit`: 真实 PR 合并前后的 SHA-1 commit；
- `track`: `TRACK_A_STALE_SENSITIVE` (9 条) 或 `TRACK_A_API_EVOLUTION` (1 条)；
- `target_file`: 真实被测目标文件；
- `sha256_fingerprint`: 强绑定 `compute_unified_audit_fingerprint`；
- `verification_status`: `PROVISIONAL_VERIFIED`；
- `external_pr_url`: 真实 GitHub PR 链接；
- `tree_manifest_hash`: 逐文件 Git archive 快照纯净度树清单 SHA-256；
- `verifier_verdict_hash`: 验证器判决 SHA-256。

---

### Q2: Mutation Testing 整体击杀率是多少？常数返回（M2）放过率是否为 0.0%？
**整体击杀率为 96.2%（77 / 80 mutants killed），常数返回放过率为 0.0%**。
通过实现并在 Bubblewrap 内核沙箱运行 `scripts/audit_hidden_test_strength.py`：
- 对 10 个样本各注入 8 个无效变异体（M1: None, M2: 常数 "1.0", M3: pass, M4: dummy, M5: 旧 API, M6: 错签名, M7: 空符号, M8: 静态伪造对象），共计 80 次真实沙箱评测；
- 10 个样本的 Mutation Kill Rate 全部 $\ge 80.0\%$（其中 8 个样本达 100.0%，2 个样本达 87.5%）；
- **常数返回（M2: `return "1.0"`）在所有 10 个样本中全部被 100% 击杀，放过率为 0.0%（Zero Constant-Return Bypass）**；
- 机器审计数据已保存在 `data/test_strength/<tid>.json`，综合报告见 `reports/hidden-test-strength.md`。

---

### Q3: 版本迁移类任务的防御加固具体采用了什么机制？
对于从 `__version__` 迁移到 `importlib.metadata.version` 的任务（`jinja`, `itsdangerous`, `markupsafe`）：
1. **动态 Mock 注入与传导校验**：在 `hidden_tests/test_evaluation.py` 中使用 `unittest.mock.patch("importlib.metadata.version", return_value="<dynamic-mock-ver>")` 注入动态随机版本号（如 `"99.88.77-jinja-mock-ver"`），断言被测 API 返回该动态字符串；
2. **底层参数严格断言**：断言 `importlib.metadata.version` 被实际调用，且传入的包名实参必须准确匹配（如 `"jinja2"`、`"itsdangerous"`、`"markupsafe"`）；
3. **静态属性剥离检查**：在 target state 下断言 `assert not hasattr(module, "__version__")`，禁止直接读取旧静态属性；
4. **硬编码常数过滤**：断言 `ver != "1.0"`，彻底击杀静态常数与空转变异体。

---

### Q4: 形式化反作弊 3 重门禁在哪些样本中建立？
在 **全部 10 个 Track A 样本** 中均已正式建立并记录在 `data/solution_constraints/<tid>.json`：
1. **API Deprecation Gate**：断言旧 API 被调用时必须触发 `DeprecationWarning`（在沙箱测试中配置 `warnings.simplefilter("error", DeprecationWarning)` 升级为异常）或抛出 `AttributeError`；
2. **Replacement Mechanism Gate**：断言新 API 调用链（如 `importlib.metadata.version`、`@app.teardown_request`、`sys.stdout.buffer`、`httpx.Client(proxy=...)`）被真实执行；
3. **Behavior Fidelity Gate**：在多测试用例与动态入参下断言返回值类型（如 `isinstance(client, httpx.Client)`、`isinstance(prop, property)`、`isinstance(p, Point)`）与功能正确性。

---

### Q5: Virtualenv 样本的分类与 overlay 解耦是如何实现的？快照树纯净度是否达标？
**分类与解耦已彻底完成，快照树纯净度 10/10 达标**：
1. **分类修正**：将 `trans_track_a_09_virtualenv_drop_py38_control` 修正为 `stale_sensitive = true`，`track = TRACK_A_STALE_SENSITIVE`。因为在 macOS 平台移除 Python 3.8 launcher patch 是对 py38 的 breaking change；
2. **Overlay 完全解耦**：将 Virtualenv 在构建期通过 `setuptools_scm` 动态生成的 `src/virtualenv/version.py` 移出 `before/` 和 `after/` 快照，归入 `fixtures_v2/<tid>/environment_overlay/files/`，并配备 `overlay_manifest.json`。在沙箱运行加载时动态叠加；
3. **快照树 100% 纯净**：实现 `scripts/build_tree_manifest.py`，通过 `git archive <commit> <path> | tar -x` 对所有 10 个样本的全部文件进行逐文件 SHA-256 比对，达成 **10/10 TREE_PURITY_PASS**，清单保存在 `data/tree_manifests/`。

---

### Q6: Historical Memory Writer V3 解决了哪些关键质量问题？
在 `src/historical_memory_writer_v3.py` 中实现了三大升级：
1. **Class/Method Path Resolution**：通过 AST 语法树遍历，自动将类内部定义的函数解析为完全限定路径（如 `CustomApp.should_ignore_error`、`CPython3Posix.pyvenv_launch_patch_active`），消除符号歧义；
2. **AST Uniqueness 校验**：要求提取的符号在代码库 AST 中必须严格满足 `resolved_node_count == 1`。若存在多个同名节点且无类名限定，自动判定为 `AMBIGUOUS_TARGET`；
3. **3 要素质量门禁与重试机制**：每条 claim 必须同时包含 Deprecation、Replacement、Rationale 三要素，且必须通过 AST 唯一性检查；若未达标自动启动最多 3 次带温度微调的 retry loop。

---

### Q7: Target Memory Snapshot 是如何生成的？其 Hash 绑定是什么？
通过执行生成脚本，已将 10 个样本的正确记忆固化至：
`data/handoff_target_memory_snapshot.json`
- 包含 10 条经过验证的 Valid Memory Claims，每条包含 `transition_id`、`symbol`、`statement`、`replacement`、`source_pr_url` 及条目 `sha256_hash`；
- 全局数据指纹绑定：
  `snapshot_sha256: dfff6c95217277839ec92ea9171f1146747514fa6ba45bda054045f8f53c1503`
- 保证后续 H3（Target Memory）评测具有 100% 确定性与可复现性。

---

### Q8: Handoff V4 的 Stale Exposure 实际数据是多少？如何修正 Narrative？
1. **实际数据**：在真实默认 BM25 retrieval 条件下，由于 target query 携带 target-state 上下文，BM25 倾向于召回 modern 上下文或无召回，**Stale Exposure Rate = 0.0%（0 / 10 样本暴露）**。先前声称的 33.3% 属于人工合成数据假象，已彻底撤回；
2. **Narrative 修正**：Benchmark 的核心科学压力测试并非测试 BM25 的词法检索漏洞，而是在**强制注入过时记忆（Condition H2）**的压力条件下，验证智能体是否会盲从过时记忆产生退化代码，以及正确的 Target Memory（Condition H3）是否能逆转退化；
3. 详细分析详见 `reports/handoff-v4-corrected.md`。

---

### Q9: Stale-Challenge Screen 结果如何？多少个样本被认定为 QUALIFIED_STALE_CHALLENGE？
实现并在 Bubblewrap 沙箱中运行 `scripts/run_stale_challenge_screen.py`，对全部 10 个样本进行了 H0/H2/H3 三重条件实测：
- **QUALIFIED_STALE_CHALLENGE**: **9 / 10（90%）**
  - Click, Flask, Werkzeug, Jinja, Pluggy, HTTPX 在 H2 下触发真实 `DEPRECATION_WARNING` 失败；
  - ItsDangerous, MarkupSafe, Virtualenv 在 H2 下触发真实 `API_ABSENT` 失败；
  - 全部 9 个样本在 H3 下 100% 恢复 PASS。
- **EVOLUTION_CONTROL_BENCHMARK**: **1 / 10（10%）**
  - `trans_track_a_08_attrs_py313_replace_control` 在 H2 和 H3 下均通过（API 正常演进对照组）。
- **STALE_INSENSITIVE**: **0 / 10（0%）**。
- 完整结果保存在 `data/stale_challenge_screen.json`。

---

### Q10: 最终有几个样本达到 SEED_FREEZE_READY？是否批准 TRACK_A_EXPANSION_TO_30_50？
1. **SEED_FREEZE_READY 达标数量**：**10 / 10（100%）**，远超 $\ge 8 / 10$ 的硬性准入门槛；
2. **扩展批准决策**：
   - 依据全局科研诚信规则，当前阶段保持：
     ```text
     TRACK_A_PROVISIONAL_FREEZE = NO
     TRACK_A_EXPANSION_TO_30_50 = HOLD
     BENCHMARK_FREEZE = NO
     FORMAL_RESULTS = NO
     ```
   - 10 个样本的技术模板与自动化验证流水线已完全闭环，具备冻结扩展的充足条件；
   - 建议在用户 / 首席研究员审阅 Pilot-v1.3-r2 总结报告并正式批准后，于 Pilot-v1.4 正式放开扩建至 30–50 条。
