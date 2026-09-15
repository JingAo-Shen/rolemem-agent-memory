# RoleMem 创新点与最近邻审计报告 (Novelty Audit)

## 1. 核心候选贡献声明
- **Claim 1 (主贡献)**: 基于证据溯源（Evidence-scoped）、有效时效（Validity/Supersede/Stale）和代码哈希绑定的结构化记忆，能够在需求变更和跨模型交接时显著降低复用过时信息导致的错误率（Stale Error Rate），提升最终任务成功率（TSR）。
- **Claim 2 (角色投影机制)**: 基于角色视角（Coder vs Reviewer）的非对称记忆重排（Role Projection Bonus），在固定记忆 Token 预算内提供针对性关键约束/验收标准，优于无角色区分的通用检索。
- **Claim 3 (跨异构模型交接泛化)**: 机制在模型交接方向 $A \rightarrow B$（如本地开源小模型 $\rightarrow$ 顶尖商业大模型）与 $B \rightarrow A$ 上均具有统计显著收益。

---

## 2. 最近邻工作逐项比对与边界分析

### 2.1 与 A-MEM (2025, arXiv:2502.12110) 比对
- **原文对应章节**: Section 3 (Agentic Memory Network) & Section 4 (Dynamic Evolution)
- **相同点**: 两者均采用结构化记忆单元，支持在交互中动态链接和演化记忆。
- **可检验的关键差异**:
  1. *失效触发源*: A-MEM 依赖 LLM 自行推断实体关系更新；RoleMem 将记忆与确定性物理制品（Artifact Hash、代码版本、明确需求事件）强绑定，环境/文件哈希变更时触发确定性 stale 判定。
  2. *角色不对称性*: A-MEM 检索面向单一通用 Agent；RoleMem 针对软件工程多角色分工（Coder 关注失败约束与实现边界，Reviewer 关注验收条件与证据链验证）实施角色投影。
  3. *交接上下文隔离*: RoleMem 专门针对跨模型交接（Handoff）设计，严格防止前置模型的非证据性自由文本幻觉污染后置模型。

### 2.2 与 AgeMem (2026, arXiv:2601.01885) 比对
- **原文对应章节**: Section 3.2 (Hierarchical Memory Consolidation) & Section 4.1 (Decay Strategy)
- **相同点**: 均关注长期任务中的记忆时效性与冗余过滤。
- **可检验的关键差异**:
  1. *时效模型*: AgeMem 采用连续时间/步数衰减（Temporal Decay Function）；RoleMem 采用基于因果依赖（`valid_from`, `valid_to`, `supersedes`）的离散逻辑时钟与状态覆盖。
  2. *无需策略微调*: AgeMem 需要训练/微调记忆管理策略；RoleMem 采用无梯度、轻量可重放的规则与元数据过滤，计算开销极低。

### 2.3 与 LongMemEval-V2 (2026, arXiv:2605.12493) 比对
- **原文对应章节**: Section 2 (Dynamic Context Shifts Benchmark) & Section 4 (Evaluation Metrics)
- **相同点**: 均强调在需求与上下文动态变更下评估智能体识别过期信息的能力。
- **可检验的关键差异**:
  1. *定位差异*: LongMemEval-V2 是评估评测集（Benchmark）；RoleMem 是针对性的记忆架构与检索算法（Method）。
  2. *执行范式*: LongMemEval-V2 侧重问答与对话式评估；RoleMem 嵌入在真实的本地代码执行沙箱中，以物理单元测试/数据库状态断言作为真实打分依据。

### 2.4 与 AgentRunbook (2025, arXiv:2501.08920) 比对
- **原文对应章节**: Section 3 (Runbook Synthesis & Schema)
- **相同点**: 均将操作经验表示为结构化步骤（前置条件、操作动作、验证方式）。
- **可检验的关键差异**:
  1. *动态演进*: AgentRunbook 生成相对静态的标准操作流程；RoleMem 追踪需求变更导致的破坏性更新（Breaking Contract Shifts），并处理未决冲突（Conflict Handling）。

---

## 3. 创新点证伪与回退预案
- **若消融实验 A3（取消 Role Bonus）表现与 Full 相同**: 则判定“角色投影”非核心贡献，主动剥离角色相关主张，将论文聚焦于“证据溯源与制品绑定的确定性时效机制（Artifact-Bound Validity Scoping）”。
- **若基线 B4（简单时间过滤）表现与 Full 无统计差异**: 则判定更深层的结构化依赖无增量收益，立即停止扩跑并在报告中如实阐述。
