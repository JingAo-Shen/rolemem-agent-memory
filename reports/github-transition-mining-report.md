# Pilot-v1.2 Real GitHub Transition Mining Report

**Stage**: Pilot-v1.2 Real GitHub Transition Mining  
**Date**: September 2026  
**Auditor**: RoleMem Benchmark Infrastructure Engine  
**Dataset Artifacts**:  
- Raw Mined Candidates: `data/candidates/mined_raw.jsonl` (44 items)  
- Reviewed Candidates: `data/reviewed/reviewed_transitions.jsonl` (44 items)  
- Benchmark Status: **Candidate Pool Established; Benchmark Freeze Deferred**

---

## 1. Mining Strategy & Quality Governance

In strict compliance with Pilot-v1.2 scientific mandates, **zero synthetic template copying** was utilized. All candidates originate from genuine, public open-source Python repositories with complete commit history, traceable pull requests, and automated test suites.

### Repository Diversity & License Distribution (15 Repositories)

| Repository | License | Candidates Mined | Primary Task Families |
| :--- | :--- | :--- | :--- |
| `psf/requests` | Apache-2.0 | 3 | Dependency unvendoring, URI normalization, Exception hierarchy |
| `urllib3/urllib3` | MIT | 3 | Case-insensitive headers, six removal, TLS client default |
| `pallets/flask` | BSD-3-Clause | 3 | Helper relocation, ContextVars migration, JSON provider |
| `pallets/werkzeug` | BSD-3-Clause | 3 | Safe comparison removal, URL quoting, JSON body parsing |
| `pallets/jinja` | BSD-3-Clause | 3 | Markup unvendoring, Filter decorators, Autoescape policy |
| `pallets/click` | BSD-3-Clause | 3 | Terminal inspection, Choice casing, Error stream routing |
| `encode/httpx` | BSD-3-Clause | 3 | Transport architecture, Async close lifecycle, Granular timeouts |
| `encode/starlette` | BSD-3-Clause | 3 | Serializer removal, Middleware context, Unbundled GraphQL |
| `tiangolo/fastapi` | MIT | 3 | Lifespan events, Pydantic v2 model_dump, Dependency cleanup |
| `pydantic/pydantic` | MIT | 3 | Field validator modes, ConfigDict migration, Schema generation |
| `sqlalchemy/sqlalchemy` | MIT | 3 | 2.0 select query execution, DeclarativeBase class, Autocommit removal |
| `celery/celery` | BSD-3-Clause | 3 | Lowercase configuration, Task module deprecation, Late acknowledgment |
| `pytest-dev/pytest` | MIT | 3 | Yield fixture deprecation, Pathlib tmp_path, Node marker inspection |
| `pyca/cryptography` | Apache-2.0 / BSD | 3 | Backend argument removal, Legacy cipher deprecation, KDF standard |
| `Textualize/rich` | MIT | 2 | Text alignment delegation, Task ID NewType enforcement |
| **Total** | — | **44** | **15 Repositories Represented** |

No repository exceeds 7% of the candidate dataset, ensuring statistical cluster independence (`cluster = repository`).

---

## 2. Transition Taxonomy Distribution

| Transition Category | Count | Primary Operational Impact on Agents |
| :--- | :--- | :--- |
| **API Signature & Method Renames** | 16 | Stale methods (e.g. `schema()`, `get_closest_marker()`) crash at invocation |
| **Dependency & Unvendoring Shifts** | 9 | Stale imports (e.g. `requests.packages.urllib3`, `six`) trigger `ImportError` |
| **Configuration & Setting Migrations** | 8 | Obsolete keys (e.g. `CELERY_BROKER_URL`, `class Config`) are ignored or rejected |
| **Behavioral Contract & Lifecycle Changes** | 6 | Deprecated hooks (e.g. `@app.on_event`, `autocommit`) fail silently or crash |
| **Security & Cryptographic Requirement Hardening** | 5 | Insecure defaults (e.g. `PROTOCOL_TLSv1`, `Blowfish`) rejected by modern libraries |

---

## 3. Track Classification Breakdown

- **Track A (Stale-Adversarial / Memory Safety)**: **33 Candidates**
  - Evaluates whether an agent can avoid obsolete code patterns when presented with historical artifacts from prior git revisions.
- **Track B (Memory-Required / Memory Utility)**: **5 Candidates**
  - Evaluates adherence to project-internal architecture decisions (ADRs) that cannot be inferred from standard Python semantics.
- **Track AB (Dual Utility + Stale Risk)**: **6 Candidates**
  - Simultaneously probes for deprecated usage while requiring project-specific configuration conventions.

---

## 4. Schema Compliance & Data Leakage Review

All 44 candidates were audited against the formal 33-field schema.

### Data Leakage Audit:
- **Zero Prompt Leakage**: Task instructions in `current_task` describe the functional requirement without embedding the target method names, deprecation warnings, or hidden assertions.
- **Evidence Verification**: Every transition records explicit `issue_url`, `pr_url`, `test_evidence_source`, and commit SHAs (`base_commit`, `history_commit`, `transition_commit`, `target_commit`).
- **Leakage Status**: 100% evaluated with `leakage_review = "PASS"`.

---

## 5. Candidate Pool Status

- Candidates are strictly isolated in `data/candidates/` and `data/reviewed/`.
- **Benchmark Freeze**: Intentionally **NOT** executed during Pilot-v1.2, adhering strictly to the phase contract.
