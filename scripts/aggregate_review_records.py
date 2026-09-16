"""
scripts/aggregate_review_records.py
Aggregates review records strictly from raw verifier artifacts (data/verifier_results/*.json)
and external ground truth artifacts (data/ground_truth_audit/*.json).
Outputs:
- data/reviewed/review_records_v4.jsonl
- data/verified/verified_v4.jsonl
Zero manual or hardcoded review stamps.
"""

import os
import sys
import json

VERIFIER_RESULTS_DIR = "/code/rolemem-agent-memory/data/verifier_results"
GROUND_TRUTH_DIR = "/code/rolemem-agent-memory/data/ground_truth_audit"
REVIEW_V4_PATH = "/code/rolemem-agent-memory/data/reviewed/review_records_v4.jsonl"
VERIFIED_V4_PATH = "/code/rolemem-agent-memory/data/verified/verified_v4.jsonl"


def main():
    verifier_files = sorted([f for f in os.listdir(VERIFIER_RESULTS_DIR) if f.endswith(".json")])
    review_records = []
    verified_records = []

    print(f"=== Aggregating review records from {len(verifier_files)} raw verifier artifacts ===")

    for v_name in verifier_files:
        v_path = os.path.join(VERIFIER_RESULTS_DIR, v_name)
        with open(v_path, "r", encoding="utf-8") as f:
            v_res = json.load(f)

        tid = v_res["transition_id"]
        gt_path = os.path.join(GROUND_TRUTH_DIR, f"{tid}.json")
        with open(gt_path, "r", encoding="utf-8") as f:
            gt_res = json.load(f)

        gates = v_res["gates"]
        decision = v_res["overall_status"]

        rec = {
            "transition_id": tid,
            "repo_name": v_res["repo_name"],
            "track": v_res.get("track", "A"),
            "review_status": "AUTO_REVIEWED",
            "reviewer_type": "automated_self_review",
            "review_decision": decision,
            "commit_verification": gates["commit_verification"],
            "causality_verified": (gates["causality_status"] == "CAUSALITY_PASS"),
            "original_test_verified": (gates["original_test_verification"] == "PASS"),
            "hidden_test_verified": (gates["hidden_test_verification"] == "PASS"),
            "controls_verified": (gates["fixture_control_verification"] == "PASS"),
            "snapshot_hash_verified": (gates["snapshot_hash_verification"] == "PASS"),
            "external_ground_truth_verified": (gates["metadata_ground_truth_verification"] == "PASS"),
            "verifier_artifact": f"data/verifier_results/{tid}.json",
            "ground_truth_artifact": f"data/ground_truth_audit/{tid}.json",
            "pr_url": gt_res.get("pr_url"),
            "pr_title": gt_res.get("pr_title"),
            "target_commit": gt_res.get("target_commit")
        }
        review_records.append(rec)

        if decision == "ACCEPT":
            verified_records.append(rec)

    os.makedirs(os.path.dirname(REVIEW_V4_PATH), exist_ok=True)
    with open(REVIEW_V4_PATH, "w", encoding="utf-8") as f:
        for r in review_records:
            f.write(json.dumps(r) + "\n")
    print(f"Wrote {len(review_records)} review records to {REVIEW_V4_PATH}")

    os.makedirs(os.path.dirname(VERIFIED_V4_PATH), exist_ok=True)
    with open(VERIFIED_V4_PATH, "w", encoding="utf-8") as f:
        for r in verified_records:
            f.write(json.dumps(r) + "\n")
    print(f"Wrote {len(verified_records)} verified records to {VERIFIED_V4_PATH}")


if __name__ == "__main__":
    main()
