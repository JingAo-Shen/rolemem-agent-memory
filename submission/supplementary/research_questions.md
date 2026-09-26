# RoleMem: Formal Research Questions (RQs) and Empirical Findings

This document outlines the three core Research Questions (RQs) that drive the empirical evaluation of the **RoleMem** framework, detailing the hypothesis, methodological evaluation, and quantitative evidence for each question.

---

## Research Question 1 (RQ1): Role-Aware Memory Specialization

> **RQ1**: *Does role-aware memory improve temporal consistency in evolving software repositories compared to monolithic memory representations?*

### Motivation & Hypothesis
Traditional agent memory architectures treat all stored facts as generic text chunks or flat vector embeddings. However, software evolution manifests differently across different semantic dimensions: an API signature change requires parameter-level AST validation, a configuration default change requires value-evolution checking, a behavioral change requires test assertion witnesses, and a dependency version bump requires manifest parsing. We hypothesize that explicitly categorizing memory into epistemic roles ($\mathcal{R} \in \{\text{API}, \text{CONFIG}, \text{BEHAVIOR}, \text{DEPENDENCY}\}$) and routing verification to role-specialized AST invariant checkers is necessary to achieve high temporal consistency.

### Empirical Evidence
- **Table 2 Ablation ($-\mathcal{R}$)**:
  - When epistemic roles are removed and memory is evaluated through a generic monolithic checker, Macro-F1 drops precipitously from **$100.0\%$ to $31.2\%$ ($\Delta = -68.8\%$)**.
  - Accuracy falls to $73.3\%$.
  - The model fails to identify parameter default shifts ($N=21$ STALE cases in CONFIG role), yielding a Stale Escape Rate ($SER$) of **$91.7\%$**.
- **Table 3 Per-Role Breakdown**:
  - Across all 4 roles, full RoleMem achieves **$100.0\%$ Accuracy and $100.0\%$ F1** (API: $N=78$, CONFIG: $N=50$, BEHAVIOR: $N=17$, DEPENDENCY: $N=5$).
  - In contrast, Naive RAG achieves $0.0\%$ F1 on BEHAVIOR and DEPENDENCY roles, and Static AST achieves $36.7\%$ F1 on CONFIG roles.

### Conclusion for RQ1
**Yes.** Role-aware memory specialization is indispensable. Routing memory verification through specialized epistemic invariants prevents semantic blindness and provides a **$+68.8\%$ absolute gain in Macro-F1**.

---

## Research Question 2 (RQ2): Evidence Grounding and Provenance

> **RQ2**: *Does evidence grounding reduce stale memory escape and minimize false invalidation in agent memory stores?*

### Motivation & Hypothesis
Software repositories contain thousands of identical symbol names across different files and classes (e.g., `__init__`, `validate`, `to_dict`, `get`). Without concrete physical grounding ($\mathcal{E} = \langle \text{file\_path}, \text{line\_number}, \text{ast\_snippet} \rangle$), memory retrieval must rely on global symbol name matching or embedding similarity, leading to namespace collisions, false invalidations of unrelated symbols, and failure to detect localized staleness. We hypothesize that anchoring memory claims to concrete source provenance resolves namespace collisions and minimizes both False Invalidation Rate (FIR) and Stale Escape Rate (SER).

### Empirical Evidence
- **Table 2 Ablation ($-\mathcal{E}$)**:
  - Stripping grounding evidence causes Macro-F1 to collapse from **$100.0\%$ to $40.7\%$ ($\Delta = -59.3\%$)**.
  - False Invalidation Rate (FIR) surges from **$0.0\%$ to $35.2\%$**, as common helper methods are mistakenly invalidated against unrelated modules.
  - Stale Escape Rate (SER) climbs from **$0.0\%$ to $16.7\%$**.
- **Table 1 Baseline Comparison**:
  - Ungrounded Naive RAG exhibits a catastrophic $FIR = 40.0\%$ and $SER = 70.8\%$ ($F1 = 28.7\%$).
  - RoleMem with grounded provenance achieves **$FIR = 0.0\%$ and $SER = 0.0\%$**.

### Conclusion for RQ2
**Yes.** Grounding factual memory claims to concrete AST snippets and physical file paths is essential for precision, reducing the False Invalidation Rate from $35.2\%$ to $0.0\%$ and the Stale Escape Rate from $70.8\%$ to $0.0\%$.

---

## Research Question 3 (RQ3): Dynamic Lifecycle State Modeling

> **RQ3**: *Does dynamic lifecycle modeling (PRESERVE, DOWNGRADE, INVALIDATE) improve evolution tracking compared to static binary memory validity?*

### Motivation & Hypothesis
Software evolution is non-binary. Many evolutionary changes are backward-compatible modifications—such as adding an optional keyword argument with a default value, or marking an API as soft-deprecated with an impending sunset date. A rigid binary system (`VALID` vs `STALE`) either prematurely discards usable knowledge or falsely trusts deprecated interfaces. We hypothesize that a three-state dynamic lifecycle engine ($\Lambda$: PRESERVE, DOWNGRADE, INVALIDATE) accurately reflects evolutionary nuances, enabling agents to handle non-breaking changes (`PARTIALLY_VALID`) while decaying epistemic confidence $\gamma$.

### Empirical Evidence
- **Table 2 Ablation ($-\Lambda$)**:
  - Replacing the 3-state lifecycle engine with a static binary validator drops Macro-F1 from **$100.0\%$ to $32.5\%$ ($\Delta = -67.5\%$)**.
  - Recall on `PARTIALLY_VALID` cases drops to **$0.0\%$**, as all backward-compatible widening and soft-deprecations are misclassified as either strictly valid or completely stale.
  - Stale Escape Rate (SER) spikes to **$87.5\%$**.
- **Track A vs. Track B Analysis (Table 1)**:
  - RoleMem seamlessly tracks both Track A (Strict 3-class, $100.0\%$ F1) and Track B (Backward-compatible binary, $100.0\%$ F1), whereas baselines fail to distinguish between fully intact contracts and partially modified interfaces.

### Conclusion for RQ3
**Yes.** Dynamic lifecycle state modeling is critical for real-world software evolution. It provides the mechanism to detect backward-compatible modifications (`PARTIALLY_VALID`) and soft-deprecations, preventing binary over-simplification and delivering a **$+67.5\%$ absolute boost in Macro-F1**.

---

## Summary Matrix of Research Questions

| RQ | Focused Component | Core Metric Evaluated | Baseline / Ablation Performance | RoleMem Performance | Relative Impact ($\Delta$) |
| :--- | :--- | :--- | :---: | :---: | :---: |
| **RQ1** | Epistemic Roles ($\mathcal{R}$) | Macro-F1 across 4 roles | $31.2\%$ ($-\mathcal{R}$) | **$100.0\%$** | **$+68.8\%$ Macro-F1** |
| **RQ2** | Evidence Grounding ($\mathcal{E}$) | False Invalidation Rate (FIR) | $35.2\%$ ($-\mathcal{E}$) / $40.0\%$ (RAG) | **$0.0\%$** | **$-35.2\%$ to $-40.0\%$ FIR** |
| **RQ3** | Lifecycle Engine ($\Lambda$) | `PARTIALLY_VALID` Recall & F1 | $0.0\%$ ($-\Lambda$) | **$100.0\%$** | **$+67.5\%$ Macro-F1** |
