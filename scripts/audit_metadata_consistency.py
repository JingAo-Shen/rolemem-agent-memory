"""
scripts/audit_metadata_consistency.py
Audits and synchronizes internal benchmark metadata across the repository.
Enforces TransitionSpec (data/specs/<transition_id>.json) as the SINGLE SOURCE OF TRUTH.
NOTE: This script ONLY audits and syncs internal metadata consistency between specs and fixtures.
It DOES NOT emit review decisions or verify external ground truth.
"""

import os
import sys
import json
import argparse
from typing import Dict, Any, List

SPECS_DIR = "/code/rolemem-agent-memory/data/specs"
FIXTURES_DIR = "/code/rolemem-agent-memory/fixtures_v2"
GOLD_V4_PATH = "/code/rolemem-agent-memory/data/gold/seed_gold_v4.jsonl"


def audit_and_sync(sync: bool = False) -> Dict[str, Any]:
    """Audit metadata consistency across specs and fixtures."""
    spec_files = sorted([f for f in os.listdir(SPECS_DIR) if f.endswith(".json")])
    discrepancies = []
    synced_count = 0

    gold_v4_records = []

    for fname in spec_files:
        spec_path = os.path.join(SPECS_DIR, fname)
        with open(spec_path, "r", encoding="utf-8") as f:
            spec = json.load(f)

        tid = spec["transition_id"]
        fixture_meta_path = os.path.join(FIXTURES_DIR, tid, "metadata.json")

        if not os.path.exists(fixture_meta_path):
            discrepancies.append({
                "transition_id": tid,
                "field": "fixture_exists",
                "spec": True,
                "fixture": False
            })
            continue

        with open(fixture_meta_path, "r", encoding="utf-8") as f:
            fixture_meta = json.load(f)

        # Fields that MUST match exactly
        fields_to_check = [
            "repo_name",
            "base_commit",
            "target_commit",
            "changed_files",
            "changed_symbols",
            "current_task",
            "stale_memory_candidate",
            "valid_memory_candidate",
            "test_evidence_source",
            "pr_url",
            "issue_url",
            "original_test_required"
        ]

        item_diffs = []
        for field in fields_to_check:
            s_val = spec.get(field)
            f_val = fixture_meta.get(field)
            if s_val != f_val:
                item_diffs.append({"field": field, "spec": s_val, "fixture": f_val})

        if item_diffs:
            discrepancies.append({"transition_id": tid, "differences": item_diffs})
            if sync:
                # Propagate from canonical spec to fixture metadata
                fixture_meta.update(spec)
                with open(fixture_meta_path, "w", encoding="utf-8") as f:
                    json.dump(fixture_meta, f, indent=2)
                synced_count += 1
        elif sync:
            fixture_meta.update(spec)
            with open(fixture_meta_path, "w", encoding="utf-8") as f:
                json.dump(fixture_meta, f, indent=2)
            synced_count += 1

        # Check for banned legacy patterns
        if "2085" in spec.get("test_evidence_source", ""):
            discrepancies.append({"transition_id": tid, "error": "Banned typo PR #2085 found in test_evidence_source"})
        if "Href" in spec.get("repository_change", ""):
            discrepancies.append({"transition_id": tid, "error": "Unrelated symbol Href found in repository_change"})
        if tid == "trans_gold_flask_02_should_ignore_error" and "errorhandler" in spec.get("valid_memory_candidate", ""):
            discrepancies.append({"transition_id": tid, "error": "Banned pattern errorhandler found in flask 02 valid candidate"})

        gold_rec = dict(spec)
        gold_rec["benchmark_status"] = "PROVISIONAL_GOLD_V2"
        gold_v4_records.append(gold_rec)

    if sync:
        os.makedirs(os.path.dirname(GOLD_V4_PATH), exist_ok=True)
        with open(GOLD_V4_PATH, "w", encoding="utf-8") as f:
            for r in gold_v4_records:
                f.write(json.dumps(r) + "\n")

    return {
        "total_specs": len(spec_files),
        "discrepancies": discrepancies,
        "synced_count": synced_count,
        "is_consistent": (len(discrepancies) == 0)
    }


def main():
    parser = argparse.ArgumentParser(description="Audit and synchronize benchmark metadata")
    parser.add_argument("--sync", action="store_true", help="Sync fixtures and jsonl from specs")
    args = parser.parse_args()

    res = audit_and_sync(sync=args.sync)
    print(f"Total Specs: {res['total_specs']}")
    print(f"Discrepancies: {len(res['discrepancies'])}")
    print(f"Synced Count: {res['synced_count']}")
    print(f"Consistent: {res['is_consistent']}")

    if not res["is_consistent"] and not args.sync:
        print("\nDiscrepancies found:")
        for d in res["discrepancies"]:
            print(json.dumps(d, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()
