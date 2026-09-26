# RoleMem: Explicit Claim Boundaries, Assumptions, and Operational Scope

This document defines the formal boundaries, core assumptions, and operational scope of the **RoleMem** framework. It establishes what RoleMem systematically verifies under static analysis, what relies on heuristics, and which dynamic programming patterns are outside its current analytical scope.

---

## 1. Foundational Assumptions

RoleMem operates under two core epistemic assumptions:

### Assumption 1: Grounded Evidence Availability
- **Operational Requirement**: Each factual memory claim $c$ must be accompanied by an explicit physical grounding tuple:
  $$\mathcal{E} = \langle \text{file\_path}, \text{line\_number}, \text{ast\_snippet} \rangle$$
- **Analytical Scope**:
  - *When Grounded*: RoleMem performs targeted AST parsing on the specified source file, avoiding global namespace collisions across polymorphic symbols.
  - *When Ungrounded*: If physical coordinates are missing or deleted, RoleMem falls back to ungrounded repository-wide heuristic matching, which carries a risk of namespace collision and reduced recall (as demonstrated in the `ROB-EM` robustness experiments).

### Assumption 2: Observable Repository Evolution
- **Operational Requirement**: Evolution transitions $\mathcal{T} = \langle S_{\text{base}}, S_{\text{target}} \rangle$ must be inspectable within version-controlled repository artifacts (source code files, packaging manifests, and test suites).
- **Analytical Scope**:
  - *Observable Changes*: Source AST diffs, configuration default expressions, packaging manifest updates, and docstring deprecation tags.
  - *Unobservable Changes*: Out-of-band infrastructure updates, dynamic cloud microservice API shifts, environment variables injected at container runtime, or database migrations lacking repository schema definitions are outside the static analysis scope.

---

## 2. Supported Languages & Artifacts

| Dimension | Supported Scope | Unsupported / Out-of-Scope |
| :--- | :--- | :--- |
| **Programming Language** | Python 3.10+ standard AST grammar | Non-Python compiled binaries without source (C/C++, Rust, Cython, `.so`, `.pyd`) |
| **Static Code Entities** | `FunctionDef`, `AsyncFunctionDef`, `ClassDef`, module functions, class methods, static methods | Dynamically generated methods created at runtime without AST nodes |
| **Configuration Artifacts** | AST parameter default expressions, literal values, container literals | Dynamic runtime configuration loaded from external network services |
| **Packaging Manifests** | `pyproject.toml`, `setup.py`, `requirements.txt` | Proprietary build systems lacking standard Python manifest specifications |
| **Behavioral Witnesses** | Test assertion patterns (`assert`, `self.assert*`), docstring contracts | Non-deterministic flaky tests, distributed end-to-end integration tests |

---

## 3. Supported Invariants vs. Unsupported Dynamic Behaviors

### A. Supported Invariants (High Confidence)
1. **Signature Compatibility**: Positional arguments, positional-only arguments, keyword-only arguments, variadic parameters (`*args`, `**kwargs`), and parameter re-ordering.
2. **Default Value Evolution**: Exact AST comparison of parameter defaults via `DefaultValueEvolutionChecker` (distinguishing identical defaults, mutated defaults, removed parameters, and newly required parameters).
3. **Deprecation Identification**: Standardized AST inspection of `@deprecated`, `@warnings.warn`, and docstring `.. deprecated::` directives.
4. **Dependency Contract Verification**: Parsing package requirement names and pinned version boundaries.

### B. Unsupported Dynamic Behaviors (Requires Runtime Execution)
1. **Dynamic Metaprogramming**: Attribute assignment via `setattr()`, dynamic lookup via `__getattr__()` / `__getattribute__()`, or dynamic class synthesis via `type(name, bases, dict)`.
2. **Dynamic Variadic Forwarding**: Functions using `def func(*args, **kwargs): ...` that delegate argument validation to internal `kwargs.get()` dictionary lookups without explicit AST parameter headers (evaluated under `ROB-AE`).
3. **Runtime Monkey-Patching**: Dynamic modification of module or class dictionaries during test setup or application bootstrapping.
4. **Cross-Module Macro-like Expansion**: Dynamic code generation via `exec()` or `eval()`.

---

## 4. Summary Matrix of Methodological Boundaries

```
+-----------------------------------------------------------------------------------+
|                        RoleMem Operational Boundary Matrix                        |
+-----------------------------------------------------------------------------------+

 [ In Scope: High Confidence ]
   • Python AST Structural Analysis (Functions, Methods, Signatures)
   • Parameter Default Expression Tracking (AST Literals, Structures)
   • Standard Deprecation Patterns (Decorators, Warning Calls, Docstrings)
   • Packaging Manifests (pyproject.toml, setup.py, requirements.txt)
   • Test Suite Invariant Witnesses (Assertion Extraction)

 [ Fallback Mode: Heuristic Confidence ]
   • Missing Evidence Provenance (Global Symbol Search Fallback)
   • Variadic Forwarding (*args, **kwargs Delegation)
   • Conflicting Multi-Channel Annotations (Fail-Closed Prioritization)

 [ Out of Scope: Dynamic Boundary ]
   • Dynamic Metaprogramming (setattr, __getattr__, type())
   • Compiled C-Extensions / Binary Objects (.so, .pyd)
   • Out-of-band Microservice & Runtime Environment State
+-----------------------------------------------------------------------------------+
```
