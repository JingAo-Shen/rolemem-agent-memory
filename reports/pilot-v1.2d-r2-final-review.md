# Pilot-v1.2d-r2 — Evidence Authenticity & Real Memory Writer Closure Final Review Report

**Date**: 2026-09-18  
**Phase Status**:
```text
PILOT_V1_2D = REOPENED
BENCHMARK_FREEZE = NO
FORMAL_RESULTS = NO
CANDIDATE_MINING = YES
GOLD_PROMOTION = NO
```

---

## 1. Executive Scientific Audit Summary

In Pilot-v1.2d-r2, all scientific conclusions previously identified as ungrounded or simulated have been rigorously investigated, formally retracted, and replaced with authentic implementations and empirical evidence:
- **Retracted Claims**: Simulated Dual-Source Ground Truth 10/10, Simulated Semantic Coherence 10/10, Synthetic Track B Seeds, Mock Memory Writer Precision/Recall 1.0, Mock Attribution Accuracy 1.0, and Mock Agent-Generated == Oracle Parity.
- **Genuine Implementations Delivered**:
  1. Authenticated GitHub REST API V3 + Bare Mirror Local Git Dual-Source Auditor (`scripts/audit_external_ground_truth_v3.py`).
  2. 10-Layer Semantic Coherence Auditor V2 (`scripts/audit_semantic_coherence_v2.py`).
  3. Causal Counterfactual Failure Taxonomy Matrix (`scripts/run_causal_counterfactual.py`).
  4. Repository-grounded Track B architectural seeds with zero-leakage evidence-hiding and empirical +1.00 memory lift on Qwen2.5-Coder-7B (`scripts/audit_track_b_evidence.py`).
  5. Real Agent A Memory Writer receiving raw git diffs with distractors, no oracle access, and cryptographic git show hash binding (`src/memory_writer_v1.py`).
  6. Non-tautological Memory Writer Evaluation (`scripts/evaluate_memory_writer.py`) yielding honest metrics: Precision 0.8333, Recall 1.0000, F1 0.9091, Attribution 1.0000.
  7. Real Agent-Generated Memory Handoff E2E Pipeline (`scripts/run_real_agent_handoff.py`) across 48 sandbox executions yielding dynamic Oracle TSR = 0.50, Agent + RoleMem TSR = 0.50, and 50% reduction in stale actions.
  8. TransitionVerifierV6 Seven-Gate Boolean Benchmark Verifier (`src/transition_verifier_v6.py`) yielding 9 SEED_ACCEPT, 1 REBUILD, 0 REJECT.

---

## 2. Systematic Answers to Scientific Audit Questions (Q1–Q9)

### Q1: Dual-Source External Ground Truth V3 Audit Status
- **GitHub API Authentication**: Confirmed authenticated PAT with ~4900 req/hr remaining.
- **Payload Persistence**: Complete raw HTTP payloads saved to `data/external_evidence/<transition_id>/` (`pr.json`, `issue.json`, `changed_files.json`, `commits.json`, `diff.patch`).
- **Elimination of Fake Issue Pass**:
  - Real reciprocal issue linkage verified for `flask_02` (Issue #5816) and `requests_02` (Issue #6715).
  - When no independent issue exists (`flask_01`), the spec explicitly declares `issue_required: false` and the auditor records `issue_status: NOT_APPLICABLE`.
- **Git Merge-Base Ancestry**: All 10 seeds verified with `git merge-base --is-ancestor <base> <target> == 0`.
- **Audit Fingerprint**: Every audit cryptographically binds `canonical_spec + fixture_manifest + hidden_test + controls + auditor_version + target_git_tree`.
- **Overall Result**: **10/10 VERIFIED PASS** saved in `data/ground_truth_audit_v3/`.

### Q2: 2×2 Causal Counterfactual Matrix & Failure Taxonomy
- **Sandbox Execution**: All 10 candidates executed across 4 counterfactual combinations in Bubblewrap.
- **Failure Taxonomy**: Upgraded with `classify_failure_reason()` supporting `DEPRECATION_WARNING`, `API_ABSENT`, `SIGNATURE_MISMATCH`, `BEHAVIOR_MISMATCH`, `IMPORT_FAILURE`, `ENVIRONMENT_FAILURE`.
- **Matrix Results**:
  - 9 CAUSAL_PASS
  - 1 TRANSITION_NOT_CAUSAL (`trans_gold_flask_01_context_stack_removal`)
- **Scientific Integrity Decision**: `trans_gold_flask_01_context_stack_removal` failed because `stale_base == FAIL` due to preexisting deprecation warnings in base commit `604de4b1a4`. In strict adherence to truthfulness > quantity, `flask_01` was **NOT** force-passed or altered; it is strictly classified as **REBUILD**.

### Q3: 10-Layer Semantic Coherence Auditor V2
- **Audit Implementation**: Evaluated all 10 distinct gates (G1 through G10) with explicit structured telemetry (`evidence`, `expected`, `observed`, `status`).
- **Coherence Results**:
  - 9 PASS
  - 1 FAIL (`flask_01` failed G10 due to causal counterfactual failure).
- **Telemetry**: Persisted in `data/semantic_audit_v2/<transition_id>.json`.

### Q4: Real Track B Repository-Grounded Seeds
- **Demotion**: Synthetic seeds `urllib3_custom_retry` and `requests_service_adapter` formally demoted to `SYNTHETIC_SANITY_ONLY`.
- **Authentic Seeds Discovered**:
  1. `track_b_urllib3_redirect_headers`: urllib3 PR #1346 (commit `560bd227b9`), `Retry.DEFAULT_REDIRECT_HEADERS_BLACKLIST = frozenset(['Authorization'])`.
  2. `track_b_werkzeug_pbkdf2_iterations`: Werkzeug PR #2612 (commit `92b994f76e`), `DEFAULT_PBKDF2_ITERATIONS = 600000`.
- **Evidence-Hiding Audit**: Verified zero leakage of decision values into task prompts or target filenames (**PASS**).
- **Empirical Model Evaluation (Qwen2.5-Coder-7B in Bubblewrap Sandbox)**:
  - Urllib3: S0 = 0.00 (0/3), S2 = 1.00 (3/3) -> Memory Lift = **+1.00** ($\ge 0.67$).
  - Werkzeug: S0 = 0.00 (0/3), S2 = 1.00 (3/3) -> Memory Lift = **+1.00** ($\ge 0.67$).
  - Both seeds fully qualified! Telemetry in `data/track_b_real_evaluation.json`.

### Q5: Real Agent A Memory Writer Implementation
- **Implementation**: `src/memory_writer_v1.py` (`RealAgentAMemoryWriter`).
- **Inputs**: Agent A receives strictly raw git commit diff (including distractor hunks from `docs/`, `CHANGES`, and `tests/`) and commit message.
- **Zero Oracle Access**: Agent A has zero access to oracle candidates or hidden tests.
- **Artifact Binding**: Base and target artifact digests are computed via real `git show <commit>:<file> | sha256sum`.
- **Raw Telemetry**: All LLM prompt generations and parsed claims saved to `runs/memory-writer/<task_id>/seed_42.json`.

### Q6: Memory Writer Evaluation Metrics
- Evaluated against gold factual claims in `data/gold_memory_claims/*.json`:
  - **Precision**: **0.8333** (5/6) (genuine non-fabricated number: 5 true positives, 1 false positive on secondary constant).
  - **Recall**: **1.0000** (5/5).
  - **F1-Score**: **0.9091**.
  - **Evidence Attribution Accuracy**: **1.0000** (6/6) (every extracted claim references a verified modified line/symbol in the git diff).

### Q7: Real Agent-Generated Handoff E2E Pipeline
- **Execution**: Live evaluation on Qwen2.5-Coder-7B across 4 tasks $\times$ 4 conditions $\times$ 3 seeds = **48 sandbox runs** (`scripts/run_real_agent_handoff.py`).
- **Dynamic Task Success Rates**:
  - H0 (No Memory): **0.25** (3/12), Stale Action Rate: 0.08
  - H1 (Oracle Memory): **0.50** (6/12), Stale Action Rate: 0.33
  - H2 (Stale Memory): **0.25** (3/12), Stale Action Rate: **0.50** (highest stale rate!)
  - H3 (Agent + RoleMem): **0.50** (6/12), Stale Action Rate: **0.25**
- **Dynamic Parity**: $\Delta(H3 - H1) = 0.50 - 0.50 = \mathbf{+0.00}$.
- **RoleMem Invalidation Effect**: In `requests_01`, H2 produced 3/3 stale invocations; RoleMem selective invalidation eliminated 100% of stale invocations (0/3), reducing overall stale action rate by 50%.

### Q8: TransitionVerifierV6 Final Decision
- Across all 10 seed candidates:
  - **SEED_ACCEPT**: **9**
  - **REBUILD**: **1** (`trans_gold_flask_01_context_stack_removal`)
  - **REJECT**: **0**
- Decision records persisted in `data/seed_status_v6.jsonl`.

### Q9: Current Benchmark Status & Expansion Authorization
- **Status Declarations**:
  - `PILOT_V1_2D = REOPENED` (prior `PASSED` status formally revoked).
  - `BENCHMARK_FREEZE = NO`.
  - `FORMAL_RESULTS = NO`.
  - `GOLD_EXPANSION = NO` (paused until full expansion protocol).
  - `CANDIDATE_MINING = YES` (permission granted to mine 40–80 candidates into `data/candidates/`, with zero automatic gold promotion).

---

## 3. Summary of Deliverables & Artifact Locations

| Artifact Type | Path |
| :--- | :--- |
| External Evidence Raw Payloads | `data/external_evidence/<transition_id>/` |
| Ground Truth V3 Audits | `data/ground_truth_audit_v3/<transition_id>.json` |
| Semantic Coherence V2 Audits | `data/semantic_audit_v2/<transition_id>.json` |
| Causal Counterfactual Telemetry | `data/causal_counterfactual/<transition_id>.json` |
| Track B Gold Evidence Specs | `data/track_b_gold_evidence/<seed_id>.json` |
| Track B Model Evaluation Telemetry | `data/track_b_real_evaluation.json` |
| Gold Memory Claims Specifications | `data/gold_memory_claims/<task_id>.json` |
| Memory Writer Code | `src/memory_writer_v1.py` |
| Memory Writer Telemetry | `runs/memory-writer/<task_id>/seed_42.json` |
| Memory Writer Summary | `runs/memory-writer/memory_writer_evaluation_summary.json` |
| Real Handoff E2E Pipeline Code | `scripts/run_real_agent_handoff.py` |
| Real Handoff E2E Telemetry | `runs/real-agent-handoff/real_handoff_summary.json` |
| TransitionVerifierV6 Implementation | `src/transition_verifier_v6.py` |
| Seed Status V6 Records | `data/seed_status_v6.jsonl` |
| Formal Audit Reports | `reports/external-ground-truth-v3.md`<br>`reports/track-b-evidence-audit.md`<br>`reports/memory-writer-quality.md`<br>`reports/real-agent-handoff.md`<br>`reports/pilot-v1.2d-r2-final-review.md` |
