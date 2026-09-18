# Track B Diagnostics and Evidence Integrity Report

## 1. Executive Summary

In Pilot-v1.2d-r3, two exploratory Track B candidates were evaluated across 5 random seeds on Qwen2.5-Coder-7B in a Bubblewrap sandbox:
- `track_b_requests_gateway_retries` (0/5 on S0, S1, S2)
- `track_b_werkzeug_debug_iframe_cookie` (0/5 on S0, S1, S2)

Detailed telemetry audit reveals that the 0/5 result was **not a model capability failure**, but a combination of **ENVIRONMENT_FAILURE** (missing package in sandbox test collection) and **EVIDENCE_DEFICIENCIES**.

## 2. Candidate Status and Evidence Audit

| Candidate ID | Status | Primary Flaw | Evaluation Validity |
| :--- | :--- | :--- | :--- |
| `track_b_requests_gateway_retries` | `REJECT_EVIDENCE_INVALID` | PR #2497 is security disclosure policy, not Retry constants | `INVALID` |
| `track_b_werkzeug_debug_iframe_cookie` | `REBUILD_EVIDENCE_PARTIAL` | PR #1913 only introduced `samesite="None"`; `secure=True` unevidenced | `INVALID` |

## 3. Failure Taxonomy Breakdown

```text
TAXONOMY CLASSIFICATION:
- requests_gateway_retries: ENVIRONMENT_FAILURE (ModuleNotFoundError: No module named 'requests')
- werkzeug_debug_iframe_cookie: ENVIRONMENT_FAILURE (ModuleNotFoundError: No module named 'werkzeug')
```

### Raw Telemetry Findings:
1. **Semantic Code Generation**: On S2 (with valid memory prompt), Qwen2.5-Coder-7B generated syntactically and semantically correct implementations conforming directly to the memory prompts:
   - For requests: `HTTPAdapter(max_retries=Retry(total=3, backoff_factor=0.5, status_forcelist=[502, 503, 504]))`
   - For werkzeug: `dump_cookie('debug_auth', token, samesite='None', secure=True, httponly=True)`
2. **Collection Error**: When pytest executed inside the Bubblewrap sandbox, the target library was not exposed in the test runner's `sys.path`, resulting in immediate `ModuleNotFoundError` during test collection before any assertion could run.
3. **Invalidity**: Because the environment prevented code execution, the evaluation is classified as `candidate evaluation = INVALID`.

## 4. Track B Search Strategy Redefinition

Moving forward under Pilot-v1.3:
1. Track B candidates must NOT be grep-able in current C1 repository code.
2. Decisions must be sourced from authentic maintainer records:
   - PR discussions & maintainer comments
   - Architecture Decision Records (ADRs)
   - Migration guides & changelog notices
   - Historical config / timeout / retry / serialization policies
3. Every candidate must pass:
   - GitHub evidence verification (actual PR / comment diff)
   - Temporal validity (`evidence_time <= target_commit_time`)
   - Current repository leakage scan (zero occurrences of decision values in C1)
   - Decision entailment audit
4. Benchmark construction is decoupled: Track B candidates remain in exploratory candidate mining and do NOT block Track A provisional expansion.
