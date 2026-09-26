# RoleMem: Submission & Replication Package (v1.0-submission)

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Protocol: V2.2-Frozen](https://img.shields.io/badge/Protocol-V2.2--Frozen-green.svg)](data/formal_v2_2/protocol_preregistration.json)
[![Tests: 297 Passed](https://img.shields.io/badge/Tests-297%20Passed-brightgreen.svg)](tests/)
[![Release: v1.0-submission](https://img.shields.io/badge/Release-v1.0--submission-blue.svg)](release/v1.0-submission/)

Official submission package, replication codebase, and experimental artifacts for the research paper:  
***"RoleMem: A Temporal Consistency Evaluation Framework for Role-Based Agent Memory"***.

---

## 1. Project Overview

Autonomous LLM agents operating in software engineering tasks accumulate factual knowledge about codebases into external memory stores. However, real-world repositories evolve continuously through Git commit histories—functions are refactored, parameter defaults shift, APIs are deprecated, and dependency constraints update. Static agent memory systems suffer from **epistemic obsolescence**, leading agents to invoke deleted APIs or violate altered contracts.

**RoleMem** establishes a formal framework and evaluation architecture to maintain temporal consistency across evolving codebases:
1. **Formal 6-Tuple Memory Unit**: $\mathcal{M} = \langle c, \mathcal{E}, \mathcal{R}, \gamma, \tau, \Phi \rangle$, integrating factual claims ($c$), physical grounding provenance ($\mathcal{E}$), epistemic memory roles ($\mathcal{R}$), confidence score ($\gamma$), temporal anchor ($\tau$), and cryptographic SHA-256 integrity hash ($\Phi$).
2. **Role-Aware Epistemic Invariant Routing**: Routes verification across four domain roles:
   - **API Role**: Callable AST existence, signature compatibility, and soft/hard deprecations.
   - **Configuration Role**: `DefaultValueEvolutionChecker` tracking parameter default mutations.
   - **Behavior Role**: Test suite assertion witness extraction.
   - **Dependency Role**: Packaging metadata (`pyproject.toml`, `setup.py`, `requirements.txt`) verification.
3. **Dynamic 3-State Lifecycle Engine ($\Lambda$)**: Implements `VALID` (PRESERVE), `PARTIALLY_VALID` (DOWNGRADE with advisory note), and `STALE` (INVALIDATE with eviction), capturing non-breaking widening and soft-deprecations without amnesia.

---

## 2. Environment Requirements

- **Operating System**: Linux x86_64 (Kernel 5.15+ / 6.6+)
- **Python Runtime**: Python 3.10+ (tested on Python 3.10, 3.11, 3.12, 3.13)
- **Core Dependencies**: `pytest >= 7.0`, `ast`, `git >= 2.34`, `matplotlib >= 3.7`, `numpy >= 1.24`
- **Hardware Requirement**: Standard CPU (no GPU required for static analysis). Mean verification latency is **$22.6\text{ms}$** per memory unit.
- **Repository Cache**: 25 bare Git repositories pre-cached in `/tmp/formal_bare_repos/` for local offline, deterministic reproduction.

---

## 3. Dataset Specifications

### A. Frozen Benchmark V2.2 ($N = 150$)
- **Repository Scope**: 25 canonical open-source Python repositories (Flask, FastAPI, Pandas, Dask, Requests, Pydantic, Celery, etc.).
- **Transitions ($\mathcal{T} = \langle S_{\text{base}}, S_{\text{target}} \rangle$)**: 50 real-world Git commit transitions mined via AST delta filtering.
- **Stratified Claims**:
  - `SIGNATURE_COMPATIBLE`: 50 claims (API Role)
  - `DEFAULT_VALUE`: 50 claims (Config Role)
  - `DEPRECATION_STATUS`: 28 claims (API Role)
  - `BEHAVIORAL_CONTRACT`: 17 claims (Behavior Role)
  - `DEPENDENCY_CONTRACT`: 5 claims (Dependency Role)
- **Dual Gold Annotation**: 75 complex claims independently double-annotated under strict isolation protocol (**Cohen's Kappa $\kappa = 1.0$**).

### B. Independent Robustness Challenge Suite ($N = 30$)
- 30 adversarial edge cases: **Evidence Missing** (10), **Ambiguous Evolution** (10), and **Conflicting Evidence** (10).

---

## 4. Replication Steps

### Step 1: Environment Setup
```bash
git clone https://github.com/JingAo-Shen/rolemem-agent-memory.git
cd rolemem-agent-memory
pip install -r requirements.txt
```

### Step 2: Execute Automated Test Suite
Runs all 297 unit, integration, and ablation tests:
```bash
pytest -q
```
*Expected output: `297 passed in ~35s` (100% pass rate).*

### Step 3: Reproduce All Paper Experiments & Tables
Executes inference for all baselines, ablations, and full RoleMem, generating Table 1, Table 2, and Table 3:
```bash
python scripts/generate_paper_experiments.py
```
*Outputs generated in `results/`, `paper/tables/`, and `release/v1.0-submission/`.*

### Step 4: Reproduce Independent Robustness Challenge Suite
Evaluates stress testing across 30 edge-case claims:
```bash
python scripts/run_robustness_experiment.py
```
*Outputs generated in `experiments/robustness/` and `paper/tables/table4_robustness.md`.*

---

## 5. Primary Results Summary

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

### Table 3: Performance Across Epistemic Roles ($N = 150$)

| Epistemic Role | Support ($N$) | Ground Truth Distribution | Majority Acc / F1 | Static AST Acc / F1 | Naive RAG Acc / F1 | RoleMem (Ours) Acc / F1 |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **API Role** | 78 | Valid: 74 / Stale: 3 / Partial: 1 | 94.9% / 32.5% | 97.4% / 59.6% | 66.7% / 31.1% | **100.0% / 100.0%** |
| **CONFIG Role** | 50 | Valid: 29 / Stale: 21 / Partial: 0 | 58.0% / 36.7% | 58.0% / 36.7% | 60.0% / 52.4% | **100.0% / 100.0%** |
| **BEHAVIOR Role** | 17 | Valid: 17 / Stale: 0 / Partial: 0 | 100.0% / 100.0% | 23.5% / 38.1% | 0.0% / 0.0% | **100.0% / 100.0%** |
| **DEPENDENCY Role** | 5 | Valid: 5 / Stale: 0 / Partial: 0 | 100.0% / 100.0% | 0.0% / 0.0% | 0.0% / 0.0% | **100.0% / 100.0%** |

---

### Table 4: Independent Robustness Stress Suite ($N = 30$)

| Challenge Category | Cases | Majority Acc / F1 | Static AST Acc / F1 | Naive RAG Acc / F1 | RoleMem (Ours) Acc / F1 |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Evidence Missing** (`ROB-EM`) | 10 | 50.0% / 33.3% | 50.0% / 33.3% | 50.0% / 33.3% | **50.0% / 33.3%** |
| **Ambiguous Evolution** (`ROB-AE`) | 10 | 40.0% / 19.1% | 50.0% / 34.8% | 50.0% / 31.6% | **70.0% / 47.9%** |
| **Conflicting Evidence** (`ROB-CE`) | 10 | 100.0% / 100.0% | 20.0% / 33.3% | 20.0% / 33.3% | **20.0% / 33.3%** |
| **Overall Robustness Suite** | **30** | **63.3% / 25.9%** | **40.0% / 26.4%** | **40.0% / 25.4%** | **46.7% / 30.1%** |

---

## 6. Submission Package Layout

```text
submission/
├── paper/                     # Manuscript sources & compiled PDF
│   ├── paper_draft_v1.md
│   └── paper.pdf
├── figures/                   # High-resolution 300 DPI publication plots
│   ├── figure2_overall_comparison.png
│   ├── figure3_ablation_f1_impact.png
│   └── figure4_role_breakdown.png
├── tables/                    # Standalone LaTeX and Markdown tables (Tables 1-4)
│   ├── table1_overall_comparison.md / .tex
│   ├── table2_ablation.md / .tex
│   ├── table3_role_analysis.md / .tex
│   └── table4_robustness.md / .tex
├── supplementary/             # Full supplementary documents & research notes
│   ├── claim_boundary.md
│   ├── claim_evidence_matrix.md
│   ├── experiment_notes.md
│   ├── final_checklist.md
│   ├── limitations.md
│   ├── possible_review_comments.md
│   ├── research_questions.md
│   ├── reviewer_response_draft.md
│   └── reviewer_simulation.md
└── artifact/                  # Frozen release candidate datasets & SHA-256 attestation
    ├── benchmark_inputs.jsonl
    ├── benchmark_gold.jsonl
    ├── all_predictions.json
    ├── table1_overall_comparison.json
    ├── table2_ablation.json
    ├── table3_role_analysis.json
    ├── table4_robustness.json
    └── freeze_attestation.json
```
