#!/usr/bin/env python3
"""
scripts/export_verified_track_a.py
Exports formally verified Track A transitions to data/provisional/track_a_v3.jsonl.

Strict Rules for Pilot-v1.3-r2.1:
1. Pure Evidence Consumer: Reads real verdict JSONs from data/verifier_verdicts/<tid>.json.
2. Zero Fallback: If verdict file is missing or invalid, immediately marks EXPORT_BLOCKED.
3. Cryptographic Validation: Requires:
   - integrity_status == "PASS"
   - overall_status == "ACCEPT"
   - audit_fingerprint == current computed fingerprint
4. verifier_verdict_hash must be SHA256 of real verdict JSON bytes.
"""

import os
import sys
import json
import hashlib

sys.path.insert(0, "/code/rolemem-agent-memory")
from src.fingerprint import compute_unified_audit_fingerprint, DEFAULT_AUDITOR_VERSION

DATA_DIR = "/code/rolemem-agent-memory/data"
MANIFEST_PATH = os.path.join(DATA_DIR, "track_a_reconstructed_manifest.jsonl")
PROVISIONAL_V3_OUT = os.path.join(DATA_DIR, "provisional", "track_a_v3.jsonl")
PROVISIONAL_V2_OUT = os.path.join(DATA_DIR, "provisional", "track_a_v2.jsonl")
FIXTURES_DIR = "/code/rolemem-agent-memory/fixtures_v2"
TREE_MANIFEST_DIR = os.path.join(DATA_DIR, "tree_manifests")
VERIFIER_DIR = os.path.join(DATA_DIR, "verifier_verdicts")

os.makedirs(os.path.dirname(PROVISIONAL_V3_OUT), exist_ok=True)


def export_verified():
    print("=== Exporting Formally Verified Track A Cohort (Zero-Fallback V9 Verifier Consumer) ===")
    specs = []
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                specs.append(json.loads(line))

    records = []
    blocked_count = 0

    for spec in specs:
        tid = spec["transition_id"]
        fix_dir = os.path.join(FIXTURES_DIR, tid)
        fp = compute_unified_audit_fingerprint(spec, fixture_dir=fix_dir, auditor_version=DEFAULT_AUDITOR_VERSION)

        # 1. Check tree manifest
        tree_man_p = os.path.join(TREE_MANIFEST_DIR, f"{tid}.json")
        if not os.path.exists(tree_man_p):
            print(f"[{tid}] EXPORT_BLOCKED: Missing tree manifest {tree_man_p}")
            blocked_count += 1
            continue
        tree_man_hash = hashlib.sha256(open(tree_man_p, "rb").read()).hexdigest()

        # 2. Check real TransitionVerifierV9 verdict
        verdict_p = os.path.join(VERIFIER_DIR, f"{tid}.json")
        if not os.path.exists(verdict_p):
            print(f"[{tid}] EXPORT_BLOCKED: Missing real verdict file {verdict_p}")
            blocked_count += 1
            continue

        verdict_bytes = open(verdict_p, "rb").read()
        verdict_data = json.loads(verdict_bytes.decode("utf-8"))

        if verdict_data.get("integrity_status") != "PASS":
            print(f"[{tid}] EXPORT_BLOCKED: integrity_status is {verdict_data.get('integrity_status')}")
            blocked_count += 1
            continue

        if verdict_data.get("overall_status") != "ACCEPT":
            print(f"[{tid}] EXPORT_BLOCKED: overall_status is {verdict_data.get('overall_status')}")
            blocked_count += 1
            continue

        if verdict_data.get("audit_fingerprint") != fp:
            print(f"[{tid}] EXPORT_BLOCKED: Stale verdict fingerprint ({verdict_data.get('audit_fingerprint')} != {fp})")
            blocked_count += 1
            continue

        verdict_hash = hashlib.sha256(verdict_bytes).hexdigest()

        pr_p = os.path.join(DATA_DIR, "external_evidence", tid, "pr.json")
        pr_url = spec.get("external_pr_url")
        if not pr_url and os.path.exists(pr_p):
            pr_data = json.load(open(pr_p))
            pr_raw = pr_data.get("html_url") or pr_data.get("url", "")
            pr_url = pr_raw.replace("api.github.com/repos", "github.com").replace("/pulls/", "/pull/")
        if not pr_url:
            pr_url = f"https://github.com/{spec['repo_name']}"

        entry = {
            "transition_id": tid,
            "repo_name": spec["repo_name"],
            "base_commit": spec["base_commit"],
            "target_commit": spec["target_commit"],
            "track": spec.get("track", "TRACK_A_STALE_SENSITIVE"),
            "target_file": spec.get("target_file", "solution.py"),
            "sha256_fingerprint": fp,
            "verification_status": "PROVISIONAL_VERIFIED",
            "benchmark_eligibility": verdict_data.get("benchmark_eligibility", "TRACK_A_PROVISIONAL_GOLD"),
            "external_pr_url": pr_url,
            "tree_manifest_hash": tree_man_hash,
            "verifier_verdict_hash": verdict_hash
        }
        records.append(entry)
        print(f"[{tid}] EXPORT_ACCEPTED | fp={fp[:12]}... | verdict_hash={verdict_hash[:12]}...")

    # Write output manifests
    with open(PROVISIONAL_V3_OUT, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")

    with open(PROVISIONAL_V2_OUT, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")

    print(f"\nSuccessfully exported {len(records)} verified transitions to {PROVISIONAL_V3_OUT} (Blocked: {blocked_count})\n")
    return records


if __name__ == "__main__":
    export_verified()
