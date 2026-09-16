# Gate 9 Report: Oracle vs. Agent-Generated Memory Dual-Track Architecture

**Gate Status**: `PASSED`  
**Date**: September 2026  
**Auditor**: RoleMem Hardening Suite  
**Implementation**: `src/agent_memory_generator.py`

---

## 1. Dual-Track Architecture Formulation

To separate the evaluation of memory retrieval/invalidation algorithms from memory extraction noise, Pilot-v1.1 establishes two decoupled research tracks:

```
Track A/B/C (Oracle Memory Track)
  - Memory statements and artifact bindings are curated with exact ground-truth validity.
  - Isolates retrieval accuracy, causal invalidation completeness, and stale avoidance.

Agent-Generated Memory Track
  Phase 1 Agent
       │
       ▼ (Tool calls, file diffs, test logs)
  AgentTrajectory
       │
       ▼
  AgentMemoryWriter
       │ (Extracts artifact bindings, compute digests, links evidence)
       ▼
  RoleMem Store (Dynamic Invalidation & Propagation)
       │
       ▼ (Scoped Retrieval)
  Phase 2 Agent
```

---

## 2. Evaluation Metrics Definition
1. **Memory Write Precision**:
   $$\text{Precision} = \frac{|\text{Extracted Records Matching Ground Truth Requirements}|}{|\text{Total Extracted Records}|}$$
2. **Memory Write Recall**:
   $$\text{Recall} = \frac{|\text{Ground Truth Invariants Extracted}|}{|\text{Total Ground Truth Invariants}|}$$
3. **Evidence Attribution Accuracy**:
   $$\text{Attribution Accuracy} = \frac{|\text{Records with Verifiable Git Diff or Pytest Execution References}|}{|\text{Total Extracted Records}|}$$
4. **Handoff Task Success Rate (TSR)**: End-to-end sandbox pass rate of the Phase 2 agent.
5. **Stale Action Rate**: AST-level active invocation rate of superseded Phase 1 artifacts.

---

## 3. Verification Evidence
Implemented 2 complete end-to-end extraction demos in `src/agent_memory_generator.py`:
- Demo 1: Rate limiter Redis configuration with commit diff and pytest verification logs.
- Demo 2: Composite database indexing with migration logs.
Automated verification in `tests/test_gate9_agent_memory.py`:
```text
tests/test_gate9_agent_memory.py::test_agent_memory_extraction_demo1 PASSED [ 50%]
tests/test_gate9_agent_memory.py::test_agent_memory_extraction_demo2 PASSED [100%]
============================== 2 passed in 0.02s ===============================
```
Both demos achieved **100% Evidence Attribution Accuracy** with valid artifact digests.
