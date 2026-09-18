# Pilot-v1.2d-r2 Track B Architectural Decision Evidence Audit Report

**Status**: **2 QUALIFIED REPOSITORY-GROUNDED POSITIVE SEEDS VERIFIED**  
**Evaluation Model**: `Qwen2.5-Coder-7B-Instruct` (device: cuda, float16)  
**Execution Environment**: Bubblewrap Secure Sandbox with Task Virtualenv  
**Date**: 2026-09-18  

---

## 1. Formal Retraction of Synthetic Track B Seeds

In adherence to scientific integrity principles, all previous synthetic/handcrafted Track B seeds are formally revoked and demoted:
- `track_b_urllib3_custom_retry`: **SYNTHETIC_SANITY_ONLY — NOT REPOSITORY GROUNDED**
- `track_b_requests_service_adapter`: **SYNTHETIC_SANITY_ONLY — NOT REPOSITORY GROUNDED**

These seeds relied on synthetic PR numbers and contrived conventions not substantiated in the underlying Git history.

---

## 2. Discovery & Verification of Real Repository Seeds

Two authentic, GitHub-verified, repository-grounded architectural decisions were mined and verified:

### 2.1 Seed 1: `track_b_urllib3_redirect_headers`
- **Repository**: `urllib3/urllib3`
- **GitHub PR**: [urllib3/urllib3#1346](https://github.com/urllib3/urllib3/pull/1346)
- **Commit**: `560bd227b90f74417ffaedebf5f8d05a8ee4f532`
- **File**: `urllib3/util/retry.py` (L151–L155)
- **Architectural Decision**: When redirecting across different hosts, urllib3 strips sensitive headers defaulting to `frozenset(['Authorization'])` (`Retry.DEFAULT_REDIRECT_HEADERS_BLACKLIST` / `DEFAULT_REMOVE_HEADERS_ON_REDIRECT`).
- **Evidence-Hiding Audit**:
  - Decision value `"Authorization"` does not appear anywhere in the task prompt or target filename.
  - Zero leakage verified: **PASS**.

### 2.2 Seed 2: `track_b_werkzeug_pbkdf2_iterations`
- **Repository**: `pallets/werkzeug`
- **GitHub PR**: [pallets/werkzeug#2612](https://github.com/pallets/werkzeug/pull/2612)
- **Commit**: `92b994f76ec3687e97839c7ea225bf556a587a98`
- **File**: `src/werkzeug/security.py` (L9–L13)
- **Architectural Decision**: Werkzeug updated the default work factor for PBKDF2 password hashing from 150,000 / 260,000 to 600,000 iterations to match updated OWASP security recommendations (`DEFAULT_PBKDF2_ITERATIONS = 600000`).
- **Evidence-Hiding Audit**:
  - Decision value `"600000"` does not appear anywhere in the task prompt or target filename.
  - Zero leakage verified: **PASS**.

---

## 3. Empirical Model Evaluation & Memory Lift

Both seeds were evaluated on Qwen2.5-Coder-7B across 3 random seeds ([42, 123, 999]) in isolated Bubblewrap sandboxes under two conditions:
- **S0 (Zero-shot No-Memory Baseline)**: Agent given only repository code and task prompt.
- **S2 (RoleMem Active Architectural Memory)**: Agent given project security architectural memory context.

| Seed Transition ID | Repository | S0 TSR (No Memory) | S2 TSR (RoleMem) | Memory Lift ($\Delta$) | Lift Threshold | Status |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| `track_b_urllib3_redirect_headers` | `urllib3/urllib3` | **0.00** (0/3) | **1.00** (3/3) | **+1.00** | $\ge 0.67$ | **QUALIFIED PASS** |
| `track_b_werkzeug_pbkdf2_iterations` | `pallets/werkzeug` | **0.00** (0/3) | **1.00** (3/3) | **+1.00** | $\ge 0.67$ | **QUALIFIED PASS** |

### 3.1 Error Analysis in S0 vs S2
- **`track_b_urllib3_redirect_headers`**:
  - **S0**: The zero-shot model generates a generic list of standard HTTP headers (`['Cookie', 'Authorization', 'X-Auth-Token', 'Set-Cookie']`), causing the strict project policy test to fail (`assert norm_headers == {'authorization'}`).
  - **S2**: With RoleMem architectural context, the model precisely outputs `frozenset(['Authorization'])`, passing the test 3/3 times.
- **`track_b_werkzeug_pbkdf2_iterations`**:
  - **S0**: The zero-shot model defaults to generic iterations (`100000` or `150000`), failing the repository standard test (`assert iterations == 600000`).
  - **S2**: With RoleMem architectural context, the model outputs `600000`, passing the test 3/3 times.

---

## 4. Telemetry Artifacts

- Evidence specs: `data/track_b_gold_evidence/<seed_id>.json`
- Full evaluation telemetry: `data/track_b_real_evaluation.json`
