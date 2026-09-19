#!/usr/bin/env python3
"""
scripts/run_transition_verifier_v9.py

Executes TransitionVerifierV9 across all 10 Track A reconstructed transitions.
Persists machine evidence verdicts to:
  data/verifier_verdicts/<tid>.json

Each verdict JSON contains:
- transition_id
- integrity_status
- benchmark_eligibility
- overall_status
- audit_fingerprint
- gates
- evidence_manifest
- verifier_version
- verified_at
"""

import os
import sys
import json
import glob
from datetime import datetime, timezone

sys.path.insert(0, "/code/rolemem-agent-memory")
from src.transition_verifier_v9 import TransitionVerifierV9
from src.fingerprint import DEFAULT_AUDITOR_VERSION

DATA_DIR = "/code/rolemem-agent-memory/data"
SPECS_DIR = os.path.join(DATA_DIR, "specs")
VERIFIER_DIR = os.path.join(DATA_DIR, "verifier_verdicts")
MANIFEST_PATH = os.path.join(DATA_DIR, "track_a_reconstructed_manifest.jsonl")

os.makedirs(VERIFIER_DIR, exist_ok=True)


def run_verifier():
    print("=== Running TransitionVerifierV9 Persistence ===")
    v9 = TransitionVerifierV9(auditor_version=DEFAULT_AUDITOR_VERSION)

    # Load from manifest for canonical ordering
    specs = []
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                item = json.loads(line)
                # Load corresponding spec JSON
                spec_path = os.path.join(SPECS_DIR, f"{item['transition_id']}.json")
                if os.path.exists(spec_path):
                    with open(spec_path, "r", encoding="utf-8") as sf:
                        specs.append(json.load(sf))
                else:
                    specs.append(item)

    print(f"Loaded {len(specs)} transitions to verify.")

    verdict_summary = {}
    accept_count = 0

    for cand in specs:
        tid = cand["transition_id"]
        result = v9.verify_candidate_v9(cand)

        verdict_doc = {
            "transition_id": tid,
            "integrity_status": result["integrity_status"],
            "benchmark_eligibility": result["benchmark_eligibility"],
            "overall_status": result["overall_status"],
            "audit_fingerprint": result["audit_fingerprint"],
            "gates": result["gates"],
            "evidence_manifest": result["evidence_manifest"],
            "verifier_version": "v9.0.0",
            "verified_at": datetime.now(timezone.utc).isoformat()
        }

        out_path = os.path.join(VERIFIER_DIR, f"{tid}.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(verdict_doc, f, indent=2)

        verdict_summary[tid] = verdict_doc
        status = result["overall_status"]
        integ = result["integrity_status"]
        elig = result["benchmark_eligibility"]
        print(f"[{tid:45}] {status:6} | Integrity: {integ:4} | Eligibility: {elig} -> {out_path}")
        if status == "ACCEPT":
            accept_count += 1

    print(f"\nVerifier V9 Complete: {accept_count}/{len(specs)} ACCEPT. Verdicts persisted to {VERIFIER_DIR}/\n")
    return verdict_summary


if __name__ == "__main__":
    run_verifier()
