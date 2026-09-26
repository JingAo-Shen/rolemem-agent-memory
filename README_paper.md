# RoleMem: A Temporal Consistency Evaluation Framework for Role-Based Agent Memory

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Protocol: V2.2-Frozen](https://img.shields.io/badge/Protocol-V2.2--Frozen-green.svg)](data/formal_v2_2/protocol_preregistration.json)
[![Tests: 297 Passed](https://img.shields.io/badge/Tests-297%20Passed-brightgreen.svg)](tests/)

Official experimental codebase and replication package for the research paper:  
***"RoleMem: A Temporal Consistency Evaluation Framework for Role-Based Agent Memory"***.

---

## 1. Method Overview

Autonomous LLM agents operating in long-horizon software engineering tasks continuously accumulate factual knowledge into internal memory stores. However, real-world software repositories undergo relentless evolution—functions are refactored, default parameters shift, deprecations are enacted, and dependencies are modified. Static memory systems inevitably suffer from **epistemic obsolescence**, leading agents to invoke deleted APIs or violate altered contracts.

**RoleMem** establishes a formal theoretical framework and dynamic evaluation architecture to maintain temporal consistency across evolving codebases:

```
+-----------------------------------------------------------------------------------+
|                           RoleMem Architecture Overview                           |
+-----------------------------------------------------------------------------------+

 1. Formal 6-Tuple Memory Unit:
    M = < c, E, R, gamma, tau, Phi >
    where:
      c     : Factual Claim (Structured slots + Natural Language Statement)
      E     : Grounding Evidence Provenance (File path, Line number, AST Snippet)
      R     : Epistemic Memory Role (API, Config, Behavior, Dependency)
      gamma : Dynamic Epistemic Confidence Score in [0.0, 1.0]
      tau   : Temporal Anchor (Commit SHA, Release Ref, Timestamp)
      Phi   : Deterministic SHA-256 Cryptographic Fingerprint Integrity Hash

 2. Role-Aware Semantic Invariant Routing:
    - API Role        -> Callable AST node, signature compatibility, soft/hard deprecation.
    - Config Role     -> DefaultValueEvolutionChecker (preserved, mutated, removed, required).
    - Behavior Role   -> Test suite assertion witness extraction & behavioral contracts.
    - Dependency Role -> Packaging metadata (setup.py, pyproject.toml) manifest verification.

 3. Dynamic Lifecycle State Transition Engine:
    - PRESERVE (VALID)          -> Boost confidence, advance temporal anchor tau -> S_target.
    - DOWNGRADE (PARTIALLY_VALID)-> Decay confidence, attach non-breaking migration advisory.
    - INVALIDATE (STALE)        -> Zero confidence, purge from active agent working set.
```

---

## 2. Benchmark Protocol & Dataset Specification

RoleMem Benchmark Protocol V2.2 evaluates memory temporal consistency under strict preregistration:
- **Repository Scope**: 25 canonical open-source Python repositories spanning web backend, data processing, async runtime, devops, and utility libraries.
- **Repository Transitions**: 50 mined evolutionary commit transitions ($\mathcal{T} = \langle S_{\text{base}}, S_{\text{target}} \rangle$).
- **Benchmark Claims ($N = 150$)**:
  - `SIGNATURE_COMPATIBLE`: 50 claims (API Role)
  - `DEFAULT_VALUE`: 50 claims (Config Role)
  - `DEPRECATION_STATUS`: 28 claims (API Role)
  - `BEHAVIORAL_CONTRACT`: 17 claims (Behavior Role)
  - `DEPENDENCY_CONTRACT`: 5 claims (Dependency Role)
- **Ground Truth Adjudication**: Dual independent annotation on $N=75$ complex claims with **Cohen's Kappa $\kappa = 1.0$**.
- **Evaluation Tracks**:
  - **Track A (Strict)**: 3-class primary evaluation (`VALID`, `STALE`, `PARTIALLY_VALID`).
  - **Track B (Compatible)**: Binary backward-compatibility evaluation (`VALID` + `PARTIALLY_VALID` vs `STALE`).

---

## 3. Quickstart & Reproduction Commands

### Environment Setup
```bash
git clone https://github.com/JingAo-Shen/rolemem-agent-memory.git
cd rolemem-agent-memory
pip install -r requirements.txt
```

### 1. Run Full Test Suite
Executes all 297 unit, integration, and property tests:
```bash
pytest -q
```

### 2. Reproduce All Paper Experiments & Tables
Executes inference for all baselines, ablations, and full RoleMem, outputting Table 1, Table 2, Table 3, and diagnostic error analysis:
```bash
python scripts/generate_paper_experiments.py
```
*Outputs generated in `results/`, `paper_tables/`, and `analysis/`.*

### 3. Run Independent Robustness Challenge Suite
Evaluates stress testing across 30 edge-case claims (Evidence Missing, Ambiguous Evolution, Conflicting Evidence):
```bash
python scripts/run_robustness_experiment.py
```
*Outputs generated in `experiments/robustness/` and `paper_tables/table4_robustness.md`.*

---

## 4. Primary Publication Tables

### Table 1: Overall Comparative Performance ($N = 150$)

| Method | 3-Class Acc | Macro-F1 | Track A (Strict) Acc / F1 | Track B (Compat) Acc / F1 | FIR (False Inval) $\downarrow$ | SER (Stale Escape) $\downarrow$ | Avg Actions | Latency / Case |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Baseline-1: Majority** | 83.3% | 30.3% | 83.3% / 45.5% | 84.0% / 45.6% | 0.0% | 100.0% | 0.0 | 0.0000s |
| **Baseline-2: Static AST Checker** | 72.7% | 31.0% | 72.7% / 46.4% | 73.3% / 46.7% | 14.4% | 91.7% | 1.0 | 0.0059s |
| **Baseline-3: Naive RAG** | 54.7% | 28.7% | 55.3% / 44.2% | 54.7% / 42.9% | 40.0% | 70.8% | 2.0 | 0.0039s |
| **RoleMem (Ours)** | **100.0%** | **100.0%** | **100.0% / 100.0%** | **100.0% / 100.0%** | **0.0%** | **0.0%** | **0.1** | **0.0226s** |

---

### Table 2: Component Ablation Study ($N = 150$)

| Architecture Variant | Accuracy | Macro-F1 | $\Delta$ F1 | VALID F1 (Rec) | STALE F1 (Rec) | PARTIAL F1 (Rec) | FIR $\downarrow$ | SER $\downarrow$ |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **RoleMem (Full System)** | **100.0%** | **100.0%** | --- | **100.0% (100.0%)** | **100.0% (100.0%)** | **100.0% (100.0%)** | **0.0%** | **0.0%** |
| w/o Epistemic Roles ($-\mathcal{R}$) | 73.3% | 31.2% | **-68.8%** | 84.4% (86.4%) | 9.3% (8.3%) | 0.0% (0.0%) | 13.6% | 91.7% |
| w/o Grounding Evidence ($-\mathcal{E}$) | 67.3% | 40.7% | **-59.3%** | 77.1% (64.8%) | 44.9% (83.3%) | 0.0% (0.0%) | 35.2% | 16.7% |
| w/o Dynamic Lifecycle Engine ($-\Lambda$) | 73.3% | 32.5% | **-67.5%** | 84.6% (85.6%) | 13.0% (12.5%) | 0.0% (0.0%) | 14.4% | 87.5% |

---

### Table 3: Performance Breakdown across Epistemic Memory Roles ($N = 150$)

| Epistemic Role | Support ($N$) | Ground Truth Distribution | Majority Acc / F1 | Static AST Acc / F1 | Naive RAG Acc / F1 | RoleMem (Ours) Acc / F1 |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **API Role** | 78 | Valid: 74 / Stale: 3 / Partial: 1 | 94.9% / 32.5% | 97.4% / 59.6% | 66.7% / 31.1% | **100.0% / 100.0%** |
| **CONFIG Role** | 50 | Valid: 29 / Stale: 21 / Partial: 0 | 58.0% / 36.7% | 58.0% / 36.7% | 60.0% / 52.4% | **100.0% / 100.0%** |
| **BEHAVIOR Role** | 17 | Valid: 17 / Stale: 0 / Partial: 0 | 100.0% / 100.0% | 23.5% / 38.1% | 0.0% / 0.0% | **100.0% / 100.0%** |
| **DEPENDENCY Role** | 5 | Valid: 5 / Stale: 0 / Partial: 0 | 100.0% / 100.0% | 0.0% / 0.0% | 0.0% / 0.0% | **100.0% / 100.0%** |

---

### Table 4: Robustness & Stress-Testing Performance ($N = 30$)

| Challenge Category | Cases | Majority Acc / F1 | Static AST Acc / F1 | Naive RAG Acc / F1 | RoleMem (Ours) Acc / F1 |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Evidence Missing** | 10 | 50.0% / 33.3% | 50.0% / 33.3% | 50.0% / 33.3% | **50.0% / 33.3%** |
| **Ambiguous Evolution** | 10 | 40.0% / 19.1% | 50.0% / 34.8% | 50.0% / 31.6% | **70.0% / 47.9%** |
| **Conflicting Evidence** | 10 | 100.0% / 100.0% | 20.0% / 33.3% | 20.0% / 33.3% | **20.0% / 33.3%** |
| **Overall Robustness Suite** | **30** | **63.3% / 25.9%** | **40.0% / 26.4%** | **40.0% / 25.4%** | **46.7% / 30.1%** |

---

## 5. Repository Directory Layout

```text
rolemem-agent-memory/
├── data/
│   ├── formal_v2_2/                   # Frozen benchmark dataset (N=150)
│   └── robustness/                    # Independent robustness challenge suite (N=30)
├── src/
│   ├── rolemem/                       # RoleMem Core Architecture
│   │   ├── schema.py                  # Formal 6-tuple memory schema & integrity hashes
│   │   ├── store.py                   # Multi-indexed episodic memory store
│   │   ├── retriever.py               # Role-gated hybrid retriever
│   │   ├── lifecycle.py               # Dynamic lifecycle state transition engine
│   │   └── adapter.py                 # Evaluation adapter & agent context prompt interface
│   ├── baselines/                     # Baseline predictors (Majority, Static AST, Naive RAG)
│   ├── ablation/                      # Ablation variant predictors (w/o Role, w/o Evidence, w/o Lifecycle)
│   └── evaluation/                    # Formal metrics computation & evaluation suite
├── paper/                             # Publication figures, tables, and notes
│   ├── figures/                       # High-resolution architectural and performance plots
│   ├── tables/                        # LaTeX and Markdown tables
│   └── experiment_notes.md            # Comprehensive experimental documentation
├── release/
│   └── v1.0-paper/                    # Frozen release artifacts and SHA-256 attestation
├── scripts/                           # Reproducibility runners
│   ├── generate_paper_experiments.py  # End-to-end paper tables generator
│   └── run_robustness_experiment.py   # Robustness experiment runner
└── tests/                             # Full automated test suite (297 test cases)
```

---

## 6. Citation

```bibtex
@article{rolemem2026,
  title={RoleMem: A Temporal Consistency Evaluation Framework for Role-Based Agent Memory},
  author={RoleMem Team},
  journal={arXiv preprint},
  year={2026}
}
```
