# Experiment Audit Report: Pilot-v0 Evaluation & Architectural Deficiencies

**Audit Date**: September 2026  
**Status**: Comprehensive Critical Audit — Pre-Refactoring Stage  
**Target Milestone**: `pilot-v0` Freeze and Architecture Restructuring

---

## 1. Executive Summary & Status Declaration

All results, metrics, and claims previously generated in **Phase P3 (300-episode simulated benchmark)** and **Phase P4 (DeepSeek 12-task initial pilot)** are formally designated as **`pilot-v0`** and **INVALIDATED for formal academic submission**.

This audit details the structural deficiencies, synthetic artifacts, and evaluator mismatches identified in `pilot-v0`, establishing the strict scientific requirements for `pilot-v1`.

---

## 2. Detailed Audit of Identified Deficiencies in Pilot-v0

### 2.1 Deficiency 1: P3 300-Task Experiment Relied on Deterministic Mock Actions
- **Finding**: The 300-episode dataset in `runs/p3_final_summary.json` was evaluated using deterministic mock action functions (synthetic regex substitutions simulating agent responses) rather than real LLM forward passes.
- **Scientific Consequence**: The reported 80.0% TSR vs 50.0% baseline and the statistical significance metric ($p < 0.001$) reflect deterministic simulator rules rather than empirical neural network behavior under real prompt distributions.

### 2.2 Deficiency 2: P3 Baseline Implementation Alias Issues
- **Finding**: In the P3 simulation scripts, baseline condition pairs were aliased to identical execution routines:
  - `B0_no_memory` and `A2_no_validity` shared identical underlying code branches.
  - `B4_time_filter` and `A3_no_role_bonus` shared identical internal retrieval logic.
- **Scientific Consequence**: The apparent equality of performance across certain baselines in P3 was an artifact of implementation aliasing rather than empirical equivalence.

### 2.3 Deficiency 3: Template-Replicated Dataset Structure
- **Finding**: The 300 test episodes in `data/test_episodes.jsonl` were generated via programmatic template replication of a small core set of rules rather than 300 genuinely diverse, independent software engineering problems.
- **Scientific Consequence**: Treating template variations as independent statistical degrees of freedom produces artificially narrow bootstrap confidence intervals.

### 2.4 Deficiency 4: Pilot-v0 Real DeepSeek Evaluator Mismatch
- **Finding**: In `src/real_llm_runner.py` and `scripts/run_real_experiment.py`, evaluation logic relied on category-level keyword and AST assertions (e.g., checking `TIMEOUT_MS` across all `no_update` tasks, `ADAPTIVE_LRU` across all `explicit_update` tasks, `SALT` across all `stale_evidence` tasks).
- **Scientific Consequence**: Tasks with distinct domain names (e.g., email validation vs payment gateway) were evaluated against uniform proxy assertions rather than their genuine domain functionality. The 91.7% TSR obtained in the 12-task pilot must not be cited as a validated scientific claim.

---

## 3. Retracted Paper Claims (Formal Notice)

The following claims are formally **RETRACTED** and will not appear in subsequent academic drafts until verified under the new `pilot-v1` framework:
1. *RoleMem achieves 80.0% TSR vs 50.0% on 300 software maintenance tasks ($p < 0.001$).*
2. *Role Projection provides an independently verified 30.0pp performance boost.*
3. *Qwen2.5-Coder-3B and DeepSeek cross-model handoffs have been formally benchmarked on full test suites.*
4. *DeepSeek API experiment in pilot-v0 represents definitive DeepSeek-V3 benchmark validation.*

---

## 4. Architecture Requirements for Pilot-v1 Restructuring

To guarantee scientific rigor, the `pilot-v1` implementation enforces the following standards:

```
+----------------------------------------------------------------------------------+
|                     PILOT-V1 SCIENTIFIC RIGOR REQUIREMENTS                       |
|                                                                                  |
| 1. Per-Task Independent Fixtures:                                                |
|    - Every task has its own initial code, historical events, repo transition,    |
|      target files, domain-specific pytest test suite, and stale ground truth.    |
|    - NO uniform proxy assertions across categories.                              |
|                                                                                  |
| 2. Fair Information Budget:                                                      |
|    - B0, B1, B2, B3, B4, B5, F receive IDENTICAL current instructions & repo.    |
|    - B0 receives zero historical memory, but FULL current task requirements.     |
|    - Only memory representation & filtering vary across methods.                 |
|                                                                                  |
| 3. Real Workspace Artifact Hash Calculation:                                     |
|    - SHA-256 digests computed directly from filesystem / workspace buffers.      |
|    - NO synthetic "hash_v1" / "hash_v2" fake string parameters.                  |
|    - Selective Invalidation: only memories tied to modified files are pruned.    |
|                                                                                  |
| 4. Distinct Baselines (No Aliasing):                                             |
|    - B0: No Memory                                                               |
|    - B1: Recent Raw History (Token-budget constrained)                           |
|    - B2: Rolling Summary                                                         |
|    - B3: Genuine BM25 Retrieval                                                  |
|    - B4: BM25 + Temporal Window ([t_from, t_to])                                 |
|    - B5: MemStrata-Style Temporal Supersession (Causal DAG, no artifact hash)    |
|    - F: RoleMem (Artifact-Grounded + Causal DAG + Scoped Projection)             |
|                                                                                  |
| 5. Real LLM Execution & Raw Prediction Logging:                                  |
|    - All smoke tasks executed with genuine LLM calls.                            |
|    - Raw outputs, AST verification logs, and pytest execution reports saved.     |
+----------------------------------------------------------------------------------+
```
