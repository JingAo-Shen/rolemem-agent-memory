# RoleMem Protocol V2.1 — Final Limitations, Errata & Scientific Scope Audit

## 1. Formal Status Declaration
```text
PROTOCOL_V2_1_DEVELOPMENT_CLOSED = YES
ALGORITHM_FREEZE = NO
BENCHMARK_FREEZE = NO
HUMAN_VALIDATION = PENDING
FORMAL_AGENT_RESULTS = NO
FORMAL_PAPER_RESULTS = NO
```

This document serves as the permanent scientific errata and limitation record for Protocol V2.1.
All artifacts defined in `data/freeze/protocol_v2_1_development_freeze.json` are frozen and strictly immutable. Under Protocol V2.2, V2.1 is strictly used as a baseline development sanity check.

---

## 2. Documented Limitations & Errata

### A. Track A Curation Scope: `Track A Core = 0`
- Under the strict machine evaluation gates implemented in Protocol V2.1-R3.1, `track_a_core.jsonl` contains **0 candidate transitions**, while 25 transitions are classified into `rebuild_candidates.jsonl` and 1 in `track_a_controls.jsonl`.
- **Scientific Implication**: Protocol V2.1 Track A cannot be used as a formal LLM agent evaluation benchmark. Formal multi-seed agent baseline runs (`configs/experiment_protocol_v2_1.yaml` conditions B0-B5, F, A1-A5) are deferred until formal Track A reconstruction.

### B. Evidence Integrity Determinism vs. External Independent Verification
- In Protocol V2.1-R3.1, the evidence integrity gate asserts `stored_diff_sha256 == recomputed_diff_sha256`.
- **Scientific Implication**: This assertion verifies **deterministic recomputation** from cached Git trees within the execution environment. It does not constitute third-party independent artifact integrity verification against immutable remote public archives.

### C. GitHub PR Commit Association: Provisional Metadata Validation
- The `pr_commit_relation = VERIFIED` field in V2.1 indicates syntactic format presence and commit message cross-referencing.
- **Scientific Implication**: It does not programmatically verify live GitHub Pull Request merge commit hashes against the GitHub REST API or signed Git tags. It must be interpreted as **provisional metadata validation**.

### D. Benchmark Specificity & Diagnostic Scope
- Category C contains 1 verified diagnostic case (`pluggy.HookSpec`). It serves as an exploratory sanity check for cross-file dependency propagation, and cannot be used to make standalone statistical category-level superiority claims.
- Category D2 contains 2 verified behavioral break cases (`urllib3.BaseHTTPResponse` and `marshmallow.__all__`).

---

## 3. Immutability Covenant
To maintain strict scientific reproducibility and prevent retroactive benchmark tailoring, **zero modifications** may be made to:
- `data/memory_validity_v2_1/blind_inputs.jsonl`
- `data/memory_validity_v2_1/gold_labels.jsonl`
- `data/memory_validity_v2_1/case_id_map_private.json`
- Historical V2.1 transition categories, cases, or ground truth labels.
