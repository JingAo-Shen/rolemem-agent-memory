# RoleMem 硬件与执行环境可行性审计 (Feasibility Audit)

## 1. 硬件实测数据
- **GPU**: NVIDIA GeForce RTX 2080 Ti (实测显存容量: 22,528 MiB / 22.0 GB VRAM)
  - 驱动版本: 580.82.07
  - CUDA 版本: 13.0
  - 显存状态: 基础占用 < 150 MiB，空闲可用显存 > 21.8 GB。
- **CPU**: 13th Gen Intel(R) Core(TM) i5-13490F (16 逻辑核心)
- **内存 (RAM)**: 31 GiB 总容量，当前可用 ~14 GiB。
- **磁盘存储**: 761 GB 总容量，可用 697 GB (挂载于 rpool/ROOT/ubuntu_3f7ed0)。

## 2. 软件与依赖可用性
- **Python**: 3.13.5 (Anaconda 环境)
- **PyTorch**: 2.10.0+cu128 (CUDA acceleration available: True)
- **Git 凭证**: 已配置并存储全局凭证 (user: JingAo-Shen)，GitHub 远程推送测试通过。
- **商业 LLM API**: 已在系统 opencode 配置 (/root/.local/share/opencode/auth.json) 中确认 DeepSeek API 凭据。

## 3. 被测模型配置与可行性结论
- **Model A (本地开源小模型 SLM)**: Qwen2.5-Coder-3B-Instruct
  - 参数量: ~3B
  - 显存需求: FP16 模式占用约 6.5 GB，INT4/INT8 模式占用约 2.5~3.8 GB。
  - 22 GB 显卡容量评估: 完全可本地常驻，推理延迟预估在 20~50 ms/token，无需额外费用。
- **Model B (顶级商业大模型 LLM)**: DeepSeek-V3 / DeepSeek-Coder
  - 接口: DeepSeek OpenAI-compatible API
  - 预算与成本评估: P0~P3 全流程（约 1500 万 tokens）预估消耗 ¥20~30 元人民币，极其经济。
- **结论**: 硬件、软件、API 与存储完全满足从 P0 到 P4 的全量实验需求，无阻断性项 (No Blockers)。
