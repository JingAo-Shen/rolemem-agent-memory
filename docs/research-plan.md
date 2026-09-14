# Research Plan

## Core Question

Can structured, evidence-grounded and role-conditioned memory preserve task continuity when work is handed off across different LLM agents or models, while reducing stale-memory and model-specific bias?

## Candidate Contributions

1. Define a precise research problem with measurable failure modes.
2. Build a reproducible benchmark or task suite.
3. Propose a method that is lightweight enough to run mostly on a 22 GB GPU.
4. Compare against strong, simple baselines rather than only weak handcrafted baselines.
5. Report quality, cost, latency, memory use, and failure cases.

## Research Hypotheses

- **H1:** A structured method tailored to the target failure mode can outperform naive context expansion or naive retrieval.
- **H2:** The method can improve task success without requiring a larger backbone model.
- **H3:** Benefits remain under model/domain/task transfer instead of appearing only in a single in-domain setup.
- **H4:** The contribution remains useful after controlling for additional tokens, retrieval calls, or compute budget.

## Methodology Rules

- Separate training, validation, and final evaluation scenarios.
- Log every experiment with seed, model version, prompt/config hash, GPU, runtime, and cost.
- Always include simple baselines.
- Prefer at least 3 random seeds for smaller experiments.
- Perform ablations on every proposed component.
- Add qualitative failure analysis, not only aggregate accuracy.

## Paper Skeleton

1. Introduction
2. Related Work
3. Problem Formulation
4. Proposed Method
5. Benchmark / Experimental Setup
6. Main Results
7. Ablation Study
8. Failure Analysis
9. Limitations
10. Conclusion

## Direction-Specific Design

### Memory Layers
- Evidence Memory: immutable observations, files, tests, logs, tool results.
- Canonical Memory: facts, decisions, constraints, failures, skills, hypotheses.
- Role Views: coder, reviewer, researcher, planner, operator.

### Key Research Problems
- Cross-model memory transfer
- Stale memory and temporal validity
- Conflict resolution
- Selective forgetting
- Evidence-based verification before memory write
- Role-aware projection rather than plain top-k retrieval

### Candidate Benchmark: CrossAgentBench
Tasks are divided into multiple sessions with deliberate agent/model handoffs, requirement changes, stale facts, failed attempts, and conflicting updates.

### Candidate Metrics
- Task Success Rate
- Context Recovery Accuracy
- Cross-Agent Transfer Retention
- Stale Memory Error Rate
- Conflict Resolution Accuracy
- Repeated Failure Rate
- Token / latency / storage cost

