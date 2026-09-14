# RoleMem: Role-Conditioned Agent Memory

> Research on role-conditioned, agent-agnostic long-term memory for cross-agent task continuity.

## Research Goal

Can structured, evidence-grounded and role-conditioned memory preserve task continuity when work is handed off across different LLM agents or models, while reducing stale-memory and model-specific bias?

## First Paper Target

**RoleMem: Role-Conditioned Agent-Agnostic Memory for Cross-Agent Task Continuity**

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
