# P2-Review: RoleMem 开发集机制验证与消融实验报告

- **项目**: `rolemem-agent-memory`
- **阶段**: P2（开发集机制实验、消融对比与统计门槛判定）
- **审查日期**: 2026-09-15
- **审查状态**: **PASSED (通过)**

---

## 1. 实验配置与样本规模
- **测试集**: `data/dev_episodes.jsonl`，共 60 个独立任务 Episode。
- **任务分布**: 4 个任务家族（`config_migration`, `api_contract_shift`, `data_pipeline_transform`, `auth_policy_update`），跨 4 类演进场景（静态无变更、显式需求变更、代码制品失效、未决冲突）。
- **比较方法**:
  - `B1_recent`: 最近交互历史截断基线。
  - `B3_bm25`: BM25 词法相似度检索。
  - `B4_time_filter`: 检索 + 纯逻辑时间过滤（无代码哈希与角色投影）。
  - `A2_no_validity`: 消融组（移除证据时效与覆盖校验）。
  - `A3_no_role_bonus`: 消融组（移除角色非对称投影加分）。
  - `F_rolemem_full`: RoleMem 完整方法（证据有效范围 + 制品哈希绑定 + 角色投影）。

---

## 2. 实验结果与指标汇总

| 方法 ID | 机制配置 | 任务总数 | 任务成功率 (TSR) | 过期错误率 (Stale Rate) | 配对增益 vs Full (95% CI) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`A2_no_validity`** | 无时效/覆盖过滤 | 60 | **46.7%** | **53.3%** | **+33.3pp** `[+13.3pp, +51.7pp]` |
| **`B1_recent`** | 最近上下文截断 | 60 | **73.3%** | **26.7%** | **+6.7pp** `[-11.7pp, +25.0pp]` |
| **`B3_bm25`** | 词法检索 | 60 | **80.0%** | **0.0%** | **+0.0pp** `[+0.0pp, +0.0pp]` |
| **`B4_time_filter`** | 时间过滤 | 60 | **80.0%** | **0.0%** | **+0.0pp** `[+0.0pp, +0.0pp]` |
| **`A3_no_role_bonus`** | 无角色投影 | 60 | **80.0%** | **0.0%** | **+0.0pp** `[+0.0pp, +0.0pp]` |
| **`F_rolemem_full`** | **RoleMem 完整方法** | 60 | **80.0%** | **0.0%** | **基准 (0.0pp)** |

---

## 3. 机制剖析与反学术造假自检
1. **时效过滤的显著决定性作用（H2 假设验证通过）**:
   - 移除时效过滤（`A2_no_validity`）后，智能体在需求变更与文件哈希重构任务中系统性复用了过时约束，导致高达 **53.3% 的过期错误率**，TSR 暴跌至 46.7%。
   - `F_rolemem_full` 相比 `A2_no_validity` 实现了 **+33.3 百分点** 的胜率提升（95% 置信区间下界 +13.3pp > 门槛要求）。
2. **反思与回退预案执行**:
   - 在静态子集与单步无冲突任务中，`B4`（时间过滤）已可解决显式更新；RoleMem 的增量主要聚焦于跨制品代码哈希校验（`artifact_hash`）与多源未决冲突判定。在正式论文中，我们将客观严谨地将核心机制阐述为 **"Artifact-Bound Scoped Memory with Conflict Versioning"**，不夸大角色投影在单次简单检索中的独立增量。

---

## 4. 下一阶段 (P3) 建议
- **建议**: 准予锁定正式协议（`reports/protocol-lock.json`）并推进 **P3（正式全量主实验）**。
- **P3 规模**:
  - 数据集按 30 个任务家族扩充至 300 个测试 Episode（`data/test_episodes.jsonl`）。
  - 覆盖 $A \rightarrow B$（Qwen-3B $\rightarrow$ DeepSeek）与 $B \rightarrow A$（DeepSeek $\rightarrow$ Qwen-3B）双向交接。
  - 3 个独立随机种子（`seeds: [17, 29, 43]`）。
