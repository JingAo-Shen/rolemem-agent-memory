# Roadmap

## Phase 0 — Literature and Problem Lock
- Build a paper matrix of recent related work.
- Identify 3–5 strongest baselines.
- Write a one-page problem definition.
- Define success/failure metrics before implementing the proposed method.

## Phase 1 — Reproducible Baseline
- Implement the simplest working pipeline.
- Freeze dataset/task splits.
- Add experiment logging and seed control.
- Reproduce at least one public baseline.

## Phase 2 — Proposed Method
- Implement the smallest version of the core idea.
- Run controlled comparisons under the same budget.
- Record negative results.

## Phase 3 — Ablation and Generalization
- Remove each component independently.
- Test different backbone sizes.
- Test transfer to at least one unseen model/domain/environment when applicable.

## Phase 4 — Paper
- Freeze the experimental protocol.
- Generate final tables and plots automatically.
- Write limitations and failure cases early.
- Prepare reproducibility checklist and release plan.
