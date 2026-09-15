# RoleMem agent 工作包

## P0：锁定研究对象
输入：本目录 research-plan、experiment-matrix，以及根目录 LITERATURE-STARTER.md 和 EXECUTION-CONTRACT.md。
步骤：
1. 建 literature.csv，至少 8 篇，最近 3 篇阅读全文设置；重点检查 A-MEM、AgeMem、LongMemEval-V2 的证据/更新/角色/交接覆盖。
2. 写 novelty-audit.md：每个候选贡献分别列最近邻、原文节号、相同点、可检验差异。找不到差异可以建议停止，不得编造。
3. 只读检查本机 GPU/依赖/现有模型，记录精确 ID 与可用性；先不下载大权重、不新增付费调用。
4. 编写 12 个任务规格（非完整实现），列可见事件、切换点、角色、隐藏验收条件。更新信息对所有方法同等可见。
5. 写 problem-lock.md，选择 A/B 候选、首个交接方向、数据家族规则、预算与尚缺依赖。
产出：reports/literature.csv、novelty-audit.md、feasibility.md、problem-lock.md、P0-review.md；data/task-specs.jsonl。
验收：每个规格能判对错；角色变化与模型变化可独立操纵；最近邻差异可被实验否定；没有承诺尚未测量的收益。完成即交回。

## P1：评测器和基线
前提：P0 已复核。
步骤：实现 12 fixtures 与隔离的隐藏测试；新增 src/memory.py、src/evaluate.py、src/cli.py；先实现 B0/B1/B3；建立 events/schema 和 task-family split 检查；完成无模型 mock 与已有真实模型冒烟各一份。
必须测试：未来 evidence ID 不可检索；同组跨 split 被拒绝；过期规则 fixture 被评分器抓到；空输出/超时算失败；重放 metrics 相同。
产出：configs/smoke.json、data/manifests、tests、runs/smoke-*、reports/P1-review.md。
验收：至少 1 条真实轨迹可手工对账；通过模型输出的虚假“成功”不能骗过评分器。模型不可用时只标 mock PASSED，阶段 BLOCKED。

## P2：最小机制实验
前提：P1 已复核；输入 60 dev 与训练历史库。
步骤：按研究计划实现 evidence/expiry/role；B1/B3/B4/F/A2/A3 同预算运行；抽查至少 10 条证据；分类记录静态与更新失败；画成本与 TSR 表；按停止门槛判定。
产出：configs/pilot.json、runs/pilot-*、reports/P2-review.md（每个方法成本、所有失败、role 是否独立有效）。
验收：Full 不能比基线多看到更新；A3 只移除 role bonus；结果可从原始日志重算；不接触 test。无增益也是有效交付。

## P3：冻结与正式实验
前提：研究负责人复核 P2，确认继续该方向和预算。输入为冻结数据清单、开发选择和实验矩阵。
步骤：
1. 生成 reports/protocol-lock.json：主指标/比较/阈值/数据 hash/模型版本/种子/样本规模/预算/失败处理；附功效或精度评估。测试开启时间记录为独立事件。
2. 按矩阵执行主实验和消融，默认 seeds 17/29/43；基线运行失败先修复并保留原记录，不得把缺失行悄悄删掉。
3. 从逐样本结果做配对聚类区间；报告每种子、全部失败和成本。只在冻结范围内运行，不因 test 不理想改方法。
产出：configs/final.json、reports/protocol-lock.json、runs/final-*、reports/P3-review.md、原始 predictions 与指标。
验收：可从原始预测重算表；正式与 pilot 分开；若 test 暴露实现错误，保存无效结果、记录修复并将后续运行标 corrected，不能装作首次测试。

## P4：论文证据包
前提：P3 已复核。
步骤：实现 scripts/build_tables.py 从 runs 生成 CSV/图；写 papers/claims-evidence.csv（claim、run_id、metric、figure、scope、limitation）；撰写方法、设置、结果、失败与限制，再写摘要。
产出：papers/draft.md、tables、figures、claims-evidence.csv、reproduce.md、reports/P4-review.md。
验收：每个数字有原始记录；负结果和未满足约束在摘要/结论中如实体现；论文标题匹配实际完成设置。无数据或未运行部分不能生成示意数字混作实验结果。

## 统一执行入口（P1 需实现）
以下是接口规格，当前不可假称已存在。命令均在本方向目录运行：
- python -m src.cli validate --config configs/smoke.json
- python -m src.cli run --config configs/smoke.json
- python -m src.cli summarize --run-dir runs/<真实run_id>

实现 --help、非零错误退出码、日志输出目录；不支持的配置要报错，不能静默回退。禁止让 validate 命令触发训练/付费调用。真实框架入口可由 CLI 包装，保持重放信息完整。

