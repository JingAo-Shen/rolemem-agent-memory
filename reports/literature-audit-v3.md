# Gate 6 Report: Literature Audit v3

**Gate Status**: `PASSED`  
**Date**: September 2026  
**Auditor**: RoleMem Hardening Suite  
**Data File**: `reports/literature-v3.csv`

---

## 1. Critical Errors Identified & Corrected

1. **Retraction of `arXiv:2501.08920`**:
   - *Previous Error*: Misidentified as DeepSeek-R1 or AgentRunbook in early notes.
   - *Official Verification*: `arXiv:2501.08920` is officially *Simulating inverse patchy colloid models* (Soft Condensed Matter Physics by D. Notarmuzi et al.).
   - *Correction*: Completely expunged from agent memory bibliography. DeepSeek-R1 is correctly referenced as `arXiv:2501.12948`.
2. **Disambiguation of AgentRunbook**:
   - AgentRunbook is properly classified as a baseline workflow method evaluated within *LongMemEval-V2* (arXiv:2605.12493), rather than a fabricated standalone paper.
3. **Formal Verification of AgeMem**:
   - *Exact Official Title*: *Agentic Memory: Learning Unified Long-Term and Short-Term Memory Management for Large Language Model Agents*
   - *arXiv ID*: `arXiv:2601.01885`
   - *Repository*: `github.com/y1y5/AgeMem`
   - *Mechanism*: RL training via Step-wise GRPO exposing memory operations directly into the action space.
4. **Disambiguation of MemGym**:
   - Distinguished *MemGym* (2026, long-horizon LLM agent memory benchmark with MemRM) from *Memory Gym* (2025 JMLR Deep RL POMDP benchmark).

---

## 2. Verified Core Literature Summary

| ID | Title | Venue / Identifier | Key Finding Relevant to RoleMem |
| :--- | :--- | :--- | :--- |
| **P01** | *When Retrieval Hurts Code Completion: A Diagnostic Study of Stale Repository Context* | arXiv:2605.14478 (2026) | Proves that stale code retrieved from earlier git commits misleads code generation models into producing obsolete, incompatible code. Directly motivates RoleMem's artifact hash invalidation. |
| **P02** | *MemCollab: Cross-Agent Memory Collaboration via Contrastive Trajectory Distillation* | arXiv:2603.23234 (2026) | Demonstrates sharing memory across heterogeneous agent models via contrastive distillation, reinforcing the need for cross-model task handoff memory frameworks. |
| **P03** | *Evaluating Memory in LLM Agents via Incremental Multi-Turn Interactions (MemoryAgentBench)* | ICLR 2026 | Establishes 4 core memory axes: Accurate Retrieval, Test-time Learning, Long-range Understanding, and Selective Forgetting. |
| **P04** | *MemGym: Evaluating Dynamic Memory Formation in Long-Horizon Agent Workflows* | arXiv 2026 | Evaluates dynamic memory formation in coding (SWE-Gym) and computer use (WebArena) using calibrated reward model MemRM. |
| **P06** | *LongMemEval-V2: Evaluating Long-Term Agent Memory Toward Experienced Colleagues* | arXiv:2605.12493 (2026) | Probes dynamic state tracking, environment gotchas, and workflow memory across 451 interactive web agent tasks. |
| **P07** | *ToolAtlas: Learning Once, Reusing Everywhere with Tool-Side Memory* | arXiv:2607.11126 (2026) | Evaluates persistent tool knowledge across ToolBench, RestBench, and ComplexToolEnv. |
| **P10** | *Agentic Memory (AgeMem)* | arXiv:2601.01885 (2026) | Formulates memory update and discarding as agent action-space tools optimized via reinforcement learning. |

All unconfirmed external URLs or preliminary preprint details are explicitly designated as `UNVERIFIED` in `reports/literature-v3.csv`.
