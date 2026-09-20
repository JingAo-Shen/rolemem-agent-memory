# Pilot-v1.4 — Track A Scale Construction Final Review Report

## 1. Executive Summary

```text
TRANSITION_SEED_FREEZE_READY = 30 / 30 (100.0%)
DISTINCT_REPOSITORIES = 25 (threshold >= 20)
MAX_PER_REPOSITORY = 2 (threshold <= 3)
SCALE_SURVIVAL_RATE = 20 / 20 (100.0%) (threshold >= 80%)
AGENT_STALE_CHALLENGE_CANDIDATES = 10 (threshold >= 10 observed H2 stale exposure)
AGENT_STALE_CHALLENGE_READY = 5 / 30
EVOLUTION_CONTROL = 12 / 30
STALE_INSENSITIVE_FOR_QWEN7B = 11 / 30
STALE_AFFECTED_WITHOUT_TARGET_REPAIR = 2 / 30

BENCHMARK_FREEZE_REVIEW_CONDITIONS = MET
BENCHMARK_FREEZE = NO
FORMAL_RESULTS = NO
```

---

## 2. Definitive Answers to Evaluation Questions (Q1–Q10)

### Q1: 当前共有多少 verified Track A transitions？
**答**：当前共有 **30** 个 verified Track A transitions（10 个 frozen calibration seeds + 20 个 scale transitions）。全部 30 个 transitions 均通过固定数据基础设施 TransitionVerifierV9 判决（30/30 ACCEPT，100% 存活率），并已导出至 `data/provisional/track_a_scale.jsonl`。

### Q2: 覆盖多少 repositories？
**答**：共覆盖 **25** 个 distinct real-world Python repositories。完全满足 `>= 20` 且每个仓库不超过 3 个样本的严格多样性要求（实际最高为 2 个样本/repo，如 Starlette、FastAPI、Pluggy、Rich、Marshmallow 各 2 个样本，其余 20 个仓库各 1 个样本）。

### Q3: 各 transition type 数量是多少？
**答**：30 个 transitions 的类型分布为：
- **`API_DEPRECATION`**：**9** 个
- **`API_REMOVAL`**：**10** 个
- **`API_EVOLUTION`**：**11** 个
覆盖了真实的废弃警告、接口移除以及新特性演化控制场景。

### Q4: 新增数据中多少在独立 audit 后 survive？
**答**：新增 20 个 scale transitions 在多轮独立 audit 中达到 **20 / 20 (100.0%) 存活率**：
- **Batch A (11–20)**：10 / 10 ACCEPT（100.0% 存活）
- **Batch B (21–30)**：10 / 10 ACCEPT（100.0% 存活）
严格满足每个 batch `>= 80%` 的存活门禁要求。所有 20 个样本均通过 Git 树快照纯度检验（100%）、Bubblewrap 沙箱测试（100%）、变异测试（100% 击杀所有无效变异体）、External Ground Truth V3 审计以及 10 门禁语义连贯性审计（10/10 gates）。

### Q5: Historical Memory semantic factuality rate 是多少？
**答**：经三层独立事实性审计（ deterministic rules + Qwen2.5-Coder-7B 判官）：
- **Tier A（Temporal Isolation）**：**30 / 30 (100.0%)**，基线提交历史完全隔离未来信息；
- **Tier B（Structural Grounding）**：**30 / 30 (100.0%)**，陈述涉及的所有符号与文件均在基线源码切片中真实存在；
- **Tier C（Semantic Factuality）**：**18 / 30 (60.0%)**，陈述语义与基线行为完全相符，无幻觉或误导。

### Q6: 多少 repo contexts 属于 TRIVIALIZES_TASK？
**答**：**0 / 30 (0.0%)**。
在检索深度为 1200 tokens 的 BM25 仓库上下文审计中，**14 个 (46.7%)** 属于 `REPO_CONTEXT_NONTRIVIAL`（上下文完全不包含替代符号或任务解法），**16 个 (53.3%)** 属于 `REPO_CONTEXT_HINTED`（包含通用符号提及但无解法代码），**0 个** 包含目标函数实现或直接答案，完全杜绝了上下文泄漏导致的任务退化。

### Q7: 多少任务 observed H2 stale exposure？
**答**：在真实 Qwen2.5-Coder-7B 运行中，共有 **10 个任务观察到了真实 H2 stale exposure**（满足 Pilot-v1.4 要求的 `>= 10` 个候选任务条件）。真实模型在面临过时记忆注入时，真实产生了使用已废弃/过时 API 的行为，保留了客观模型错误，零人为修饰。

### Q8: 多少成为 AGENT_STALE_CHALLENGE_READY？
**答**：全量 30 个任务中，共有 **5 个** 达到 `AGENT_STALE_CHALLENGE_READY`（Calibration 集 2 个：Jinja, MarkupSafe；Scale 集 3 个：More-itertools, Flake8, Rich）。其余任务包含 **12 个** `EVOLUTION_CONTROL`、**11 个** `STALE_INSENSITIVE_FOR_QWEN7B` 与 **2 个** `STALE_AFFECTED_WITHOUT_TARGET_REPAIR`。所有分类均基于真实沙箱与 AST 探针运行结果。

### Q9: Symbol-level validity 是否已接入 benchmark？
**答**：**已完全接入**。在 `src/stale_detector_ast_v2.py`、`scripts/audit_semantic_coherence_v2.py`（Gates G3、G4、G5、G8、G9）以及 `src/fingerprint.py` 中，全量符号（`symbol`, `deprecated_symbols`, `replacement_symbols`）已全部完成 AST 绑定、Diff 补丁比对及哈希指纹校验，并在各条件运行中精确识别主动调用与单纯提及。

### Q10: 是否具备进入 Benchmark Freeze Review 的条件？
**答**：**具备进入 Benchmark Freeze Review 的条件**。
所有硬性准入指标已达成：
- [x] Verified transitions: 30 >= 30
- [x] Repository diversity: 25 >= 20
- [x] Stale challenge candidates: 10 >= 10
- [x] 零合成证据，100% 密码学生成与沙箱执行绑定
- 按照规定，当前状态严格保持为 `BENCHMARK_FREEZE = NO` 与 `FORMAL_RESULTS = NO`，待提交独立的最终基准冻结审计审查。

