# RoleMem: Author Response & Rebuttal Draft

We thank the reviewers for their thoughtful, rigorous, and constructive feedback on our submission:  
***"RoleMem: A Temporal Consistency Evaluation Framework for Role-Based Agent Memory"***.

Below, we provide detailed, point-by-point responses to the core questions raised regarding benchmark accuracy, robustness performance, methodological scope, and system scalability.

---

## Question 1: "Why does RoleMem achieve 100.0% accuracy on the standard benchmark? Is the benchmark too trivial, synthetic, or overfitted?"

### Author Response:

We appreciate the reviewer raising this question. In empirical machine learning, a $100\%$ score naturally warrants scrutiny. However, in RoleMem, this outcome is the expected result of a **deterministic syntactic invariant validation over structured AST subtrees**, rather than a statistical heuristic over ambiguous natural language text.

1. **Deterministic Syntactic Invariant Validation over Structured AST Subtrees**:
   Unlike unstructured text retrieval, software engineering artifacts have well-defined, standardized formal grammars (Python AST). When a memory claim is grounded by concrete physical provenance $\mathcal{E} = \langle \text{file\_path}, \text{line\_number}, \text{ast\_snippet} \rangle$, the verification task reduces from an ill-posed global search to an exact syntactic invariant evaluation over a specific AST subtree.
2. **Domain-Specialized Invariant Checkers**:
   RoleMem routes claims according to their epistemic role ($\mathcal{R}$):
   - `SIGNATURE_COMPATIBLE` ($N=50$): Evaluated by computing exact parameter set differences, positional constraints, variadics, and keyword-only flags.
   - `DEFAULT_VALUE` ($N=50$): Evaluated via `DefaultValueEvolutionChecker`, comparing AST literal representations to identify identical, mutated, removed, or newly required parameters.
   - `DEPRECATION_STATUS` ($N=28$): Evaluated via AST visitors inspecting decorators (`@deprecated`, `@warnings.warn`) and docstring tags.
   - `BEHAVIORAL_CONTRACT` ($N=17$) & `DEPENDENCY_CONTRACT` ($N=5$): Evaluated against test assertion witnesses and packaging manifests (`pyproject.toml`, `setup.py`, `requirements.txt`).
3. **The Task is Highly Non-Trivial for Baseline Systems**:
   If the benchmark were trivial or easily solvable by standard approaches:
   - **Naive RAG** achieves only **$28.7\%$ Macro-F1** with a **$70.8\%$ Stale Escape Rate** and a **$40.0\%$ False Invalidation Rate**.
   - **Static AST Checker** achieves only **$31.0\%$ Macro-F1** with a **$91.7\%$ Stale Escape Rate**.
   - **Component Ablations** show catastrophic drops when any single component is removed: removing roles ($-\mathcal{R}$) drops Macro-F1 by **$-68.8\%$** (to $31.2\%$), removing evidence ($-\mathcal{E}$) drops Macro-F1 by **$-59.3\%$** (to $40.7\%$), and removing lifecycle modeling ($-\Lambda$) drops Macro-F1 by **$-67.5\%$** (to $32.5\%$).
4. **Observable Transitions & Clean Ground Truth**:
   The 50 benchmark transitions represent real-world Git commits mined from 25 open-source repositories. Dual independent annotation achieved high inter-annotator agreement ($\kappa = 1.0$), ensuring that the ground truth strictly mirrors formal repository syntax without annotation noise.

---

## Question 2: "Why is performance on the independent robustness suite lower (46.7% - 70.0% accuracy)? Does this indicate brittleness?"

### Author Response:

The lower accuracy on the independent robustness suite ($N=30$) is not a sign of arbitrary brittleness, but the direct and expected demonstration of the **theoretical boundaries of static program analysis**, which we explicitly designed these stress cases to measure:

1. **Evidence Missing (`ROB-EM`, $50.0\%$ Accuracy / $33.3\%$ F1)**:
   - *Design*: Grounding file paths were intentionally stripped to simulate ungrounded memories.
   - *Outcome*: Without file coordinates, RoleMem must fall back to global repository symbol search. When polymorphic helper functions (e.g., `validate`, `execute`, `get`) appear in multiple files with differing signatures, static analysis cannot determine the intended target without provenance. This drop empirically confirms our hypothesis for **RQ2**: physical evidence grounding is essential to prevent namespace collisions.
2. **Ambiguous Evolution (`ROB-AE`, $70.0\%$ Accuracy / $47.9\%$ F1)**:
   - *Design*: Evaluates complex semantic refactorings, such as functions rewritten to use variadic forwarding (`def func(*args, **kwargs): ...`) that delegate parameter checking to internal `kwargs.get()` dictionary unpackers.
   - *Outcome*: RoleMem achieves $70.0\%$ accuracy (substantially outperforming Majority at $40.0\%$ and AST at $50.0\%$). However, statically parsing the function header cannot inspect runtime dictionary unpacking without inter-procedural dataflow analysis.
3. **Conflicting Multi-Channel Evidence (`ROB-CE`, $20.0\%$ Accuracy / $33.3\%$ F1)**:
   - *Design*: Evaluates contradictory signals (e.g., a module docstring marks an API as deprecated, but the symbol AST decorator does not, or vice versa).
   - *Outcome*: RoleMem implements a strict *fail-closed safety policy*: if any grounded channel signals deprecation, RoleMem marks the memory as `PARTIALLY_VALID` or `STALE` to prevent runtime agent failures. In contrast, the Majority baseline trivially predicts `VALID` for all cases, scoring higher only when lenient execution is permitted.

---

## Question 3: "How does RoleMem compare with frontier LLMs prompting on raw repository diffs?"

### Author Response:

While frontier LLMs (e.g., GPT-4o, Claude 3.5 Sonnet) can analyze code diffs, utilizing them for real-time per-step agent memory verification introduces critical operational bottlenecks:
1. **Latency**: Prompting an LLM with multi-file diffs requires $2.0 - 5.0\text{s}$ per verification query. RoleMem executes in **$22.6\text{ms}$** ($0.0226\text{s}$), operating over **$100\times$ faster**.
2. **Token Cost & Context Windows**: Large repository diffs consume tens of thousands of tokens per step, rapidly exhausting context budgets. RoleMem requires **no external LLM tokens**.
3. **Determinism**: LLM reasoning over complex parameter defaults remains prone to stochastic hallucinations, whereas RoleMem provides deterministic validation over AST subtrees.

---

## Question 4: "How does RoleMem handle dynamic Python features such as runtime metaprogramming?"

### Author Response:

We have explicitly delineated this boundary in Section 7 (Limitations) and `paper/claim_boundary.md`:
- Static AST analysis operates directly on inspectable syntax nodes (`FunctionDef`, `AsyncFunctionDef`, `ClassDef`).
- For dynamic attributes created via `setattr()`, dynamic method dispatch via `__getattr__()`, or dynamic class synthesis via `type()`, static AST nodes are absent. In such cases, RoleMem routes verification to test assertion witnesses (`BEHAVIOR` role) or falls back to heuristic tracking.
- We view dynamic sandbox execution tracing as a complementary extension for future multi-runtime architectures.

---

## Question 5: "How does RoleMem scale to large repositories (100k+ LOC) and thousands of memory claims?"

### Author Response:

RoleMem is architected for constant-time, low-overhead scaling:
1. **Multi-Indexed Dual Lookup**: Memories are indexed via hash maps over symbol names and file paths ($\mathcal{O}(1)$ lookup).
2. **Scoped File-Level AST Parsing**: Verification parses *only* the specific target file referenced in provenance $\mathcal{E}$ (e.g., parsing a 300-line file takes $<5\text{ms}$), rather than the entire 100k+ LOC repository.
3. **Lifecycle Compaction**: As memories transition to `STALE`, they are evicted from active prompt working memory into an archival log, maintaining bounded context size during long-horizon agent execution.
