# RoleMem: A Temporal Consistency Evaluation Framework for Role-Based Agent Memory

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Protocol: V2.2-Frozen](https://img.shields.io/badge/Protocol-V2.2--Frozen-green.svg)](data/formal_v2_2/protocol_preregistration.json)
[![Tests: 297 Passed](https://img.shields.io/badge/Tests-297%20Passed-brightgreen.svg)](tests/)
[![Release: v1.0-submission](https://img.shields.io/badge/Release-v1.0--submission-blue.svg)](release/v1.0-submission/)

Official repository and replication package for the research paper:  
***"RoleMem: A Temporal Consistency Evaluation Framework for Role-Based Agent Memory"***.

---

## 1. Overview

Autonomous LLM agents operating in software engineering tasks accumulate factual knowledge about codebases into external memory stores. However, real-world repositories evolve continuously through Git commit histories—functions are refactored, parameter defaults shift, APIs are deprecated, and dependency constraints update. Static agent memory systems suffer from **epistemic obsolescence**, leading agents to invoke deleted APIs or violate altered contracts.

**RoleMem** establishes a formal framework and dynamic verification system to maintain temporal consistency across evolving codebases:
1. **Formal 6-Tuple Memory Representation**: $\mathcal{M} = \langle c, \mathcal{E}, \mathcal{R}, \gamma, \tau, \Phi \rangle$, integrating factual claims ($c$), physical grounding provenance ($\mathcal{E}$), epistemic memory roles ($\mathcal{R}$), confidence scores ($\gamma$), temporal anchors ($\tau$), and cryptographic SHA-256 integrity hashes ($\Phi$).
2. **Role-Aware Epistemic Invariant Routing**: Routes verification across four domain roles:
   - **API Role**: Callable AST existence, signature compatibility, and soft/hard deprecations.
   - **Configuration Role**: `DefaultValueEvolutionChecker` tracking parameter default mutations.
   - **Behavior Role**: Test suite assertion witness extraction.
   - **Dependency Role**: Packaging metadata (`pyproject.toml`, `setup.py`, `requirements.txt`) verification.
3. **Dynamic 3-State Lifecycle Engine ($\Lambda$)**: Implements `VALID` (PRESERVE), `PARTIALLY_VALID` (DOWNGRADE with advisory note), and `STALE` (INVALIDATE with eviction), capturing non-breaking widening and soft-deprecations without amnesia.

---

## 2. Quickstart & Replication

### Environment Requirements
- **Operating System**: Linux x86_64
- **Python Runtime**: Python 3.10+ (tested on Python 3.10, 3.11, 3.12, 3.13)
- **Dependencies**: `pytest >= 7.0`, `ast`, `git >= 2.34`, `matplotlib >= 3.7`, `numpy >= 1.24`

### Installation
```bash
git clone https://github.com/JingAo-Shen/rolemem-agent-memory.git
cd rolemem-agent-memory
pip install -r requirements.txt
```

### 1. Run Full Test Suite
```bash
pytest -q
```
*Expected: 297 passed in ~35s.*

### 2. Reproduce All Paper Experiments
```bash
python scripts/generate_paper_experiments.py
python scripts/run_robustness_experiment.py
```

---

## 3. Key Results Summary

- **Table 1 (Overall Comparative Performance, $N=150$)**: RoleMem achieves **$100.0\%$ Macro-F1**, reducing False Invalidation Rate ($FIR$) and Stale Escape Rate ($SER$) to **$0.0\%$**, outperforming Majority ($30.3\%$), Static AST ($31.0\%$), and Naive RAG ($28.7\%$) with a mean latency of **$22.6\text{ms}$** and no external LLM token overhead.
- **Table 2 (Component Ablations, $N=150$)**: Removing Epistemic Roles ($-\mathcal{R}$) drops Macro-F1 by **$-68.8\%$**; removing Grounding Evidence ($-\mathcal{E}$) drops Macro-F1 by **$-59.3\%$** ($+35.2\%$ FIR); disabling Dynamic Lifecycle ($-\Lambda$) drops Macro-F1 by **$-67.5\%$**.
- **Table 3 (Epistemic Role Breakdown, $N=150$)**: $100.0\%$ F1 across API ($N=78$), Config ($N=50$), Behavior ($N=17$), and Dependency ($N=5$) roles.
- **Table 4 (Robustness Challenge Suite, $N=30$)**: $70.0\%$ on Ambiguous Evolution (`ROB-AE`), $50.0\%$ on Missing Evidence (`ROB-EM`), $20.0\%$ on Conflicting Evidence (`ROB-CE`).

---

## 4. Submission Package Directory

Complete submission assets are packaged in [`submission/`](submission/):
```text
submission/
├── paper/                     # Manuscript source & compiled PDF (paper.pdf)
├── figures/                   # 300 DPI publication plots (Figures 2, 3, 4)
├── tables/                    # Standalone LaTeX and Markdown tables (Tables 1-4)
├── supplementary/             # Full research notes, QA checklists, rebuttal drafts
└── artifact/                  # Frozen benchmark & robustness datasets with SHA-256 attestation
```

---

## 5. Documentation Directory

- [`README_submission.md`](README_submission.md) & [`README_paper.md`](README_paper.md): Detailed replication guides.
- [`paper/paper_draft_v1.md`](paper/paper_draft_v1.md): Full academic paper draft.
- [`paper/claim_evidence_matrix.md`](paper/claim_evidence_matrix.md): Claim-to-evidence traceability matrix.
- [`paper/claim_boundary.md`](paper/claim_boundary.md): Operational scope & dynamic boundaries.
- [`paper/limitations.md`](paper/limitations.md): Core assumptions & unsupported dynamic patterns.
- [`paper/research_questions.md`](paper/research_questions.md): Detailed RQ1, RQ2, and RQ3 analyses.
- [`paper/possible_review_comments.md`](paper/possible_review_comments.md): Bank of 22 reviewer questions & defenses.
- [`paper/final_checklist.md`](paper/final_checklist.md): Pre-submission QA audit.
- [`final_release_notes.md`](final_release_notes.md): Formal v1.0-submission release notes.
