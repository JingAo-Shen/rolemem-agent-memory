# RoleMem: System Architecture and Dynamic Memory Lifecycle Specification

## 1. System Overview & Scientific Motivation

Autonomous agent systems operating on evolving software repositories face a fundamental challenge: **Temporal Consistency Breakdown**. When an agent persists factual memories (e.g., function signatures, default parameter values, behavior contracts, or package dependencies) observed at an initial codebase state $S_{\text{base}}$, downstream repository evolution across commits, releases, and refactorings can silently invalidate those memories at state $S_{\text{target}}$. Unchecked reliance on stale historical memories leads to runtime crashes, hallucinated API calls, and broken dependency resolutions.

**RoleMem** addresses this challenge through an epistemic, role-based memory framework with:
1. Structured, role-typed memory representations.
2. Multi-channel, role-aware retrieval.
3. Budget-bounded evidence escalation.
4. Formal state transition dynamics (Preserve, Downgrade, Invalidate).

```
+-----------------------------------------------------------------------------------+
|                              RoleMem Core Architecture                            |
+-----------------------------------------------------------------------------------+
|                                                                                   |
|  [Agent Input / Query]                                                            |
|          │                                                                        |
|          ▼                                                                        |
|  ┌─────────────────────────────────┐                                              |
|  │  Role-Aware Hybrid Retriever    │ ◄── [Vector + BM25 + Role Index]             |
|  └───────────────┬─────────────────┘                                              |
|                  ▼                                                                |
|  ┌─────────────────────────────────┐                                              |
|  │  Candidate Memory Record        │: <claim, evidence, role, confidence, tau>    |
|  └───────────────┬─────────────────┘                                              |
|                  ▼                                                                |
|  ┌─────────────────────────────────────────────────────────────┐                  |
|  │  Budget-Bounded Evidence Escalation Ladder (B50 Budget)     │                  |
|  │    Tier 0: Static AST Witness Check        (Cost: 0 actions)│                  |
|  │    Tier 1: Targeted File Search & AST      (Cost: 1-5 act)  │                  |
|  │    Tier 2: Packaging & Dependency Parsing  (Cost: 5-10 act) │                  |
|  │    Tier 3: Test Discovery & Execution      (Cost: 10-25 act)│                  |
|  └───────────────┬─────────────────────────────────────────────┘                  |
|                  ▼                                                                |
|  ┌─────────────────────────────────────────────────────────────┐                  |
|  │  Temporal State Transition Engine                           │                  |
|  │    ├─ PRESERVE   (VALID)           -> Boost confidence      │                  |
|  │    ├─ DOWNGRADE  (PARTIALLY_VALID) -> Decay & Warn          │                  |
|  │    └─ INVALIDATE (STALE)           -> Purge & Invalidate    │                  |
|  └───────────────┬─────────────────────────────────────────────┘                  |
|                  ▼                                                                |
|  [Decision Output / Evaluation Adapter]                                           |
|                                                                                   |
+-----------------------------------------------------------------------------------+
```

---

## 2. Memory Representation

Every unit of agent memory in RoleMem is formally modeled as a 6-tuple:

$$\mathcal{M} = \langle c, \mathcal{E}, \mathcal{R}, \gamma, \tau, \Phi \rangle$$

### 2.1 Specification of Tuple Components

1. **Claim ($c$)**:
   - The factual proposition asserted by the agent. Formatted dual-mode:
     - `structured_claim`: Strongly typed JSON slot dictionary:
       $$\text{slots} \in \{\text{module}, \text{symbol}, \text{attribute}, \text{expected\_parameters}, \text{expected\_default}, \text{contract\_specification}, \text{version\_constraint}\}$$
     - `raw_statement`: Canonical natural language statement for human readability and LLM prompt conditioning.

2. **Grounding Evidence ($\mathcal{E}$)**:
   - Verifiable provenance linking the claim to physical source artifacts at creation time:
     - `evidence_path`: Relative file path in repository tree (e.g. `src/package/module.py`).
     - `evidence_lineno`: Integer line number in source file.
     - `evidence_snippet`: Verbatim source code, test assertion, or manifest snippet proving claim truth.
     - `extraction_channel`: `AST_ANALYSIS` | `DOCUMENTATION_PARSING` | `PACKAGE_METADATA_PARSING` | `TEST_ASSERTION_EXTRACTION`.

3. **Memory Role ($\mathcal{R}$)**:
   - The functional epistemic domain of the memory:
     $$\mathcal{R} \in \{\mathcal{R}_{\text{API}}, \mathcal{R}_{\text{Behavior}}, \mathcal{R}_{\text{Dependency}}, \mathcal{R}_{\text{Config}}\}$$

4. **Confidence Score ($\gamma \in [0.0, 1.0]$)**:
   - Calibrated Bayesian belief certainty reflecting verification depth, evidence specificity, and temporal age.

5. **Temporal Snapshot ($\tau$)**:
   - Explicit version anchoring:
     $$\tau = (\text{commit\_sha}, \text{timestamp\_iso8601}, \text{release\_ref})$$

6. **Provenance Hash Fingerprint ($\Phi$)**:
   - Cryptographic commitment ensuring tamper-evident immutability:
     $$\Phi = \text{SHA256}(c \parallel \mathcal{E} \parallel \mathcal{R} \parallel \tau)$$

---

## 3. Epistemic Memory Roles Taxonomy

RoleMem stratifies memory into four primary operational roles, each governed by specialized verification procedures and validity invariants:

| Memory Role | Target Domain | Eligible Claim Types | Primary Verification Mechanism |
| :--- | :--- | :--- | :--- |
| **$\mathcal{R}_{\text{API}}$ (API Memory)** | Structural interfaces, public symbols, signatures, callability | `SYMBOL_EXISTS`, `CALLABLE`, `SIGNATURE_COMPATIBLE`, `IMPORT_PATH_VALID`, `ATTRIBUTE_EXISTS` | AST symbol table lookup, argument list inspection |
| **$\mathcal{R}_{\text{Behavior}}$ (Behavior Memory)** | Runtime transformations, return values, exception contracts | `BEHAVIORAL_CONTRACT`, `RETURN_VALUE` | Unit test execution, assertion analysis, docstring contract checks |
| **$\mathcal{R}_{\text{Dependency}}$ (Dependency Memory)** | Package requirements, version specifiers, optional extras | `DEPENDENCY_CONTRACT` | `pyproject.toml`, `setup.py`, `requirements.txt` manifest parsing |
| **$\mathcal{R}_{\text{Config}}$ (Configuration Memory)** | Parameter defaults, environment flags, settings keys | `DEFAULT_VALUE`, `ATTRIBUTE_EXISTS` | AST parameter default literal evaluation, config dictionary parsing |

---

## 4. Multi-Modal Retrieval Mechanisms

RoleMem implements and compares three retrieval paradigms for accessing relevant memory units during code reasoning:

### 4.1 Vector Similarity Retrieval (Dense Embedding)
- **Method**: Dense embedding representations $\mathbf{e}_q, \mathbf{e}_m \in \mathbb{R}^d$ generated via text/code embedding models:
  $$\text{Score}_{\text{dense}}(q, m) = \cos(\mathbf{e}_q, \mathbf{e}_m) = \frac{\mathbf{e}_q \cdot \mathbf{e}_m}{\|\mathbf{e}_q\| \|\mathbf{e}_m\|}$$
- **Strengths**: Captures semantic intent and paraphrased queries.
- **Weaknesses**: Prone to symbol collision (e.g., confusing `client.get()` with `requests.get()`) and blind to subtle signature/default mutations.

### 4.2 Keyword Retrieval (Sparse BM25)
- **Method**: Inverted index over exact token stems from `structured_claim` and `evidence_snippet`:
  $$\text{Score}_{\text{BM25}}(q, m) = \sum_{t \in q} \text{IDF}(t) \cdot \frac{f(t, m) \cdot (k_1 + 1)}{f(t, m) + k_1 \cdot \left(1 - b + b \cdot \frac{|m|}{\text{avgdl}}\right)}$$
- **Strengths**: Precise on exact identifier names, module paths, and parameter tokens.
- **Weaknesses**: Misses related functional concepts expressed with different vocabulary.

### 4.3 Role-Aware Structural Retrieval (RoleMem Hybrid)
- **Method**: Composite scoring with hard role-filtering and confidence weighting:
  $$\text{Score}_{\text{RoleMem}}(q, m) = \mathbb{I}(\text{RoleMatch}(q, m)) \cdot \left[ \alpha \cdot \text{Score}_{\text{BM25}}(q, m) + \beta \cdot \text{Score}_{\text{dense}}(q, m) + \omega_{\text{conf}} \cdot \gamma_m \right]$$
- **Advantages**:
  - Gated by epistemic role: API queries cannot accidentally retrieve configuration flags.
  - Prioritizes memories with higher verified confidence $\gamma_m$.
  - Achieves superior precision and zero cross-role contamination.

---

## 5. Dynamic Memory Lifecycle & Update Policy

When the agent transitions from codebase state $S_{\text{base}}$ to $S_{\text{target}}$, active memories undergo formal temporal state transitions.

```
                      [Active Memory M at S_base]
                                   │
                    ┌──────────────┴──────────────┐
                    ▼                             ▼
         [Target State Witness Check]   [Evidence Escalation]
                    │                             │
        ┌───────────┼───────────┐                 │
        ▼           ▼           ▼                 │
   [Preserve]  [Downgrade] [Invalidate] ◄─────────┘
     (VALID)   (PARTIALLY)   (STALE)
        │           │           │
        ▼           ▼           ▼
  [Confidence  [Confidence  [Purge from
    Boost]       Decay]     Working Set]
```

### 5.1 State Transition Definitions

1. **PRESERVE ($\text{VALID}$)**:
   - **Condition**: Target state AST, tests, or manifests confirm that the claim predicate $\Pi(s)$ remains 100% true without breaking alteration.
   - **Action**: Update temporal anchor $\tau \leftarrow \tau_{\text{target}}$, increase confidence $\gamma \leftarrow \min(1.0, \gamma + \delta_{\text{boost}})$.

2. **DOWNGRADE ($\text{PARTIALLY\_VALID}$)**:
   - **Condition**: Non-breaking modification detected (e.g. backward-compatible re-export alias, signature widened with new optional parameters having default values, or soft deprecation notice without hard removal).
   - **Action**: Mark status `PARTIALLY_VALID`, apply confidence decay $\gamma \leftarrow \gamma \times \lambda_{\text{decay}}$ ($\lambda = 0.8$), and attach a migration advisory directive.

3. **INVALIDATE ($\text{STALE}$)**:
   - **Condition**: Incompatible modification detected (e.g. symbol removed/renamed, required positional parameter added, existing parameter deleted, default value altered, dependency constraint broken, or test assertion fails).
   - **Action**: Set status `STALE`, purge from active agent context, and record in historical contradiction log to prevent regression.

### 5.2 Budget-Bounded Evidence Escalation Ladder (B50 Budget)

To prevent unbounded exploration costs, RoleMem enforces a strict 4-tier escalation policy bounded by maximum budget $B_{\text{max}} = 50$ actions:

1. **Tier 0: In-Memory Static Witness Check (Cost: 0 actions)**:
   - Fast AST node lookup in pre-parsed target tree cache.
2. **Tier 1: Targeted Repository File Search (Cost: 1–5 actions)**:
   - Direct file inspection and syntax tree traversal.
3. **Tier 2: Manifest & Dependency Parsing (Cost: 5–10 actions)**:
   - Packaging file parsing (`pyproject.toml`, `setup.py`, `setup.cfg`).
4. **Tier 3: Test Discovery & Targeted Execution (Cost: 10–25 actions)**:
   - Isolated sandbox test execution for behavioral contracts.

---

## 6. Evaluation Adapter Specification

The RoleMem Evaluation Adapter interfaces the core memory engine with the formal preregistered benchmark:

```
+───────────────────────────────────────────────────────────────+
|                 RoleMem Evaluation Adapter Flow               |
+───────────────────────────────────────────────────────────────+
|                                                               |
|   formal_inputs.jsonl                                         |
|         │                                                     |
|         ▼                                                     |
|   ┌────────────────────────────────────────────────────────┐  |
|   │ RoleMemEvaluationAdapter                               │  |
|   │   1. Parse case_id, structured_claim, raw_statement    │  |
|   │   2. Checkout target repository snapshot               │  |
|   │   3. Route claim to role-specific validity analyzer    │  |
|   │   4. Execute budget-bounded evidence escalation        │  |
|   │   5. Determine predicted_label & confidence score      │  |
|   └────────────────────────┬───────────────────────────────┘  |
|                            ▼                                  |
|   formal_predictions.jsonl                                    |
|   {"case_id": "FV22-000001", "predicted_label": "VALID", ...} |
|                                                               |
+───────────────────────────────────────────────────────────────+
```

### 6.1 Input / Output Schemas

- **Input Format** ([`data/formal_v2_2/formal_inputs.jsonl`](file:///code/rolemem-agent-memory/data/formal_v2_2/formal_inputs.jsonl)):
  ```json
  {
    "case_id": "FV22-000001",
    "structured_claim": {
      "module": "agateexcel.table_xlsx",
      "symbol": "TableXLSX.from_xlsx",
      "parameter_or_attr": "sheet",
      "expected_default": null
    },
    "raw_statement": "In wireservice/agate-excel, the parameter 'sheet' of 'TableXLSX.from_xlsx' in module 'agateexcel.table_xlsx' defaults to 'None'.",
    "claim_type": "DEFAULT_VALUE",
    "repository_name": "wireservice/agate-excel"
  }
  ```

- **Output Format** (`data/formal_v2_2/formal_predictions.jsonl`):
  ```json
  {
    "case_id": "FV22-000001",
    "predicted_label": "VALID",
    "confidence": 0.95,
    "escalation_tier": "TIER_0_STATIC_AST",
    "action_count": 1,
    "execution_wall_time_sec": 0.012
  }
  ```

---

## 7. Scientific & Protocol Invariants

1. **Protocol Immutability**: The benchmark inputs (`formal_inputs.jsonl`) and ground truth (`formal_gold_private.jsonl`) are strictly frozen and immutable.
2. **Algorithm Immutability**: Core validation rules under `src/claim_validity/**` and `src/evidence_escalation/**` remain identical to frozen commit `fe62749b`.
3. **Budget Invariant**: Every evaluation run operates under default runtime budget $B = 50$, with all action costs explicitly audited.
