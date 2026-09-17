"""
scripts/verify_seed_benchmark_v5.py
Executes TransitionVerifierV5 across all seed transitions.
Outputs:
  data/verifier_results_v5/<transition_id>.json
  data/seed_status_v5.jsonl
"""

import os
import sys
import json
from typing import Dict, Any, List

sys.path.insert(0, "/code/rolemem-agent-memory")
from src.transition_verifier_v5 import TransitionVerifierV5

SPECS_DIR = "/code/rolemem-agent-memory/data/specs"
RESULTS_DIR = "/code/rolemem-agent-memory/data/verifier_results_v5"
STATUS_FILE = "/code/rolemem-agent-memory/data/seed_status_v5.jsonl"


def main():
    os.makedirs(RESULTS_DIR, exist_ok=True)
    verifier = TransitionVerifierV5()

    spec_files = sorted([f for f in os.listdir(SPECS_DIR) if f.endswith(".json")])
    print(f"=== Running TransitionVerifierV5 on {len(spec_files)} Transitions ===\n")

    records = []
    accept_count = 0
    rebuild_count = 0
    reject_count = 0

    for sf in spec_files:
        spec_path = os.path.join(SPECS_DIR, sf)
        with open(spec_path, "r", encoding="utf-8") as f:
            candidate = json.load(f)

        tid = candidate["transition_id"]
        res = verifier.verify_candidate_v5(candidate)
        status = res["overall_status"]

        # Map to canonical Seed Status enum: SEED_ACCEPT, REBUILD, REJECT, AMBIGUOUS
        if status == "ACCEPT":
            seed_status = "SEED_ACCEPT"
            accept_count += 1
        elif status == "REBUILD":
            seed_status = "REBUILD"
            rebuild_count += 1
        elif status == "AMBIGUOUS":
            seed_status = "AMBIGUOUS"
        else:
            seed_status = "REJECT"
            reject_count += 1

        rec = {
            "transition_id": tid,
            "seed_status": seed_status,
            "overall_status": status,
            "repo_name": candidate.get("repo_name"),
            "track": candidate.get("track"),
            "gates": res["gates"],
            "causality_status": res["causal_counterfactual"].get("causality_status"),
            "spec_sha256": res["spec_sha256"]
        }
        records.append(rec)

        # Save individual verifier result
        out_json = os.path.join(RESULTS_DIR, f"{tid}.json")
        with open(out_json, "w", encoding="utf-8") as f:
            json.dump(res, f, indent=2)

        print(f"[{tid}] -> {seed_status}")
        for g_name, g_val in res["gates"].items():
            print(f"   {g_name}: {g_val}")
        print()

    # Save summary jsonl
    with open(STATUS_FILE, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")

    print(f"==================================================")
    print(f"TransitionVerifierV5 Final Tally:")
    print(f"  SEED_ACCEPT: {accept_count}/{len(spec_files)}")
    print(f"  REBUILD:     {rebuild_count}/{len(spec_files)}")
    print(f"  REJECT:      {reject_count}/{len(spec_files)}")
    print(f"Status file written to: {STATUS_FILE}")
    print(f"==================================================")


if __name__ == "__main__":
    main()
