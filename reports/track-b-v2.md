# Pilot-v1.2d-r3 Track B (Memory-Required) Evaluation Report

**Evaluation Framework**: Repository-Visible Context + Evidence-Hiding Audit + Matched 5-Seed Sandbox Evaluation  
**Model**: `Qwen2.5-Coder-7B-Instruct` (temp=0.2, 5 seeds per condition)  
**Evidence Source**: Automatically rendered from `runs/track-b-v2/track_b_summary.json`

---

## 1. Demoted Probes (Pilot-v1.2d-r2 Legacy Seeds)

In accordance with Section 4, previous synthetic Track B seeds are demoted to `EVIDENCE_GROUNDED_MEMORY_LIFT_PROBE`:

| Probe ID | Repository | Classification | Demotion Rationale |
| :--- | :--- | :--- | :--- |
| `track_b_urllib3_redirect_headers` | `urllib3/urllib3` | `EVIDENCE_GROUNDED_MEMORY_LIFT_PROBE` | Decision constant DEFAULT_REMOVE_HEADERS_ON_REDIRECT is present in C1 repo retry.py |
| `track_b_werkzeug_pbkdf2_iterations` | `pallets/werkzeug` | `EVIDENCE_GROUNDED_MEMORY_LIFT_PROBE` | Decision came from subsequent PR #2612 (2023) injected into older 2021 repo (evidence_time > target_state_time) |

---

## 2. Repository-State Track B Candidates Evaluation

Strict Qualification Criteria (Section 8):
- `S2 TSR - S0 TSR >= 0.4`
- `S0 TSR <= 0.4`
- `S2 TSR >= 0.8`
- `evidence_time <= current_state_time` (Historical causality)
- Zero leakage in visible repo context (`Evidence-Hiding Audit == PASS`)

| Candidate ID | Repository | S0 TSR (No Mem) | S1 TSR (Stale) | S2 TSR (Valid) | Delta Lift | Evidence Hiding | Status |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `track_b_requests_gateway_retries` | `psf/requests` | 0.00 | 0.00 | 0.00 | +0.00 | PASS | NOT_QUALIFIED |
| `track_b_werkzeug_debug_iframe_cookie` | `pallets/werkzeug` | 0.00 | 0.00 | 0.00 | +0.00 | PASS | NOT_QUALIFIED |

---

## 3. Summary & Qualification Status

- Total Evaluated Candidates: `2`
- Qualified Repository-State Seeds: `0`
