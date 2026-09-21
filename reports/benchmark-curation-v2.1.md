# RoleMem Protocol V2.1-R3.1 — Gate-Based Benchmark Curation Report

## 1. Executive Curation Summary
- **Total Evaluated Transitions**: 30
- **Core Benchmark Candidates**: 0 provisional candidates (0.0%)
- **Control Benchmark Candidates**: 1 (3.3%)
- **Rebuild Candidates**: 25 (83.3%)
- **Excluded Transitions**: 4 (13.3%)
- **Distinct Repositories (Core)**: 0
- **Distinct Repositories (All)**: 25

---

## 2. Gate Verification Overview

| Gate | Description | Pass Count | Pass Rate |
| :--- | :--- | :--- | :--- |
| **1. Authenticity** | Real 40-char Git SHA & verified git commit | 30/30 | 100.0% |
| **2. Evidence Integrity** | Real diff hunks, PR URL & external evidence | 30/30 | 100.0% |
| **3. Causal Matrix** | Machine-generated 2x2 sandbox execution | 19/30 | 63.3% |
| **4. Stale Grounding** | Grounded historical memory | 28/30 | 93.3% |
| **5. Valid Grounding** | Grounded target memory | 0/30 | 0.0% |
| **6. Task Mapping** | Concrete pytest task mapping | 0/30 | 0.0% |
| **7. Leakage** | Non-trivial BM25 context | 29/30 | 96.7% |
| **8. Environment** | Sandbox execution 2-run reproducibility | 30/30 | 100.0% |

---

## 3. Core Benchmark Provisional Candidates


## 4. Control Transitions

- **`trans_track_a_08_attrs_py313_replace_control`** (attrs): Verified negative evolution control passing sandbox stability criteria.