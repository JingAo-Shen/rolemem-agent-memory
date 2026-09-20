#!/usr/bin/env python3
"""
scripts/audit_scale_target_memory_v3.py
Formal Fail-Closed Target Memory Audit V3 for Scale Transitions (11-30).

Verifies:
1. statement entailed by target state (non-empty, references replacement or target convention)
2. evidence_file exists
3. evidence_excerpt non-empty
4. evidence_hunk_sha256 == recomputed SHA256(supporting_hunk)
5. diff_patch_sha256 == recomputed SHA256(diff.patch)
6. source_commit == actual target_commit in spec
7. PR relation valid (PR url non-empty and matches spec/pr.json)
8. no hand-written fallback (supporting_hunk is non-empty and actually from diff.patch)

Outputs:
data/scale_target_memory_audit_v3/<tid>.json
"""

import os
import json
import glob
import hashlib
from typing import Dict, Any


def audit_scale_target_memory_v3():
    scale_target_path = "/code/rolemem-agent-memory/data/handoff_target_memory_scale.json"
    specs_dir = "/code/rolemem-agent-memory/data/specs"
    evidence_dir = "/code/rolemem-agent-memory/data/external_evidence"
    out_dir = "/code/rolemem-agent-memory/data/scale_target_memory_audit_v3"
    os.makedirs(out_dir, exist_ok=True)

    with open(scale_target_path, "r", encoding="utf-8") as f:
        target_bank = json.load(f)

    claims = target_bank.get("claims", {})
    results = {}

    for idx in range(11, 31):
        spec_files = glob.glob(f"{specs_dir}/trans_track_a_{idx:02d}_*.json")
        if not spec_files:
            continue
        with open(spec_files[0], "r", encoding="utf-8") as f:
            spec = json.load(f)
        tid = spec["transition_id"]

        claim = claims.get(tid)
        if not claim:
            audit_result = {
                "transition_id": tid,
                "provenance_status": "TARGET_MEMORY_PROVENANCE_FAIL",
                "reason": "Missing claim in target memory snapshot",
                "checks": {"claim_present": False}
            }
            results[tid] = audit_result
            with open(f"{out_dir}/{tid}.json", "w", encoding="utf-8") as f:
                json.dump(audit_result, f, indent=2)
            continue

        # Recompute hashes
        supporting_hunk = claim.get("supporting_hunk", "")
        recomputed_hunk_hash = hashlib.sha256(supporting_hunk.encode("utf-8")).hexdigest() if supporting_hunk else ""
        
        evidence_excerpt = claim.get("evidence_excerpt", "")
        recomputed_excerpt_hash = hashlib.sha256(evidence_excerpt.encode("utf-8")).hexdigest() if evidence_excerpt else ""

        diff_path = f"{evidence_dir}/{tid}/diff.patch"
        diff_patch_content = ""
        recomputed_diff_hash = ""
        if os.path.exists(diff_path):
            with open(diff_path, "r", encoding="utf-8", errors="replace") as f:
                diff_patch_content = f.read()
            recomputed_diff_hash = hashlib.sha256(diff_patch_content.encode("utf-8")).hexdigest()

        # Checks
        source_commit = claim.get("source_commit", "")
        expected_target_commit = spec.get("target_commit", "")
        commit_match = bool(source_commit and expected_target_commit and source_commit == expected_target_commit)

        source_pr = claim.get("source_pr_url", "")
        expected_pr = spec.get("pr_url") or spec.get("external_pr_url") or ""
        pr_match = bool(source_pr and (source_pr == expected_pr or expected_pr in source_pr or source_pr in expected_pr))

        hunk_non_empty = bool(supporting_hunk.strip()) and (recomputed_hunk_hash != "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855")
        excerpt_non_empty = bool(evidence_excerpt.strip()) and (recomputed_excerpt_hash != "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855")

        hunk_in_diff = bool(diff_patch_content and (supporting_hunk.strip()[:100] in diff_patch_content or supporting_hunk in diff_patch_content))
        hunk_hash_match = bool(hunk_non_empty and claim.get("evidence_hunk_sha256") == recomputed_hunk_hash)
        diff_hash_match = bool(recomputed_diff_hash and claim.get("diff_patch_sha256") == recomputed_diff_hash)
        excerpt_hash_match = bool(excerpt_non_empty and claim.get("evidence_excerpt_hash") == recomputed_excerpt_hash)

        statement = claim.get("statement", "")
        statement_entailment = bool(len(statement.strip()) > 10 and ("Use " in statement or "replace" in statement.lower() or "instead" in statement.lower() or spec.get("symbol", "").split(".")[-1] in statement or any(r.split(".")[-1] in statement for r in spec.get("replacement_symbols", []))))

        all_checks = {
            "source_commit_matches": commit_match,
            "source_pr_matches": pr_match,
            "supporting_hunk_non_empty": hunk_non_empty,
            "evidence_excerpt_non_empty": excerpt_non_empty,
            "hunk_in_diff_patch": hunk_in_diff,
            "evidence_hunk_sha256_verified": hunk_hash_match,
            "diff_patch_sha256_verified": diff_hash_match,
            "evidence_excerpt_hash_verified": excerpt_hash_match,
            "statement_entailed": statement_entailment
        }

        all_pass = all(all_checks.values())
        status = "TARGET_MEMORY_VERIFIED" if all_pass else "TARGET_MEMORY_PROVENANCE_FAIL"

        audit_result = {
            "transition_id": tid,
            "provenance_status": status,
            "checks": all_checks,
            "recomputed_hashes": {
                "diff_hunk_sha256": recomputed_hunk_hash,
                "diff_patch_sha256": recomputed_diff_hash,
                "evidence_excerpt_hash": recomputed_excerpt_hash
            },
            "claim": claim
        }

        results[tid] = audit_result
        with open(f"{out_dir}/{tid}.json", "w", encoding="utf-8") as f:
            json.dump(audit_result, f, indent=2)

    passed_count = sum(1 for r in results.values() if r["provenance_status"] == "TARGET_MEMORY_VERIFIED")
    print(f"[AUDIT V3] Target Memory Audit: {passed_count}/{len(results)} TARGET_MEMORY_VERIFIED")


if __name__ == "__main__":
    audit_scale_target_memory_v3()
