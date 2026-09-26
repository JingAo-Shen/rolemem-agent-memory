# RoleMem: Core Assumptions, Operational Boundaries, and Limitations

This document formally delineates the foundational assumptions, theoretical scope, and operational boundaries of the **RoleMem** temporal consistency framework. Acknowledging these boundaries is essential for properly interpreting experimental results, understanding deployment prerequisites, and guiding future extensions.

---

## 1. Foundational Assumptions

RoleMem operates under two primary epistemic assumptions regarding agent memory and software repositories:

### Assumption 1: Grounded Evidence Availability
- **Definition**: Every factual memory claim $c$ stored in the agent's memory store $\mathcal{M}$ is grounded by an explicit provenance tuple:
  $$\mathcal{E} = \langle \text{file\_path}, \text{line\_number}, \text{ast\_snippet} \rangle$$
- **Rationale**: In real-world software agent workflows (e.g., repository navigation, code synthesis, bug localization), factual claims are derived from agent observations of concrete source code files. Grounding provides the physical invariant anchor needed to disambiguate identical symbol names across distinct modules (e.g., multiple definitions of `__init__`, `validate`, or `parse`).
- **Implication of Violation**: If an agent stores completely ungrounded memories (e.g., abstract conversational summaries without file provenance), RoleMem degrades to ungrounded global AST search. As demonstrated in our ablation study ($-\mathcal{E}$), ungrounded retrieval suffers from severe namespace collisions, resulting in a **$59.3\%$ drop in Macro-F1** and a False Invalidation Rate of $35.2\%$.

### Assumption 2: Observable Repository Evolution
- **Definition**: The transition from base state $S_{\text{base}}$ to target state $S_{\text{target}}$ is fully observable through inspectable repository artifacts, including:
  1. Python Abstract Syntax Trees (ASTs) of source files.
  2. Standard packaging and configuration manifests (`setup.py`, `pyproject.toml`, `requirements.txt`).
  3. Test suite assertion witnesses and docstrings.
- **Rationale**: RoleMem verifies temporal consistency by comparing the historical memory claim $c$ anchored at $S_{\text{base}}$ against the syntactic and semantic structures of $S_{\text{target}}$.
- **Implication of Violation**: If software evolution occurs outside the observable codebase—such as runtime configuration changes, dynamic external cloud service APIs, database schema migrations without repository metadata, or untracked environment variables—RoleMem cannot statically observe the transition and may yield false invariants.

---

## 2. Operational Boundaries & Theoretical Limitations

### A. Static AST Traversal vs. Dynamic Metaprogramming
- **Static Invariant Boundary**: RoleMem's primary inference engine relies on AST static analysis (`ast.parse`) for callable signatures, parameter default values, and decorator bindings.
- **Dynamic Language Constraints**: Python is a highly dynamic language supporting runtime metaprogramming patterns:
  - Dynamic attribute binding (`setattr`, `getattr`, `__getattr__`, `__getattribute__`).
  - Dynamic class construction (`type(name, bases, dict)`).
  - Runtime monkey-patching and decorator mutation.
  - C-extensions and compiled binary bindings (`.so`, `.pyd`, Cython).
- **Behavior under Metaprogramming**: When a repository heavily utilizes runtime metaprogramming to define public APIs dynamically without explicit AST `FunctionDef` or `AsyncFunctionDef` nodes, static parsing alone cannot resolve signatures. RoleMem addresses this by falling back to test-suite witness execution and docstring assertion extractors, but purely dynamic un-tested symbols remain a challenge for static verification.

### B. Ambiguous Evolution & Semantic Overloading
- **Variadic Forwarding (`*args`, `**kwargs`)**: When an API transitions from explicit parameter signatures to generic variadic forwarding (`def func(*args, **kwargs): ...`), static AST analysis cannot determine whether the original explicit parameter is still accepted internally by kwargs unpackers without full inter-procedural dataflow analysis.
- **Dynamic Type Polymorphism**: Type signatures that evolve without explicit type annotations (or use ambiguous `Any` unions) may maintain syntactic compatibility while subtly altering expected runtime value semantics.

### C. Conflicting Multi-Channel Evidence
- **Channel Divergence**: Software artifacts often contain multiple heterogeneous channels conveying status:
  - AST decorator: `@deprecated` or `@warnings.warn`.
  - Docstring notice: `.. deprecated:: 2.0`.
  - Packaging deprecation flag in `__all__` or `__init__.py`.
- **Precedence Conflicts**: When one channel indicates obsolescence (e.g. module docstring marked as deprecated) while the symbol AST remains active, static priority rules may conflict. RoleMem enforces fail-closed prioritization (tagging as `PARTIALLY_VALID` or `STALE` under explicit soft/hard deprecation), but human intent in contradictory documentation requires deep natural language understanding.

### D. Ecosystem and Language Specialization
- **Current Scope**: RoleMem V1.0 is engineered and benchmarked for the Python software ecosystem, leveraging Python's standardized AST grammar and PEP-compliant packaging conventions.
- **Cross-Language Generalization**: Applying RoleMem to dynamically typed ecosystems with fragmented module standards (e.g., JavaScript/TypeScript with ESM/CommonJS duality, or Ruby's open classes) will require developing language-specific AST extractors and manifest parsers.

---

## 3. Summary of Design Choices and Scope Definitions

| Dimension | RoleMem Scope | Out-of-Scope / Requires Extension |
| :--- | :--- | :--- |
| **Language Target** | Python 3.10+ source code | Non-Python compiled binaries without source |
| **Memory Grounding** | Concrete file path, line number, AST snippet | Hallucinated abstract text with no file links |
| **Repository Artifacts** | Git commits, AST, manifests, test witnesses | Out-of-band runtime microservice states |
| **Evolution Invariants** | Signature, Default Value, Deprecation, Manifest | Deep inter-procedural runtime heap state |
| **Verification Latency** | Sub-30ms static AST verification | Heavy multi-minute VM execution environments |

These limitations define the exact conditions under which RoleMem's methodological properties and empirical performance hold, providing a transparent foundation for the paper's scientific claims.
