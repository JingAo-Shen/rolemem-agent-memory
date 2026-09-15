# 原始文献与数据核验起点

检索日期：2026-09-15。本轮核验层级是论文摘要/公开页面和数据仓库说明，未完成系统综述、全文复现或许可证审计。下列“缺口”都是研究假设，不能引用本文件声称首次提出。P0 需查全文、补 2025–2026 最近邻与反例。

## 记忆与交接

- [A-MEM (2025)](https://arxiv.org/abs/2502.12110)：结构化连接与记忆演化已经有先例；“结构化记忆”本身不能作为新贡献。[作者代码](https://github.com/agiresearch/A-mem)。
- [AgeMem (2026)](https://arxiv.org/abs/2601.01885)：统一长短期记忆管理的近期工作；需比较本文无需策略训练的窄目标与它的覆盖关系。
- [LongMemEval (2024/2025)](https://arxiv.org/abs/2410.10813)：包含知识更新、时间推理等能力，可作为外部诊断，不直接等价于任务交接。
- [LongMemEval-V2 (2026)](https://arxiv.org/abs/2605.12493)：环境经验、紧凑证据和 AgentRunbook 方法与本题很接近，P0 必须全文核查，不能只与旧 RAG 比较。

候选差异：在可执行任务上交叉操纵角色、模型交接和状态变化，检验有效期与角色投影的独立作用。若新文献已覆盖，必须改写贡献。

## 小模型路由

- [RouteLLM](https://arxiv.org/abs/2406.18665) / [作者代码](https://github.com/lm-sys/routellm)：已有成本—质量路由；在工具任务上移植时要说明训练目标和任务分布的区别。
- [MetaRouter (2026)](https://arxiv.org/abs/2606.06178)：近期偏好与成本路由工作，作为补充审查候选，不能据摘要称为最强 agent 路由基线。

候选差异：记忆改变小模型成功概率后，路由器是否仍校准；必须用 memory × routing 因子实验排除简单叠加。

## 机器人失败记忆

- [Reflexion](https://arxiv.org/abs/2303.11366)：文本反思与跨尝试经验已有先例。
- [REFLECT](https://arxiv.org/abs/2306.15724)：机器人失败解释和修正已有先例；RoboFail 是诊断参考，不默认它能直接运行本项目 ROS2 任务。

候选差异：可验证失败记录的有效范围与失效机制，跨任务复用而非同一任务无限重试。ROS2 接口工程不能单独当学术创新。

## X 光数据与跨域

- [OPIXray 作者仓库](https://github.com/DIG-Beihang/OPIXray)：刀具相关 5 类及测试遮挡分级；其 OL 分级不能当成扫描仪域。
- [HiXray 等作者数据目录](https://github.com/DIG-Beihang/XrayDetection)：含不同数据集和申请说明。需区分各小节，不能把另一个数据集的类别列表误记成 HiXray 类别。
- [SIXray 作者仓库](https://github.com/MeioJane/SIXray)：全库图像级标签与可用定位标注必须分别核对；不能把百万图像默认成百万检测框样本。
- [DOAM / OPIXray 论文](https://arxiv.org/abs/2004.08656)：遮挡建模已有工作，先核对其模块与本文轻量一致性方法的差异。

**纠正原模板：** OPIXray、HiXray、SIXray 不得默认构成同标签空间的闭集迁移矩阵。需实际形成 `class-map.csv` 和 `annotation-audit.md`。本轮跨域 DG 最新直接基线检索尚不充分；P0 须补查并锁定一种满足“源域训练、无目标访问”的公开方法，不得把 UDA 当 DG。

## 未知检测与 X 光开放词汇

- [ORE](https://arxiv.org/abs/2103.02603)：开放世界定义包含未知发现和增量学习；只做固定类别留出时应称开集检测。
- [OW-DETR](https://openaccess.thecvf.com/content/CVPR2022/papers/Gupta_OW-DETR_Open-World_Detection_Transformer_CVPR_2022_paper.pdf)：可参考未知发现和物体性机制；正式复现需核查监督信息。
- [OLN-SSOS (2024)](https://arxiv.org/abs/2407.15763)：已有含 X 光的物体级异常检测，是必须审查的直接相关工作。
- [OVXD (2024)](https://arxiv.org/abs/2406.10961)：已有 X 光开放词汇检测；未知类名可见与不可见必须区分。
- [RAXO / DET-COMPASS (2025)](https://arxiv.org/abs/2503.17071) / [作者代码与数据入口](https://github.com/PAGF188/RAXO)：已有 X 光开放词汇方法及更丰富类别基准；可审计其标注覆盖，不能默认等同穷尽背景标注。

候选差异：类别与域双变化下的校准和误报约束，不是“首次在 X 光识别新类别”。未知物体不等于危险物体。

## P0 文献表必填字段

`title, year, primary_url, version, full_text_read, task, supervision, target_access, memory_scope, backbone, benchmark, metric, code_url, license_status, exact_overlap, difference_to_test, reproduce_or_adapt, blocker`。

每方向至少 8 篇，其中至少 3 篇为 2025–2026 的相关候选；数量仅是检索下限，找不到时如实记录检索词和空缺。最近的 3 篇必须读全文实验设置，而非仅凭摘要判断。若无法获得全文，写未核验并降低结论，不凑引文。

