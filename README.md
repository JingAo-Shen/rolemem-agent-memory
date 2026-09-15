# RoleMem: Role-Conditioned Agent Memory

> Research on role-conditioned, agent-agnostic long-term memory for cross-agent task continuity.

## Research Goal

Can structured, evidence-grounded and role-conditioned memory preserve task continuity when work is handed off across different LLM agents or models, while reducing stale-memory and model-specific bias?

## First Paper Target

**RoleMem: Role-Conditioned Agent-Agnostic Memory for Cross-Agent Task Continuity**

## Execution Plan Update — 2026-09-15

当前执行以 [细化研究计划](docs/research-plan.md)、[实验矩阵](experiments/experiment-matrix.md) 和 [agent 工作包](docs/agent-task-packets.md) 为准。先读根目录 [执行总纲](RESEARCH-EXECUTION-GUIDE.md)。上面的原始题目是孵化目标；硬件容量尚待实测。所有实验目前均未运行。

## Repository Status

This repository is currently in the **research incubation** stage. The immediate goal is to turn the idea into a reproducible research question, benchmark, baseline suite, and first paper submission.

## Planned Structure

- `docs/research-plan.md` — research questions, hypotheses, novelty, risks
- `docs/roadmap.md` — staged implementation plan
- `experiments/experiment-matrix.md` — baselines, ablations, metrics
- `papers/` — manuscript notes, figures, tables, drafts
- `src/` — implementation
- `data/` — dataset scripts/configs; do not commit large datasets

## Hardware Assumption

Primary local environment: NVIDIA RTX 2080 Ti, 22 GB VRAM. Larger models or large-scale runs may use rented cloud GPUs when necessary.

## Current Principle

Prefer research problems where **memory, verification, generalization, orchestration, or evaluation design** are the main contribution, rather than simply scaling model size.
