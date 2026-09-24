# RoleMem Protocol V2.2 — Formal Unseen Benchmark Preregistration

**Protocol Document ID:** `RM-PREREG-V2.2-001`  
**Protocol Version:** `2.2-formal-v1.0`  
**Frozen Algorithm Source Commit:** `fe62749b98ea2a8e62ed5dbb031b39deddc33624`  
**Freeze Tag:** `protocol-v2.2-v1-deterministic-freeze`  
**Freeze Attestation Commit:** `fcff4104645203bdf35a27ffbd04542d7e9dd995`  
**Freeze Attestation Tag:** `protocol-v2.2-v1-freeze-attestation`  
**Freeze Closure Commit:** `da105f9555e098e9e2fcb87e190ce9eb730af3ee`  
**Freeze Closure Status:** `PASS`  
**Preregistration State:** `S0_PREREGISTRATION`  
**Date:** September 24, 2026  

---

## 1. Executive Summary & Scientific Boundary

This document establishes the binding preregistration protocol for the **RoleMem Protocol V2.2 Formal Unseen Benchmark**. This benchmark serves as the definitive, confirmatory evaluation of the frozen RoleMem deterministic evidence escalation architecture for agent memory validity.

### Non-Negotiable Boundaries:
1. **Algorithm Source Code Immobility**: The algorithm codebase under `src/claim_validity/**` and `src/evidence_escalation/**` is strictly frozen at commit `fe62749b98ea2a8e62ed5dbb031b39deddc33624` (tagged `protocol-v2.2-v1-deterministic-freeze`). Zero modifications to algorithm logic, validators, AST parsing, witness binding, planner policies, cost models, or thresholds are permitted.
2. **Strict Protocol-Only Scope**: This task establishes formal rules, sampling hierarchies, metric formulas, and firewall state machines **before** any candidate formal repository is discovered, selected, cloned, inspected, mined, or evaluated.
3. **Prohibition of Data Hunting**: No candidate repositories are searched or inspected during this phase. Zero formal claims and zero formal gold labels exist.

```
+----------------------------------------------------------------------------------------------------+
|                                    FORMAL DATA FIREWALL (S0)                                       |
|                                                                                                    |
|   Formal Repositories Selected:  0               Formal Transitions Inspected:    0                 |
|   Formal Claims Created:        0               Formal Gold Labels Created:      0                 |
|   formal_data_opened:           false           formal_state:                    S0_PREREGISTRATION|
+----------------------------------------------------------------------------------------------------+
```

---

## 2. Contaminated Repository Blacklist Universe

To prevent subtle test-set leakage, data dredging, or historical bias from past research phases, all formal candidate discovery must exclude every repository recorded in the frozen contamination registry.

- **Registry Location**: [`data/splits/repository_contamination_registry.json`](file:///code/rolemem-agent-memory/data/splits/repository_contamination_registry.json)
- **Registry Cryptographic Hash (SHA256)**: `ae01f0c825cb3beb4bd415426d7ce4ff6931db1b9535369f28239c4aded7a03d`
- **Contaminated Universe Size**: Exactly 29 distinct repositories.

### Blacklisted Universe (29 Repositories):
```
attrs, cachelib, celery, click, cryptography, dateutil, fastapi, flake8, flask,
httpx, iniconfig, itsdangerous, jinja, markupsafe, marshmallow, more-itertools,
packaging, pluggy, pydantic, pytest, requests, rich, sqlalchemy, starlette,
tqdm, urllib3, uvicorn, virtualenv, werkzeug
```

### Blacklist Invariant:
Formal candidate discovery must load `repository_contamination_registry.json` programmatically. Any repository $R$ satisfying $R \in \text{Blacklist}$, including any forks, renames, mirrors, or submodules of these 29 repositories, is strictly ineligible.

---

## 3. Repository-Level Unseen Condition

A candidate repository $R$ is formally classified as `FORMAL_UNSEEN` if and only if, prior to formal discovery, $R$ has **zero** historical occurrences in:
- `data/**` (including all historical benchmarks, specs, curation pools, and blind annotation sets)
- `reports/**` (all research reports, audits, and feasibility reviews)
- `runs/**` (all multi-seed runs, pilot runs, and telemetry outputs)
- Test fixtures and mocks in `tests/`
- Prior transition specifications and manifests

Verification is enforced programmatically prior to candidate acceptance.

---

## 4. Objective Repository Eligibility Criteria

Repository eligibility must be determined entirely by objective, mechanical repository characteristics, without regard to whether a repository contains changes that RoleMem can solve.

### Mandatory Inclusion Rules:
1. **Public Open-Source Git Repository**: Hosted publicly with complete git commit graph and tag objects.
2. **Primary Language**: Python ($\ge 85\%$ codebase volume in Python).
3. **Mature Historical Track Record**: At least 2 full calendar years of commit history OR $\ge 100$ non-merge commits.
4. **Automated Test Infrastructure**: Dedicated `tests/` or `test/` directory containing executable pytest or unittest test suites.
5. **Identifiable Release Anchors**: Multiple tagged releases (preferred) or clearly identifiable chronological commit milestones.
6. **AST Syntax Parseability**: Source files must parse cleanly under standard Python 3 AST parsers.
7. **Active Status at Transition**: Repository was not archived or abandoned at the sampled transition point.
8. **Real Software Engineering Project**: Synthetic, tutorial-only, benchmark-only, or toy demo repositories are strictly excluded.

Subjective criteria such as "looks interesting" or "has easy claims" are explicitly forbidden.

---

## 5. Selection Independence & Anti-Outcome-Conditioning

The pipeline enforces strict temporal and logical separation: **Repository selection must strictly precede RoleMem execution and prediction.**

### Prohibited Practices:
- Running RoleMem on candidate transitions to filter or select repositories.
- Discarding a repository after observing that RoleMem abstains or fails on its transitions.
- Selecting repositories specifically because they match known deterministic rule templates.

---

## 6. Preregistered Discovery Source & Search Constraints

- **Discovery Source**: Public Python open-source universe (GitHub public search API / open-source archive).
- **Fixed Search Parameters**:
  - `language`: `Python`
  - `is:fork`: `false`
  - `is:archived`: `false`
  - `min_stars`: `50` (ensures non-trivial codebase quality and maintenance)
  - `min_non_merge_commits`: `100`

Search constraints are fixed now and must not be altered post hoc.

---

## 7. Category Diversity Specifications

To prevent over-indexing on web frameworks or simple CLI tools, candidate discovery must ensure coverage across distinct functional domains:
1. `libraries` (algorithmic, mathematical, data-structure libraries)
2. `developer_tools` (linters, formatters, code analyzers, build tools)
3. `data_utility` (parsers, serializes, file format handlers, ETL tools)
4. `cli_packages` (command-line interfaces, terminal tooling)
5. `web_backend` (HTTP clients, servers, API frameworks, networking)
6. `infrastructure` (process managers, storage engines, system abstractions)

Category assignment must be based solely on package purpose, never on expected benchmark label.

---

## 8. Formal Repository Scale Targets & Shortfall Procedures

- **Minimum Accepted Formal Repositories**: $N_{\min} = 20$
- **Target Repositories**: $N_{\text{target}} = 25$
- **Maximum Accepted Repositories**: $N_{\max} = 30$

### Shortfall Procedure:
If rule-based discovery yields fewer than 20 eligible repositories:
1. Record explicit status: `FORMAL_REPOSITORY_SHORTFALL`.
2. Halt execution immediately.
3. Criteria must **never** be silently relaxed. An external review must determine whether to expand the search breadth using preregistered rules.

---

## 9. Rule-Based Transition Sampling Protocol

Transitions within accepted repositories must be identified using deterministic or fixed-seed selection algorithms. Manual cherry-picking of "interesting breaking changes" or "convenient stale symbols" is forbidden.

---

## 10. Transition Selection Hierarchy

For each eligible repository $R$, candidate transitions $(C_{\text{base}} \to C_{\text{target}})$ are sampled according to a strict priority hierarchy:

### Tier 1 (Release Tags — Preferred):
Consecutive stable release tags (e.g., $v_{i} \to v_{i+1}$), sorted chronologically by tag release date. Alpha, beta, and release-candidate tags are excluded unless the project standardizes on them.

### Tier 2 (Chronological Commit Windows):
If fewer than 2 release tags exist:
- Chronologically ordered non-merge commits.
- Minimum commit distance: $\Delta_{\text{commits}} \ge 20$ non-merge commits.
- Minimum temporal distance: $\Delta t \ge 14$ days.

Fixed parameters: $\Delta_{\text{commits}} = 20$, $\Delta t = 14\text{ days}$.

---

## 11. Per-Repository Caps & Anti-Dominance Invariants

To guarantee that no single massive repository dominates the benchmark statistics:
- **Maximum Transitions per Repository**: $M_{\text{trans/repo}} \le 3$
- **Maximum Final Benchmark Claims per Repository**: $M_{\text{claims/repo}} \le 8$

---

## 12. Separation of Technical Screening from Validity Adjudication

The pipeline maintains a strict operational separation between technical feasibility screening and validity adjudication:

```
[Accepted Repository]
         |
         v
[Transition Sampling]
         |
         v
[Technical Screening]  --> Allowed exclusions: checkout failure, missing commits, AST parse errors
         |
         v
[Memory Claim Construction (Base Only)]
         |
         v
[Gold Adjudication (Target State)]
```

Technical screening cannot reject transitions due to lack of stale claims or algorithm difficulty.

---

## 13. Historical Memory Provenance & Base-Truth Invariant

Every formal memory claim represents a factual proposition about the software state at $C_{\text{base}}$.

### Mandatory Invariant:
$$\text{Truth}(Claim, C_{\text{base}}) = \text{VERIFIED}$$

If a candidate claim cannot be verified as true at the base commit, it is classified as `EXCLUDE_INVALID_HISTORICAL_MEMORY` and excluded from the benchmark. It is never labeled as `VALID` or `STALE`.

---

## 14. Information Isolation of Memory Author

The **Memory Author** agent or human annotator operating at $C_{\text{base}}$ must be strictly sandboxed:
- **Permitted Inputs**: $C_{\text{base}}$ git snapshot, base source code, base test suite, base docstrings.
- **Forbidden Inputs**: Target commit $C_{\text{target}}$, git diff $(C_{\text{base}} \to C_{\text{target}})$, target test outcomes, future changelogs, gold labels, and RoleMem predictions.

This guarantees that claims reflect authentic, unpolluted historical memories.

---

## 15. Memory Author vs. Validity Adjudicator Separation

The pipeline enforces distinct roles with isolated information contexts:
- **Memory Author Role**: Observes only $C_{\text{base}}$ state; outputs structured memory claims with base evidence bindings.
- **Validity Adjudicator Role**: Receives the frozen base claim and evaluates its temporal validity at $C_{\text{target}}$ against target evidence.

---

## 16. Structured Claim Representation & Frozen Claim Types

Claims must conform to the frozen V2.2 structured claim schema (`src/claim_validity/types.py`). No new `ClaimType` may be introduced.

### Eligible Frozen Claim Types:
1. `SYMBOL_EXISTS`: Verification of top-level or module symbol presence.
2. `ATTRIBUTE_EXISTS`: Verification of class/instance attribute presence.
3. `IMPORT_PATH_VALID`: Verification of module/symbol import path accessibility.
4. `CALLABLE`: Verification of callable interface status.
5. `SIGNATURE_COMPATIBLE`: Verification of positional/keyword argument compatibility.
6. `DEFAULT_VALUE`: Verification of parameter or configuration default values.
7. `RETURN_VALUE`: Verification of returned type or constant value.
8. `DEPRECATION_STATUS`: Verification of formal deprecation warnings or lifecycle state.
9. `BEHAVIORAL_CONTRACT`: Verification of auditable semantic execution requirements (e.g. operations, sequences, return relations).
10. `DEPENDENCY_CONTRACT`: Verification of package dependency requirements and semantic constraints.

---

## 17. Natural Language Statement & Traceability Preservation

Every formal benchmark case must preserve full bidirectional provenance:
- `raw_statement`: Natural language description of the memory claim.
- `structured_claim`: Machine-readable JSON representation of claim semantics.
- `base_evidence`: Explicit source file, AST node, or test citation verifying truth at $C_{\text{base}}$.
- `repository`: Repository name.
- `base_commit`: Commit hash of $C_{\text{base}}$.
- `target_commit`: Commit hash of $C_{\text{target}}$.
- `file_symbol_provenance`: Exact file path and qualified symbol name.

---

## 18. Anti-Artificial Quota Rule (No Forced Balancing)

The formal benchmark must represent **natural prevalence**. Artificial quotas (such as forcing an exact 50% `VALID` / 50% `STALE` distribution) are forbidden because they distort realistic software evolution distributions.

---

## 19. Primary Benchmark Track: `FORMAL-NATURAL`

- **Primary Track**: `FORMAL-NATURAL` is the definitive confirmatory benchmark.
- All cases entering `FORMAL-NATURAL` are sampled via the preregistered objective rules.
- Scientific conclusions regarding RoleMem generalizability will be drawn primarily from this track.

---

## 20. Secondary Diagnostic Track: `FORMAL-CHALLENGE`

If structurally interesting edge cases emerge (e.g., subtle behavioral semantic shifts where AST symbol presence is unchanged), they may be indexed in an optional `FORMAL-CHALLENGE` track. This track is strictly secondary and descriptive.

---

## 21. Formal Benchmark Scale Targets

- **Minimum Valid Claims**: $K_{\min} = 100$
- **Target Valid Claims**: $K_{\text{target}} = 150$
- **Maximum Valid Claims**: $K_{\max} = 200$
- **Minimum Distinct Repositories**: $\ge 20$

If rule-based generation produces fewer than 100 valid claims across $\ge 20$ repositories, `FORMAL_BENCHMARK_SHORTFALL` is recorded and pipeline halts.

---

## 22. Claim Type Distribution Caps

To prevent the benchmark from being overwhelmed by trivial presence checks:
- **Single Claim Type Cap**: No single `ClaimType` (e.g., `SYMBOL_EXISTS`) may exceed **50%** of the total formal benchmark.
- This cap is applied prior to target gold adjudication based strictly on claim schema.

---

## 23. Behavioral Contract Inclusion Standards

Behavioral claims must specify concrete, auditable semantic requirements:
- `OPERATION`: Execution of a specific method/function.
- `ATTRIBUTE_STATE`: State mutation or attribute invariance.
- `CONSTRUCTOR_ARGUMENT`: Constructor parameter handling.
- `DEFAULT_VALUE`: Default argument evaluation.
- `RETURN_RELATION`: Input-output relation.
- `SEQUENCE`: Statement-level execution ordering ($lineno(op_1) < lineno(op_2)$).

Vague assertions ("functions properly") are prohibited.

---

## 24. Dependency Contract Inclusion Standards

Dependency claims must explicitly specify:
- `subject`: The module or function relying on the dependency.
- `dependency`: The external package or module name.
- `relation`: The exact usage pattern or version constraint.

Dependency claims must be derived base-first, not retroactively generated from target diffs.

---

## 25. Opaque Case Identifier Specification

Formal external evaluation case IDs must follow the format:
$$\text{Case ID} = \text{FV22-}\mathbf{DDDDDD}\quad (\text{e.g., }\texttt{FV22-000001})$$

The case ID contains zero encoded information regarding repository, category, label, or transition. Private mappings are maintained in a physically separated file.

---

## 26. Physical Gold Isolation & Three-File Protocol

Formal evaluation data is partitioned into three distinct files:
1. `data/formal_v2_2/formal_inputs.jsonl`: Contains only opaque case IDs, base state representations, structured claims, and transition metadata. Delivered to the agent during evaluation.
2. `data/formal_v2_2/formal_gold_private.jsonl`: Contains case IDs, ground-truth validity labels (`VALID`, `STALE`, `UNRESOLVED_GOLD`), and gold evidence citations. Sealed until predictions are hashed.
3. `data/formal_v2_2/formal_case_map_private.json`: Contains the private mapping from opaque case IDs to repository names and commit hashes.

---

## 27. Gold Adjudication Labels & `UNRESOLVED_GOLD` Rule

Target validity ground-truth labels:
- `VALID`: Claim remains fully true and compatible at $C_{\text{target}}$.
- `STALE`: Claim is contradicted, broken, removed, or invalidated at $C_{\text{target}}$.
- `UNRESOLVED_GOLD`: Evidence is insufficient to definitively classify validity.

`UNRESOLVED_GOLD` cases are excluded from primary binary scoring metrics and reported separately as data quality diagnostics.

---

## 28. Gold Evidence Preference Hierarchy

Ground truth adjudication must record evidence according to the following preference hierarchy:
1. **Target Source / AST Analysis**: Direct syntax/AST evidence in target codebase.
2. **Repository-Native Target Tests**: Passing/failing test suites executed at $C_{\text{target}}$.
3. **Target Observable Runtime Behavior**: Isolated executable witnesses at $C_{\text{target}}$.
4. **Dependency-Local Source Evidence**: Upstream/downstream package code.
5. **Release Documentation & Changelogs**: Official upstream release notes.
6. **Human Expert Adjudication**: Manual audit.

---

## 29. Dual Independent Adjudication & Inter-Annotator Agreement

For complex behavioral and dependency claims, two independent adjudicators must evaluate validity.
- Annotators are blind to RoleMem predictions.
- Inter-annotator agreement (Cohen's $\kappa$ and percentage agreement) must be computed and published.
- Disagreements are resolved through documented consensus review.

---

## 30. Evaluation Execution Sequence

The formal evaluation follows an immutable eight-step state progression:
1. **Freeze Formal Inputs**: Generate and lock `formal_inputs.jsonl`.
2. **Hash Formal Inputs**: Compute and log SHA256 checksum of inputs.
3. **Execute Frozen RoleMem**: Run frozen RoleMem (B50 default budget) exactly once.
4. **Save Predictions**: Record outputs to `formal_predictions.jsonl`.
5. **Hash Predictions**: Compute and log SHA256 checksum of predictions.
6. **Close Prediction Phase**: Transition state machine from `S6_PREDICTION_RUN` to `S7_GOLD_OPEN`.
7. **Unseal Gold**: Open `formal_gold_private.jsonl`.
8. **Compute Metrics**: Calculate evaluation metrics, bootstrap confidence intervals, and reports.

---

## 31. Strict One-Shot Evaluation Rule & Infrastructure Restart Invariants

The frozen algorithm may be executed on the formal benchmark **exactly once** for primary results.

### Infrastructure Restart Conditions:
A rerun is permissible **only** if:
1. An operating system crash, power failure, or fatal hardware error halted execution mid-run.
2. Zero prediction outputs were exposed or inspected.
3. The private gold file remained unsealed (`formal_data_opened == false`).
4. The incident is fully documented with system logs.

---

## 32. Post-Formal Failure & Non-Mutation Rules

If formal evaluation results expose performance limitations:
- **No In-Place Tuning**: Modifying the algorithm and rerunning on the same formal benchmark is strictly forbidden.
- The V1 formal result remains immutable.
- Any subsequent version (e.g., V2) must be evaluated on a completely new, independently preregistered and sealed benchmark.

---

## 33. Primary Metric Definitions

For a selective classifier making predictions $\hat{y} \in \{\text{VALID}, \text{STALE}, \text{UNCERTAIN}\}$ against binary ground truth $y \in \{\text{VALID}, \text{STALE}\}$:

Let $N$ be total evaluated cases, $D = \{i \mid \hat{y}_i \neq \text{UNCERTAIN}\}$ be the decided subset, and $U = \{i \mid \hat{y}_i = \text{UNCERTAIN}\}$ be the abstained subset.

1. **Coverage ($\mathcal{C}$)**:
   $$\mathcal{C} = \frac{|D|}{N}$$

2. **Selective Risk ($\mathcal{R}$)**:
   $$\mathcal{R} = \frac{1}{|D|} \sum_{i \in D} \mathbb{I}(\hat{y}_i \neq y_i)$$

3. **Accuracy Among Decided ($\text{Acc}_D$)**:
   $$\text{Acc}_D = 1 - \mathcal{R} = \frac{1}{|D|} \sum_{i \in D} \mathbb{I}(\hat{y}_i = y_i)$$

4. **Balanced Accuracy Among Decided ($\text{BAcc}_D$)**:
   $$\text{BAcc}_D = \frac{1}{2} \left( \frac{\text{TP}_D}{\text{TP}_D + \text{FN}_D} + \frac{\text{TN}_D}{\text{TN}_D + \text{FP}_D} \right)$$

5. **Matthews Correlation Coefficient Among Decided ($\text{MCC}_D$)**:
   $$\text{MCC}_D = \frac{\text{TP}_D \cdot \text{TN}_D - \text{FP}_D \cdot \text{FN}_D}{\sqrt{(\text{TP}_D + \text{FP}_D)(\text{TP}_D + \text{FN}_D)(\text{TN}_D + \text{FP}_D)(\text{TN}_D + \text{FN}_D)}}$$

6. **False Invalid Rate ($\text{FIR}$)**:
   $$\text{FIR} = \frac{|\{i \in D \mid y_i = \text{VALID} \land \hat{y}_i = \text{STALE}\}|}{|\{i \in D \mid y_i = \text{VALID}\}|}$$

7. **Stale Escape Rate ($\text{SER}$)**:
   $$\text{SER} = \frac{|\{i \in D \mid y_i = \text{STALE} \land \hat{y}_i = \text{VALID}\}|}{|\{i \in D \mid y_i = \text{STALE}\}|}$$

---

## 34. Primary Metric Priority

Because RoleMem is a selective memory classification system, **Coverage and Selective Risk form the inseparable primary metric pair**:
$$\text{Primary Goal: Maximize Coverage while Minimizing Selective Risk}$$

Reporting accuracy alone without coverage is forbidden. A trivial model with 100% accuracy on 1% coverage is uninformative.

---

## 35. Discrete Policy & Calibration Reporting

RoleMem operates on discrete evidence thresholds and policy tiers (Static $\to$ Search $\to$ Dependency $\to$ Witness $\to$ Targeted Execution). Performance will be reported across discrete escalation stages. No synthetic continuous probabilities will be fabricated post hoc.

---

## 36. Preregistered Baselines & Oracle Demarcation

The following baseline methods are preregistered for comparative evaluation:
1. **File-Level Validity**: Assumes any modification to the defining file invalidates the claim.
2. **Pure Symbol AST**: Evaluates existence via exact AST name matching at target.
3. **Dependency-Aware Static**: Incorporates static import/dependency graph tracking.
4. **RoleMem V2.1 Baseline**: Pre-escalation claim-aware hybrid model.
5. **Claim-Aware Static**: V2.2 static claim validation without dynamic evidence escalation.
6. **Claim-Aware + Selective Escalation V1 (RoleMem V2.2 Frozen)**: The proposed method.

*Note*: Oracle methods (e.g. perfect diff visibility) are labeled as theoretical upper bounds, never as deployable baselines.

---

## 37. Preregistered Pipeline Ablations

Ablations evaluate incremental evidence sources using the frozen codebase configuration:
- `Ablation 0`: Static Validation Only
- `Ablation 1`: Static + Repository Search
- `Ablation 2`: Static + Search + Dependency Inspection
- `Ablation 3`: Static + Search + Dependency + Test Discovery
- `Ablation 4`: Full V1 (Default B50: Static + Search + Dependency + Test Discovery + Targeted Execution)

---

## 38. Cost & Budget Tracking (B50 Protocol)

All primary evaluations run under the frozen default **B50 budget** (max 50 cost units per claim). The following operational cost metrics must be reported:
- `files_scanned`: Number of files inspected.
- `tests_inspected`: Number of test files/functions parsed.
- `executions`: Number of targeted sandbox executions performed.
- `execution_wall_time_sec`: Total wall clock time spent in execution.
- `action_count`: Total planner actions invoked.
- `abstentions`: Count of cases where budget was exhausted or evidence remained inconclusive.

---

## 39. Repository-Level Clustered Bootstrap Confidence Intervals

Because claims sampled from the same repository share common codebases and dependency structures, observations are clustered by repository.

### Bootstrap Protocol:
- **Resampling Unit**: Repository clusters (cluster bootstrap).
- **Number of Bootstrap Replicates**: $B = 5000$.
- **Random Seed**: `3407`.
- **Confidence Level**: $95\%$ two-sided percentile confidence intervals.

---

## 40. Dual Reporting: Micro (Claim-Level) and Macro (Repository-Level)

Results must be reported across both aggregation levels:
- **Micro Metrics**: Computed across all pooled claims ($N$ claims).
- **Macro Metrics**: Metric computed per repository, then averaged across all repositories ($M$ repositories):
  $$\text{Metric}_{\text{macro}} = \frac{1}{M} \sum_{r=1}^M \text{Metric}(r)$$

This ensures large repositories do not mask weaknesses in smaller ones.

---

## 41. Label Prevalence & Class Imbalance Transparency

Formal reports must explicitly document:
- Overall count and proportion of `VALID`, `STALE`, and `UNRESOLVED_GOLD` cases.
- Breakdown of label prevalence by repository, claim type, and transition distance.

---

## 42. Descriptive Diagnostic Subsets vs. Confirmatory Results

Subgroup breakdowns (e.g., symbol modified vs. unmodified, behavioral contracts vs. structural imports) are descriptive diagnostics. They provide scientific insight but cannot supersede the primary confirmatory `FORMAL-NATURAL` result.

---

## 43. Pre-Planned Hypotheses vs. Exploratory Post-Hoc Slices

- **Confirmatory Hypotheses**:
  - $H_1$: Frozen RoleMem V2.2 achieves $\ge 80\%$ Coverage with $\le 5\%$ Selective Risk on `FORMAL-NATURAL`.
  - $H_2$: Selective evidence escalation significantly outperforms static-only claim validation in coverage without increasing selective risk.
- **Exploratory Slices**: Any unanticipated data slice evaluated after gold opening must be explicitly designated as `EXPLORATORY_POST_HOC`.

---

## 44. Formal Data Firewall State Machine

The lifecycle of formal benchmark execution follows a strictly enforced 9-state machine:

```
[S0_PREREGISTRATION]           <-- CURRENT TASK TERMINATION POINT
        |
        v
[S1_REPOSITORY_DISCOVERY]
        |
        v
[S2_TRANSITION_MINING]
        |
        v
[S3_CLAIM_CONSTRUCTION]
        |
        v
[S4_GOLD_ADJUDICATION]
        |
        v
[S5_FORMAL_INPUT_FREEZE]
        |
        v
[S6_PREDICTION_RUN]
        |
        v
[S7_GOLD_OPEN]
        |
        v
[S8_SCORING_COMPLETE]
```

---

## 45. Current Milestone Termination Invariant

This task terminates strictly at **`S0_PREREGISTRATION`**.
- Formal candidate repositories selected: **0**
- Formal transitions inspected: **0**
- Formal claims generated: **0**
- Formal gold labels created: **0**
- `formal_data_opened`: **`false`**

---

## 46. Machine-Readable Manifest Reference

The machine-readable configuration corresponding to this protocol is stored at:
[`data/formal_v2_2/protocol_preregistration.json`](file:///code/rolemem-agent-memory/data/formal_v2_2/protocol_preregistration.json)

---

## 47. Human-Readable Protocol Integrity

This document (`reports/protocol-v2.2-formal-benchmark-preregistration.md`) is checked for completeness and consistency against the machine-readable manifest and the frozen algorithm constraints.

---

## 48. Automated Preregistration Verifier Reference

Automated verification of this preregistration milestone is implemented in:
[`scripts/verify_v2_2_formal_preregistration.py`](file:///code/rolemem-agent-memory/scripts/verify_v2_2_formal_preregistration.py)

---

## 49. Anti-Leak & Accidental Exposure Scanner

The automated verifier incorporates an anti-leak scanner that audits all repository files for:
- GitHub URLs or repository names outside the frozen 29-repository contaminated universe.
- Unregistered commit SHAs.
- Premature formal case IDs or gold annotations.

---

## 50. Preregistration Freeze Tag Specification

Upon successful verification of this protocol, an immutable Git tag will be created:
```
protocol-v2.2-formal-preregistration
```
This tag anchors the protocol before discovery begins.

---

## 51. Firewall State Invariant at Preregistration

The formal firewall manifest ([`data/freeze/protocol_v2_2_formal_data_firewall.json`](file:///code/rolemem-agent-memory/data/freeze/protocol_v2_2_formal_data_firewall.json)) records:
```json
{
  "formal_protocol_preregistered": true,
  "formal_state": "S0_PREREGISTRATION",
  "formal_data_opened": false,
  "formal_repository_list": null,
  "formal_case_ids": null,
  "formal_gold": null
}
```

---

## 52. Formal Milestone Status Summary

```text
==================================================
ROLEMEM V2.2 — FORMAL PREREGISTRATION SUMMARY
==================================================
Algorithm Freeze:                PASS (fe62749b)
Freeze Closure:                  PASS (da105f95)
Formal Preregistration:          PASS (RM-PREREG-V2.2-001)

Formal State:                    S0_PREREGISTRATION
Formal Repositories Selected:    0
Formal Transitions Inspected:    0
Formal Claims Created:           0
Formal Gold Labels Created:      0

formal_data_opened:              false
==================================================
```
