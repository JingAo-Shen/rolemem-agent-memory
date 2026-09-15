# RoleMem 问题与协议锁定文档 (Problem Lock)

## 1. 研究场景与任务类型
- **领域**: 软件工程可执行代码维护与交接任务沙箱（Python 本地可重置沙箱）。
- **任务家族 (Task Families)**:
  1. `config_migration`: 配置文件/环境变量字段变更与向后兼容修复。
  2. `api_contract_shift`: RESTful/RPC 接口入参、返回值契约及状态码变更。
  3. `data_pipeline_transform`: 数据流时区、单位转换、数据格式清洗规则演进。
  4. `auth_policy_update`: 权限鉴权逻辑与策略分支覆盖。

## 2. 四类状态演进场景划分
- **Category 1 (No Update - 静态基准)**: 需求自始至终未变，检验基础记忆检索与代码能力。
- **Category 2 (Explicit Update - 显式需求变更)**: 需求中间发生明确变更（valid_to 生效，新需求 supersedes 旧需求），检验模型能否放弃旧逻辑。
- **Category 3 (Stale Evidence - 制品失效)**: 依赖文件哈希改变或模块被重构，导致旧执行结论失效，检验系统能否根据 artifact_hash 判定 stale。
- **Category 4 (Unresolved Conflict - 未决冲突)**: 存在相互矛盾的上下文且无明确版本覆盖，检验系统能否保留双向证据标为 conflict 并触发 Reviewer 介入，而非随意盲从最新语句。

## 3. 模型与交接方向配置
- **Model A (SLM)**: Qwen2.5-Coder-3B-Instruct
- **Model B (LLM)**: DeepSeek-V3
- **交接方向**:
  - 主实验: Model A (Coder) -> Model B (Reviewer) 及 Model B (Coder) -> Model A (Reviewer)
  - 控制组: Model A -> Model A 及 Model B -> Model B

## 4. 统一预算约束
- **输入记忆预算 (Memory Budget)**: 主实验固定 2,048 Tokens (敏感性分析测试 512, 1024, 4096)。
- **每轮动作上限**: 最多 20 个工具动作。
- **模型输出上限**: 单次最多 4,096 Tokens。
- **打分方式**: 物理隔离的隐藏 pytest 测试套件与状态断言，100% 确定性评分。
