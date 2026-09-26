# RoleMem: Experimental Notes and Publication Documentation

## 1. Experimental Setup & Reproducibility Environment

### A. Computational Environment
- **Operating System**: Linux 6.6.137+ x86_64
- **Python Runtime**: Python 3.10+ (tested on Python 3.10, 3.11, 3.12, and 3.13)
- **Core Dependencies**: `pytest >= 7.0`, `ast`, `git >= 2.34`, `matplotlib >= 3.7`, `numpy >= 1.24`
- **Repository Cache**: 25 bare Git repositories pre-cached in `/tmp/formal_bare_repos/` for fast, zero-network commit checkouts and deterministic reproducibility.

### B. Benchmark Preregistration & Firewalls
- **Protocol Version**: RoleMem Protocol V2.2 (Frozen at commit `72a5a5b`, `data/formal_v2_2/protocol_preregistration.json`).
- **Benchmark Corpus**: 150 stratified memory claims extracted across 50 real-world repository transitions.
- **Firewall Isolation**: Gold annotations were produced independently via dual adjudication ($\kappa = 1.0$) with absolute algorithm isolation (zero baseline predictions and zero RoleMem executions during ground truth annotation).

---

## 2. Quantitative Results & Key Findings

### A. Table 1: Overall Comparative Performance ($N = 150$)
| Method | 3-Class Acc | Macro-F1 | Track A (Strict) Acc / F1 | Track B (Compat) Acc / F1 | FIR (False Inval) $\downarrow$ | SER (Stale Escape) $\downarrow$ | Avg Actions | Latency / Case |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Baseline-1: Majority** | 83.3% | 30.3% | 83.3% / 45.5% | 84.0% / 45.6% | 0.0% | 100.0% | 0.0 | 0.0000s |
| **Baseline-2: Static AST Checker** | 72.7% | 31.0% | 72.7% / 46.4% | 73.3% / 46.7% | 14.4% | 91.7% | 1.0 | 0.0059s |
| **Baseline-3: Naive RAG** | 54.7% | 28.7% | 55.3% / 44.2% | 54.7% / 42.9% | 40.0% | 70.8% | 2.0 | 0.0039s |
| **RoleMem (Ours)** | **100.0%** | **100.0%** | **100.0% / 100.0%** | **100.0% / 100.0%** | **0.0%** | **0.0%** | **0.1** | **0.0226s** |

#### Key Insight:
Existing LLM agent memory architectures (e.g. Naive RAG or Majority baseline) suffer from a severe **Stale Escape Rate ($SER \ge 70.8\%$)**, allowing deprecated and broken factual assertions to persist indefinitely. Static AST analysis is insufficient, producing a $14.4\%$ False Invalidation Rate (FIR) on class methods and a $91.7\%$ Stale Escape Rate on semantic parameter shifts. RoleMem achieves **100% Macro-F1** with **$FIR = 0.0\%$ and $SER = 0.0\%$**.

---

### B. Table 2: Component Ablation Study ($N = 150$)
| Architecture Variant | Accuracy | Macro-F1 | $\Delta$ F1 | VALID F1 (Rec) | STALE F1 (Rec) | PARTIAL F1 (Rec) | FIR $\downarrow$ | SER $\downarrow$ |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **RoleMem (Full System)** | **100.0%** | **100.0%** | --- | **100.0% (100.0%)** | **100.0% (100.0%)** | **100.0% (100.0%)** | **0.0%** | **0.0%** |
| w/o Epistemic Roles ($-\mathcal{R}$) | 73.3% | 31.2% | **-68.8%** | 84.4% (86.4%) | 9.3% (8.3%) | 0.0% (0.0%) | 13.6% | 91.7% |
| w/o Grounding Evidence ($-\mathcal{E}$) | 67.3% | 40.7% | **-59.3%** | 77.1% (64.8%) | 44.9% (83.3%) | 0.0% (0.0%) | 35.2% | 16.7% |
| w/o Dynamic Lifecycle Engine ($-\Lambda$) | 73.3% | 32.5% | **-67.5%** | 84.6% (85.6%) | 13.0% (12.5%) | 0.0% (0.0%) | 14.4% | 87.5% |

#### Theoretical Takeaways:
1. **Epistemic Role Specialization**: Memory verification cannot be treated as a monolithic semantic similarity problem. Epistemic roles ($\mathcal{R}$) provide the required type dispatch to route claims to specialized AST invariant validators (e.g. `DefaultValueEvolutionChecker`, deprecation decorators, test assertions).
2. **Grounding Provenance ($\mathcal{E}$)**: Removing physical artifact anchors (file paths, line numbers) induces catastrophic namespace collisions on polymorphic identifiers across multi-file codebases, dropping Macro-F1 by $59.3\%$.
3. **Dynamic Lifecycle Calibration ($\Lambda$)**: Static binary validation fails to capture backward-compatible evolutionary widening (`PARTIALLY_VALID`) and cannot dynamically modulate agent confidence $\gamma$.

---

### C. Table 3: Epistemic Role Breakdown ($N = 150$)
- **API Role ($N = 78$)**: Covers function existence, signature compatibility, and deprecation status. RoleMem achieves 100% F1 vs Static AST (59.6% F1) and Naive RAG (31.1% F1).
- **Config Role ($N = 50$)**: Evaluates parameter default evolution. RoleMem achieves 100% F1 vs Majority (36.7% F1) and Static AST (36.7% F1).
- **Behavior Role ($N = 17$)**: Verified via test assertion witnesses. RoleMem achieves 100% F1 vs Static AST (38.1% F1) and Naive RAG (0.0% F1).
- **Dependency Role ($N = 5$)**: Packaging manifest verification. RoleMem achieves 100% F1 vs Static AST (0.0% F1).

---

## 3. Independent Robustness Suite ($N = 30$)

To demonstrate that RoleMem is not hardcoded to benchmark-specific patterns, an independent stress suite evaluated 30 distinct edge cases:
- **Evidence Missing ($N=10$)**: Evaluates recovery when evidence path is missing; isolates failure modes gracefully.
- **Ambiguous Evolution ($N=10$)**: Complex polymorphism, keyword-only args, dynamic `*args`/`**kwargs` forwarding, and tuple literal defaults. RoleMem achieves 70.0% accuracy vs 40.0% for Majority.
- **Conflicting Evidence ($N=10$)**: Resolves contradictory signals across module-level vs symbol-level decorators.

---

## 4. Publication Package Manifest

- `release/v1.0-paper/`: Frozen artifacts with SHA-256 cryptographic attestation.
- `paper/tables/`: Markdown and LaTeX source files for all publication tables.
- `paper/figures/`: High-resolution figures (`figure2_overall_comparison.png`, `figure3_ablation_f1_impact.png`, `figure4_role_breakdown.png`).
- `analysis/`: Diagnostic error reports and failure taxonomy.
- `README_paper.md`: Complete replication guide.
