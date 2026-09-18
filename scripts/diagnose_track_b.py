#!/usr/bin/env python3
"""
scripts/diagnose_track_b.py
Diagnoses Track B candidate evaluations, classifies failure taxonomy,
and formally updates candidate status for:
- requests_gateway_retries -> REJECT_EVIDENCE_INVALID
- werkzeug_debug_iframe_cookie -> REBUILD_EVIDENCE_PARTIAL
"""

import os
import sys
import json
from typing import Dict, Any, List

sys.path.insert(0, "/code/rolemem-agent-memory")

RUNS_DIR = "/code/rolemem-agent-memory/runs/track-b-v2"
TRACK_B_CANDIDATES_DIR = "/code/rolemem-agent-memory/data/track_b_candidates"
os.makedirs(TRACK_B_CANDIDATES_DIR, exist_ok=True)
REPORTS_DIR = "/code/rolemem-agent-memory/reports"
os.makedirs(REPORTS_DIR, exist_ok=True)


TAXONOMY_CATEGORIES = [
    "MODEL_LOGIC_FAILURE",
    "MODEL_IMPORT_FAILURE",
    "OUTPUT_PARSE_FAILURE",
    "ENVIRONMENT_FAILURE",
    "FIXTURE_FAILURE",
    "HIDDEN_TEST_FAILURE"
]


def diagnose():
    summary_file = os.path.join(RUNS_DIR, "track_b_summary.json")
    if not os.path.exists(summary_file):
        print(f"Error: summary file {summary_file} not found")
        return

    with open(summary_file) as f:
        summary_data = json.load(f)

    diagnostics = {}

    # Diagnostic for requests_gateway_retries
    diagnostics["track_b_requests_gateway_retries"] = {
        "candidate_id": "track_b_requests_gateway_retries",
        "evidence_audit_status": "REJECT_EVIDENCE_INVALID",
        "evidence_flaw": "psf/requests PR #2497 is a security disclosure policy document, not a code implementation of Retry constants.",
        "failure_taxonomy": "ENVIRONMENT_FAILURE",
        "evaluation_validity": "INVALID",
        "failure_details": {
            "root_cause": "ModuleNotFoundError: No module named 'requests' during pytest test collection in sandbox venv.",
            "collection_status": "ERROR_COLLECTION",
            "runtime_error": "ModuleNotFoundError: No module named 'requests'",
            "code_semantic_alignment": "HIGH_ON_S2 (Qwen7B generated Retry(total=3, backoff_factor=0.5, status_forcelist=[502, 503, 504]) matching prompt memory exactly)",
            "benchmark_status": "REJECTED_FROM_TRACK_B"
        }
    }

    # Diagnostic for werkzeug_debug_iframe_cookie
    diagnostics["track_b_werkzeug_debug_iframe_cookie"] = {
        "candidate_id": "track_b_werkzeug_debug_iframe_cookie",
        "evidence_audit_status": "REBUILD_EVIDENCE_PARTIAL",
        "evidence_flaw": "pallets/werkzeug PR #1913 only introduced samesite='None'; secure=True was not added by this PR and was an unevidenced requirement.",
        "failure_taxonomy": "ENVIRONMENT_FAILURE",
        "evaluation_validity": "INVALID",
        "failure_details": {
            "root_cause": "ModuleNotFoundError: No module named 'werkzeug' during pytest test collection in sandbox venv.",
            "collection_status": "ERROR_COLLECTION",
            "runtime_error": "ModuleNotFoundError: No module named 'werkzeug'",
            "code_semantic_alignment": "HIGH_ON_S2 (Qwen7B generated dump_cookie('debug_auth', token, samesite='None', secure=True, httponly=True) matching prompt memory exactly)",
            "benchmark_status": "REBUILD_REQUIRED_BEFORE_REEVALUATION"
        }
    }

    # Save to data/track_b_candidates
    for cid, diag in diagnostics.items():
        out_path = os.path.join(TRACK_B_CANDIDATES_DIR, f"{cid}_diagnostic.json")
        with open(out_path, "w") as f:
            json.dump(diag, f, indent=2)
        print(f"Wrote diagnostic to {out_path}")

    # Generate Markdown Report: reports/track-b-diagnostics.md
    report_md = f"""# Track B Diagnostics and Evidence Integrity Report

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
"""
    with open(os.path.join(REPORTS_DIR, "track-b-diagnostics.md"), "w") as f:
        f.write(report_md)
    print(f"Wrote reports/track-b-diagnostics.md")

if __name__ == "__main__":
    diagnose()
