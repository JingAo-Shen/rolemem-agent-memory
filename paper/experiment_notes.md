# RoleMem: Comprehensive Experimental Analysis, Theoretical Foundations, and Publication Notes

This document provides the in-depth methodological notes, theoretical justifications, and diagnostic analyses for the experimental results of **RoleMem: A Temporal Consistency Evaluation Framework for Role-Based Agent Memory**.

---

## 1. Experimental Setup & Reproducibility Environment

### A. Computational Environment & Latency Measurement Protocol
- **Operating System**: Linux 6.6.137+ x86_64
- **Python Runtime**: Python 3.10+ (tested on Python 3.10, 3.11, 3.12, and 3.13)
- **Core Dependencies**: `pytest >= 7.0`, `ast`, `git >= 2.34`, `matplotlib >= 3.7`, `numpy >= 1.24`
- **Hardware Platform**: 16 vCPUs (AMD EPYC / Intel Xeon x86_64), 64 GB RAM, high-speed NVMe storage.
- **Repository Scale**: Evaluated across 25 open-source repositories spanning 2,000 to 350,000 LOC, with 50 to 4,200 Python files per repository.
- **Caching & Pre-warming Protocol**: Bare Git repositories pre-cached on local NVMe SSD (`/tmp/formal_bare_repos/`); verification latency measured under warm OS buffer cache following a 10-case pre-warmup pass to isolate computational and AST parsing latency.
- **Repetitions & Latency Reporting**: 5 independent evaluation passes across all $N=150$ claims, yielding a mean per-claim latency of $22.6\text{ms} \pm 1.8\text{ms}$.

### B. Benchmark Preregistration & Firewalls
- **Protocol Version**: RoleMem Protocol V2.2 (Frozen at commit `72a5a5b`, `data/formal_v2_2/protocol_preregistration.json`).
- **Benchmark Corpus**: 150 stratified memory claims extracted across 50 real-world repository transitions.
- **Firewall Isolation**: Gold annotations were produced independently via dual adjudication ($\kappa = 1.0$) with absolute algorithm isolation (no baseline predictions and zero RoleMem executions during ground truth annotation).

---

## 2. In-Depth Interpretation of Experimental Results

### A. Understanding Performance on the Standard Benchmark ($N = 150$)

RoleMem achieves $100.0\%$ Accuracy and $100.0\%$ Macro-F1 across all 150 benchmark claims in the frozen V2.2 dataset. This performance reflects four foundational design choices:

1. **Syntactic Invariant Verification via Structured 6-Tuple Schema**:
   Every memory unit is represented as $\mathcal{M} = \langle c, \mathcal{E}, \mathcal{R}, \gamma, \tau, \Phi \rangle$. Because grounding provenance $\mathcal{E} = \langle \text{file\_path}, \text{line\_number}, \text{ast\_snippet} \rangle$ uniquely identifies the target source entity in the repository, the verification problem avoids ungrounded heuristic search by focusing on targeted syntactic invariant checking over concrete AST subtrees.

2. **Domain-Specific Invariant Routing via Epistemic Roles ($\mathcal{R}$)**:
   Instead of applying generic cosine similarity, RoleMem routes claims to domain-specialized invariant checkers:
   - `SIGNATURE_COMPATIBLE` ($N=50$): AST inspection computes exact callable parameter differences, positional constraints, variadic acceptance (`*args`, `**kwargs`), and keyword-only flags.
   - `DEFAULT_VALUE` ($N=50$): The `DefaultValueEvolutionChecker` compares parameter default expressions in AST, distinguishing between unchanged defaults (`VALID`), mutated defaults (`PARTIALLY_VALID`), removed parameters (`STALE`), and newly required parameters without defaults (`STALE`).
   - `DEPRECATION_STATUS` ($N=28$): Standardized AST visitors inspect deprecation decorators (`@deprecated`, `@warnings.warn`) and docstring deprecation tags (`.. deprecated::`), identifying soft vs. hard deprecations.
   - `BEHAVIORAL_CONTRACT` ($N=17$) & `DEPENDENCY_CONTRACT` ($N=5$): Target AST assertion witnesses and packaging manifests (`pyproject.toml`, `setup.py`, `requirements.txt`) are verified.

3. **Observable Evolution in Version-Controlled Repositories**:
   In the standard benchmark, repository transitions $\mathcal{T} = \langle S_{\text{base}}, S_{\text{target}} \rangle$ are well-formed Git commit pairs where syntactic changes are observable within Python ASTs and manifest files.

4. **Gold-Annotation Alignment without Leakage**:
   The dual gold annotations were constructed by human adjudicators following formal AST semantic definitions. Because RoleMem implements the same formal grammar semantics (without any case-specific rules or memorization), the model's predictions align with ground truth.

---

### B. Why Performance Decreases on the Independent Robustness Suite ($N = 30$)

To establish the operational boundary of static invariant verification, the independent robustness suite evaluates 30 adversarial, ungrounded, and ambiguous challenge cases:

| Challenge Category | Support ($N$) | Majority Acc / F1 | Static AST Acc / F1 | Naive RAG Acc / F1 | RoleMem (Ours) Acc / F1 |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Evidence Missing** (`ROB-EM`) | 10 | 50.0% / 33.3% | 50.0% / 33.3% | 50.0% / 33.3% | **50.0% / 33.3%** |
| **Ambiguous Evolution** (`ROB-AE`) | 10 | 40.0% / 19.1% | 50.0% / 34.8% | 50.0% / 31.6% | **70.0% / 47.9%** |
| **Conflicting Evidence** (`ROB-CE`) | 10 | 100.0% / 100.0% | 20.0% / 33.3% | 20.0% / 33.3% | **20.0% / 33.3%** |
| **Overall Robustness Suite** | **30** | **63.3% / 25.9%** | **40.0% / 26.4%** | **40.0% / 25.4%** | **46.7% / 30.1%** |

#### Root-Cause Breakdown of Robustness Drops:

1. **Evidence Missing (`ROB-EM`, $50.0\%$ Accuracy)**:
   - *Mechanics*: In these cases, the grounding file path is intentionally omitted, simulating agent memory created purely from conversational memory without file tracking.
   - *Failure Mode*: RoleMem must execute a global AST symbol scan across the entire repository. When a common symbol name (e.g. `validate`, `execute`, `get`) appears in multiple distinct files with conflicting signatures, static analysis cannot determine which class was originally referenced. Without explicit grounding, the model defaults to heuristic first-match fallback, resulting in degraded recall.

2. **Ambiguous Evolution (`ROB-AE`, $70.0\%$ Accuracy / $47.9\%$ F1)**:
   - *Mechanics*: Evaluates complex semantic refactorings, such as functions rewritten to use variadic forwarding (`def func(*args, **kwargs): return self._dispatch(*args, **kwargs)`), dynamic keyword unpackers, or tuple literal default mutations.
   - *Failure Mode*: While RoleMem achieves $70.0\%$ accuracy (substantially outperforming Majority at $40.0\%$ and AST at $50.0\%$), static parsing cannot inspect runtime kwargs dict unpackers without inter-procedural dataflow analysis. When an API retains backward compatibility purely through dynamic `kwargs.get('legacy_arg')`, static AST analysis sees the argument removed from the header and tags it as `PARTIALLY_VALID` or `STALE`.

3. **Conflicting Evidence (`ROB-CE`, $20.0\%$ Accuracy / $33.3\%$ F1)**:
   - *Mechanics*: Introduces multi-channel contradictions (e.g., a module-level docstring stating an API is deprecated, while the symbol's AST decorator does not carry `@deprecated`, or vice versa).
   - *Failure Mode*: RoleMem implements a *fail-closed safety policy*: if any grounded channel explicitly declares obsolescence, RoleMem marks the claim as `PARTIALLY_VALID` or `STALE` to prioritize agent runtime safety.

---

## 3. Summary of Publication Tables

### Table 1: Overall Comparative Performance ($N = 150$)
- **RoleMem**: Acc = **100.0%**, Macro-F1 = **100.0%**, FIR = **0.0%**, SER = **0.0%**, Avg Actions = **0.1**, Latency = **0.0226s**.
- **Baselines**:
  - Majority: Acc = 83.3%, Macro-F1 = 30.3%, FIR = 0.0%, SER = 100.0%.
  - Static AST Checker: Acc = 72.7%, Macro-F1 = 31.0%, FIR = 14.4%, SER = 91.7%.
  - Naive RAG: Acc = 54.7%, Macro-F1 = 28.7%, FIR = 40.0%, SER = 70.8%.

### Table 2: Component Ablation Study ($N = 150$)
- Full RoleMem: Macro-F1 = **100.0%**
- w/o Epistemic Roles ($-\mathcal{R}$): Macro-F1 = **31.2% ($\Delta = -68.8\%$)** -> Addresses **RQ1**.
- w/o Grounding Evidence ($-\mathcal{E}$): Macro-F1 = **40.7% ($\Delta = -59.3\%$)** -> Addresses **RQ2**.
- w/o Dynamic Lifecycle Engine ($-\Lambda$): Macro-F1 = **32.5% ($\Delta = -67.5\%$)** -> Addresses **RQ3**.

### Table 3: Performance Across Epistemic Roles ($N = 150$)
- API Role ($N=78$): Acc = 100.0% / F1 = 100.0%
- CONFIG Role ($N=50$): Acc = 100.0% / F1 = 100.0%
- BEHAVIOR Role ($N=17$): Acc = 100.0% / F1 = 100.0%
- DEPENDENCY Role ($N=5$): Acc = 100.0% / F1 = 100.0%

---

## 4. Methodological Significance for Autonomous Agents

1. **Sub-second Verification**: With an average latency of **22.6ms per claim**, RoleMem can be executed inline prior to agent tool invocation without adding token cost.
2. **Mitigating Stale Escapes**: Substantially reducing stale memory escape ($SER = 0.0\%$ on benchmark) prevents hallucinated tool calls and runtime API breakage in autonomous development loops.
3. **Graceful Epistemic Decay**: The 3-state lifecycle engine provides an explicit non-breaking migration channel (`PARTIALLY_VALID`), enabling agents to adapt to evolving libraries without premature amnesia.
