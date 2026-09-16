"""
scripts/verify_seed_benchmark_v4.py
Runs TransitionVerifierV4 across all canonical specs in data/specs/*.json.
Enforces the 7-gate acceptance formula.
Outputs raw verifier results into data/verifier_results/<transition_id>.json.
"""

import os
import sys
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.transition_verifier_v4 import TransitionVerifierV4

SPECS_DIR = "/code/rolemem-agent-memory/data/specs"
VERIFIER_RESULTS_DIR = "/code/rolemem-agent-memory/data/verifier_results"


def main():
    verifier = TransitionVerifierV4()
    spec_files = sorted([f for f in os.listdir(SPECS_DIR) if f.endswith(".json")])

    accepted = 0
    total = len(spec_files)

    print(f"=== Running TransitionVerifierV4 across {total} transitions ===")

    for sp in spec_files:
        spec_path = os.path.join(SPECS_DIR, sp)
        with open(spec_path, "r", encoding="utf-8") as f:
            spec = json.load(f)

        tid = spec["transition_id"]
        res = verifier.verify_candidate_v4(spec)
        status = res["overall_status"]
        gates = res["gates"]

        print(f"[{tid}] {status} | Commits: {gates['commit_verification']} | "
              f"Causality: {gates['causality_status']} | "
              f"OrigTest: {gates['original_test_verification']} | "
              f"HiddenTest: {gates['hidden_test_verification']} | "
              f"Controls: {gates['fixture_control_verification']} | "
              f"Snapshot: {gates['snapshot_hash_verification']} | "
              f"GroundTruth: {gates['metadata_ground_truth_verification']}")

        if status == "ACCEPT":
            accepted += 1

    print(f"\nFinal Acceptance: {accepted}/{total} ACCEPTED")
    if accepted != total:
        sys.exit(1)


if __name__ == "__main__":
    main()
