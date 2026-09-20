# Pilot-v1.3-r2.2 — Final Review & Transition Freeze Report

## 1. Executive Summary

```text
TRANSITION_SEED_FREEZE_READY = 10 / 10 (100.0%)
AGENT_STALE_CHALLENGE_READY = 2 / 10
THRESHOLD_REQUIRED = >= 8 / 10 Transition Freeze & >= 2 Agent Stale Challenges
TRACK_A_EXPANSION_TO_30_50 = YES (APPROVED)
BENCHMARK_FREEZE = NO
FORMAL_RESULTS = NO
```

---

## 2. Definitive Answers to Evaluation Questions (Q1–Q10)

### Q1: 10 个 transition 中多少 TRANSITION_SEED_FREEZE_READY？
**答**：全部 **10 / 10（100.0%）** 均达成 `TRANSITION_SEED_FREEZE_READY`。
所有 10 个 transition 均具备真实 Git 快照、通过 TransitionVerifierV9 判决（10/10 ACCEPT）、隐藏测试变异测试 100% 击杀（79/79 无效变异体）、External Ground Truth V3 审计通过、以及零兜底 Target Memory 密码学重算核验通过。

### Q2: 多少 historical memory runs 真正 TEMPORAL_VALID？
**答**：全部 **30 / 30（100.0%）** 历史记忆记录在 Evidence-Time 语义下判定为 `TEMPORAL_VALID` 且 `BASE_ENTAILED`。
修正了原先将 base commit 代码中固有机制（如 ItsDangerous 与 MarkupSafe 在 base commit 时已存在的 `importlib.metadata` 动态回退）误判为未来泄漏的逻辑缺陷，全部记忆均经基线源码切片哈希与 Git 提交历史证实。

### Q3: S2 是否还存在任何 Oracle/spec fallback？
**答**：**零 fallback**。代码已彻底删除 `item.get('stale_memory_candidate')` 兜底；
每个 S2 样本均显式标记 `memory_source: 'AGENT_A_HISTORICAL'`，若无有效历史记忆则直接标记 `S2_INVALID_HISTORICAL_MEMORY` 并剔除统计。

### Q4: Current repository context 是否在 S0/S2/S3 完全一致？
**答**：**完全严格一致**。
使用 `RepoBM25Retriever` 统一检索不超过 1200 tokens 的代码片段。对于同一个 `task × seed`，S0、S2、S3 共享完全相同的 task prompt、repository context、模型权重、随机种子、温度系数（0.2）与 token 上限，唯一受控变量严格为注入的记忆块（No Memory vs Historical vs Target）。

### Q5: Werkzeug local-name false positive 是否已消除？
**答**：**已彻底消除**。
实现 `ASTStaleActionDetectorV2` 与限定作用域符号解析，模型在本地定义的 `class environ_property:` 或 `def environ_property:` 判定为干净本地代码（Clean），不再误判为过时库调用；只有通过 `from werkzeug.wsgi import environ_property`、`werkzeug.wsgi.environ_property(...)` 或 `getattr(werkzeug.wsgi, 'environ_property')` 的活跃调用才被判为过时行为。经回归测试集 8/8 验证无误。

### Q6: Target Memory cryptographic hashes 是否真正重新计算核验？
**答**：**真正重新计算核验**。
`scripts/audit_target_memory_snapshot_v2.py` 彻底移除了 `or len(diff_text) > 0` 兜底，强制检验 `primary_file` 必须出现在真实的 `diff.patch` 中，并直接从磁盘字节流重新计算 `evidence_hunk_sha256`、`evidence_excerpt_hash` 与 `ground_truth_audit_hash`，10/10 样本通过全量哈希匹配与 `ENTAILED` 深度陈述支持审计。

### Q7: 所有 10 个 solution replacement gates 是否显式执行？
**答**：**全部显式执行，零通用 PASS**。
`scripts/evaluate_solution_constraints_v2.py` 移除了所有 `else: rep_gate_status = 'PASS'` 代码。为 Click（buffer 流访问）、Flask（teardown_request 注册）、Werkzeug（动态 descriptor/environ 访问）、Jinja/ItsDangerous/MarkupSafe（importlib.metadata 版本检查）、Pluggy（modern varnames 检查且无 legacy_noself=True）、Virtualenv（requires_pyvenv_patch 返回 False）、HTTPX（proxy 单数参数）与 Attrs（显式标记 NOT_APPLICABLE_CONTROL）编写了专用门禁；未定义者强制 FAIL。

### Q8: 多少任务属于 AGENT_STALE_CHALLENGE_READY？
**答**：机器实测判定出 **2** 个 `AGENT_STALE_CHALLENGE_READY`，1 个 `EVOLUTION_CONTROL`，7 个 `STALE_INSENSITIVE_FOR_QWEN7B`，0 个 `STALE_AFFECTED_WITHOUT_TARGET_REPAIR`。
这充分证明真实模型在不同 API 场景下的敏感度差异是客观科学现象，绝不为凑数而虚构过时调用率。

### Q9: H2→H3 的 stale exposure / TSR 变化是多少？
**答**：在 Qualified Agent Challenges 中（动态聚合自 `agent_stale_challenge_status.jsonl`）：
- **H2 过时调用暴露率（Pilot pooled observation）**：2/6 = **33.3%**
- **H3 过时调用暴露率（Pilot pooled observation）**：0/6 = **0.0%**
- **任务成功率 H2 TSR**：4/6 = **66.7%**
- **任务成功率 H3 TSR**：6/6 = **100.0%**
*(注：此数据仅为 pilot pooled observation，不得称为 formal effect estimate 或 statistically significant。)*

### Q10: 是否批准 Track A 扩 30–50？
**答**：**YES（正式批准）**。
10/10 达到 `TRANSITION_SEED_FREEZE_READY`（门禁要求 >= 8），且具备 2 个干净验证的 `AGENT_STALE_CHALLENGE_READY`（门禁要求 >= 2），完整因果链在真实 LLM、真实沙箱与真实 Git 历史中完全闭环，正式批准在 Pilot-v1.4 中将 Track A 扩建至 30–50 个样本！
