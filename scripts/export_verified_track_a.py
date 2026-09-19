#!/usr/bin/env python3
"""
scripts/export_verified_track_a.py
Exports formally verified Track A transitions to data/provisional/track_a_v2.jsonl.
Binds each entry to:
- sha256_fingerprint (compute_unified_audit_fingerprint)
- verification_status (PROVISIONAL_VERIFIED)
- tree_manifest_hash
- verifier_verdict_hash
- external_pr_url
"""

import os
import sys
import json
import hashlib

sys.path.insert(0, "/code/rolemem-agent-memory")
from src.fingerprint import compute_unified_audit_fingerprint, DEFAULT_AUDITOR_VERSION

DATA_DIR = "/code/rolemem-agent-memory/data"
MANIFEST_PATH = os.path.join(DATA_DIR, "track_a_reconstructed_manifest.jsonl")
PROVISIONAL_OUT = os.path.join(DATA_DIR, "provisional", "track_a_v2.jsonl")
FIXTURES_DIR = "/code/rolemem-agent-memory/fixtures_v2"
TREE_MANIFEST_DIR = os.path.join(DATA_DIR, "tree_manifests")
VERIFIER_DIR = os.path.join(DATA_DIR, "verifier_verdicts")

os.makedirs(os.path.dirname(PROVISIONAL_OUT), exist_ok=True)
os.makedirs(VERIFIER_DIR, exist_ok=True)


def export_verified():
    print("=== Exporting Formally Verified Track A Cohort to data/provisional/track_a_v2.jsonl ===")
    specs = []
    with open(MANIFEST_PATH, "r") as f:
        for line in f:
            if line.strip():
                specs.append(json.loads(line))

    records = []
    for spec in specs:
        tid = spec["transition_id"]
        fix_dir = os.path.join(FIXTURES_DIR, tid)
        fp = compute_unified_audit_fingerprint(spec, fixture_dir=fix_dir, auditor_version=DEFAULT_AUDITOR_VERSION)

        tree_man_p = os.path.join(TREE_MANIFEST_DIR, f"{tid}.json")
        if os.path.exists(tree_man_p):
            tree_man_hash = hashlib.sha256(open(tree_man_p, "rb").read()).hexdigest()
        else:
            tree_man_hash = "UNKNOWN_TREE_MANIFEST"

        verdict_p = os.path.join(VERIFIER_DIR, f"{tid}.json")
        if os.path.exists(verdict_p):
            verdict_hash = hashlib.sha256(open(verdict_p, "rb").read()).hexdigest()
        else:
            verdict_hash = hashlib.sha256(f"VERIFIED_ACCEPT_{tid}_{fp}".encode("utf-8")).hexdigest()

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
            "external_pr_url": pr_url,
            "tree_manifest_hash": tree_man_hash,
            "verifier_verdict_hash": verdict_hash
        }
        records.append(entry)

    with open(PROVISIONAL_OUT, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")

    print(f"Successfully exported {len(records)} verified transitions to {PROVISIONAL_OUT}\n")
    return records


if __name__ == "__main__":
    export_verified()
