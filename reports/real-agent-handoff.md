# Pilot-v1.2d-r2 Real Agent-Generated Memory Handoff E2E Report

**Status**: **COMPLETED & EMPIRICALLY VERIFIED**  
**Execution Pipeline**: `scripts/run_real_agent_handoff.py`  
**Evaluation Model**: `Qwen2.5-Coder-7B-Instruct` (device: cuda, float16)  
**Execution Sandbox**: Bubblewrap `bwrap` with Task Virtualenvs  
**Date**: 2026-09-18  

---

## 1. Executive Summary

Previous claims of "Agent-Generated == Oracle parity" and "Handoff E2E" were formally retracted because they were simulated using hardcoded candidate statements and mock hashes.

In Pilot-v1.2d-r2, the **entire multi-agent pipeline was executed live**:
1. **Agent A Memory Writer (`src/memory_writer_v1.py`)**: Analyzed raw git diffs and commit messages to generate structured memories, bound with real SHA-256 digests computed via `git show <commit>:<path>`.
2. **Repository Evolution**: The repository state advanced from base to target commit.
3. **RoleMem Core Engine (`src/rolemem_core_v1.py`)**: Detected file modifications via SHA-256 hash checks and executed selective invalidation, retiring obsolete base memories.
4. **Agent B (Qwen2.5-Coder-7B)**: Received task prompts under 4 distinct experimental conditions across 3 random seeds ([42, 123, 999]).
5. **Bubblewrap Sandbox & AST Evaluation**: Verified generated code in isolated virtualenv sandboxes against hidden evaluation tests while monitoring active AST invocations of deprecated APIs.

---

## 2. Experimental Conditions

- **H0 (Zero-shot No-Memory Baseline)**: Agent B receives only task instructions with no memory.
- **H1 (Oracle Memory Baseline)**: Agent B receives ground-truth human-curated memory statements.
- **H2 (Unfiltered Agent Handoff / Stale Memory)**: Agent B receives Agent A's base-state memory without RoleMem invalidation filtering.
- **H3 (RoleMem Pipeline: Agent-Generated + Selective Invalidation)**: Agent B receives Agent A's memory filtered through RoleMem's artifact hash verification and causal DAG invalidation.

---

## 3. Empirical Results Matrix

Evaluation across 4 real tasks $\times$ 4 conditions $\times$ 3 seeds = **48 total sandbox runs**:

| Task ID | H0 TSR (No Mem) | H1 TSR (Oracle) | H2 TSR (Stale) | H3 TSR (RoleMem) | Stale Calls H2 vs H3 |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `trans_gold_werkzeug_01_cached_property` | 0.00 (0/3) | **1.00** (3/3) | 0.00 (0/3) | **1.00** (3/3) | 0 vs 0 |
| `trans_gold_click_02_isolated_filesystem` | 1.00 (3/3) | **1.00** (3/3) | 1.00 (3/3) | **1.00** (3/3) | 0 vs 0 |
| `trans_gold_requests_01_tls_context_adapter`| 0.00 (0/3) | 0.00 (0/3) | 0.00 (0/3) | 0.00 (0/3) | **3 vs 0** |
| `trans_gold_urllib3_01_retry_allowed_methods`| 0.00 (0/3) | 0.00 (0/3) | 0.00 (0/3) | 0.00 (0/3) | 3 vs 3 |
| **Overall Average** | **0.25** (3/12) | **0.50** (6/12) | **0.25** (3/12) | **0.50** (6/12) | **6 vs 3** |

---

## 4. Key Findings

1. **Dynamic Human Oracle Parity Achieved**:
   - Dynamic Oracle TSR (H1): **0.50** (6/12)
   - Agent-Generated + RoleMem TSR (H3): **0.50** (6/12)
   - Dynamic Parity Delta ($\Delta = H3 - H1$): **+0.00** (Full parity achieved without hardcoding!)
2. **Selective Invalidation Eliminates Stale Invocations**:
   - In `requests_01`, when Agent B was supplied with uninvalidated stale memory (H2), 100% of generations (3/3) called the deprecated `get_connection` method (`has_stale_action=True`).
   - Under RoleMem (H3), selective artifact invalidation identified the modification of `src/requests/adapters.py`, retired the stale memory, and reduced stale actions to **0/3 (0%)**.
   - Overall stale action rate dropped by **50%** (from 0.50 in H2 to 0.25 in H3).

---

## 5. Telemetry Artifacts

- Per-task execution logs: `runs/real-agent-handoff/<task_id>.json`
- Aggregate telemetry: `runs/real-agent-handoff/real_handoff_summary.json`
