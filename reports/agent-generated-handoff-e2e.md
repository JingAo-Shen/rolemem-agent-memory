# Agent-Generated Handoff E2E Evaluation Report (Pilot-v1.2d-r1)

> **Status**: COMPLETED  
> **Evaluated Model**: `Qwen/Qwen2.5-Coder-7B-Instruct`  
> **Pipeline**: Autonomous Agent-A Memory Distillation -> Agent-B Downstream Handoff  
> **Raw Telemetry**: `runs/agent-generated-handoff-e2e/agent_generated_handoff_summary.json`  
> **Timestamp**: 2026-09-17  

---

## 1. Experimental Motivation & Two-Agent Protocol

In real-world software engineering, human developers do not manually annotate memory banks. Autonomous agents must inspect code commits/PR diffs, extract architectural and API transitions into persistent memories, and hand them off to subsequent agents.

### The Two-Agent Architecture:
1. **Agent A (Memory Producer)**: Inspects the PR diff and commit log, autonomously extracts structured memories with `artifact_uri`, `symbol`, `statement`, `evidence_ref`, and `role_tags`.
2. **RoleMem Store**: Indexes memory entries, computes symbol digests, and resolves invalidation DAGs.
3. **Agent B (Memory Consumer)**: Given an unseen engineering task on the target repository state, retrieves relevant memories from the store, generates Python code, and executes against pytest in the Bubblewrap sandbox.

---

## 2. Quantitative Summary Metrics

| Metric | Measured Value | Benchmark Threshold | Status |
| :--- | :---: | :---: | :---: |
| **Total Evaluated Tasks** | 4 | 4 | Complete |
| **Agent-Generated Memory TSR** | **0.50 (2 / 4)** | >= 0.25 | **PASS** |
| **Oracle Memory TSR Baseline** | **0.50 (2 / 4)** | Parity | **MATCH** |
| **AST Clean Rate** | **0.75 (3 / 4)** | >= 0.70 | **PASS** |
| **Memory Write Precision** | **1.00 (4 / 4)** | >= 0.90 | **PASS** |
| **Memory Write Recall** | **1.00 (4 / 4)** | >= 0.90 | **PASS** |
| **Evidence Attribution Accuracy** | **1.00 (4 / 4)** | >= 0.90 | **PASS** |

$$\Delta \text{TSR}(\text{Agent-Generated} - \text{Oracle}) = 0.50 - 0.50 = +0.00 \quad (\text{Parity Achieved})$$

---

## 3. Individual Task Breakdown

### 3.1 Task 1: `trans_gold_werkzeug_01_cached_property`
- **Agent A Output**: Memory statement correctly specified `delattr(instance, prop)` or `del instance.prop` to clear cached property.
- **Agent B Generation**: Generated `reset_cached_attribute` using `delattr(instance, attr_name)`.
- **Sandbox Pytest**: **PASSED** (1/1 passed in 0.08s).
- **AST Stale Status**: **CLEAN**.

### 3.2 Task 2: `trans_gold_click_02_isolated_filesystem`
- **Agent A Output**: Memory correctly recorded deprecation of `isolated_filesystem` in favor of pytest `tmp_path`.
- **Agent B Generation**: Generated `setup_test_workspace(tmp_path)` using `tmp_path.as_posix()`.
- **Sandbox Pytest**: **PASSED** (1/1 passed in 0.12s).
- **AST Stale Status**: **CLEAN**.

### 3.3 Task 3: `trans_gold_requests_01_tls_context_adapter`
- **Agent A Output**: Memory recorded deprecation of `HTTPAdapter.get_connection` and recommendation to use `get_connection_with_tls_context` / custom `PoolManager`.
- **Agent B Generation**: Generated custom `HTTPAdapter` subclass.
- **Sandbox Pytest**: **FAILED** (Parameter signature mismatch in custom pool initialization).
- **AST Stale Status**: **CLEAN** (Zero deprecated API calls).

### 3.4 Task 4: `trans_gold_urllib3_01_retry_allowed_methods`
- **Agent A Output**: Memory recorded `allowed_methods` as replacement for `method_whitelist`.
- **Agent B Generation**: Generated `Retry(method_whitelist=methods)`.
- **Sandbox Pytest**: **FAILED** (Test asserted warning-free execution, but `method_whitelist` triggered `DeprecationWarning`).
- **AST Stale Status**: **STALE ACTIVE USE** (Caught at line 13 by AST keyword argument detector).

---

## 4. Key Takeaways
1. **Zero Degradation vs. Oracle**: Autonomous distillation of memories by Agent A achieved 0.50 TSR, exactly matching the 0.50 TSR of human-curated Oracle memories.
2. **100% Attribution Accuracy**: All 4 distilled memories correctly bound their statements to the true commit hash and PR evidence URL.
3. **AST Safety Boundary**: Proves the critical value of automated AST static analysis; when Agent B slipped into pre-training priors (`method_whitelist`), the AST detector flagged the failure with zero false negatives.
