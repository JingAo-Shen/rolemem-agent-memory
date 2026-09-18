"""
scripts/verify_seeds_v6.py
Runs TransitionVerifierV6 across all 10 seed specs.
Generates data/seed_status_v6.jsonl with strict 8-gate boolean verification.
"""

import os
import sys
import json

sys.path.insert(0, "/code/rolemem-agent-memory")
from src.transition_verifier_v6 import TransitionVerifierV6

SPECS_DIR = "/code/rolemem-agent-memory/data/specs"
OUT_FILE = "/code/rolemem-agent-memory/data/seed_status_v6.jsonl"

SEEDS = [
    "trans_gold_click_01_option_parser",
    "trans_gold_click_02_isolated_filesystem",
    "trans_gold_flask_01_context_stack_removal",
    "trans_gold_flask_02_should_ignore_error",
    "trans_gold_requests_01_tls_context_adapter",
    "trans_gold_requests_02_pool_key_overrides",
    "trans_gold_urllib3_01_retry_allowed_methods",
    "trans_gold_urllib3_02_empty_allowed_methods",
    "trans_gold_werkzeug_01_cached_property",
    "trans_gold_werkzeug_02_environ_properties",
]


def run():
    verifier = TransitionVerifierV6()
    results = []

    print("=== Running TransitionVerifierV6 on 10 Seed Specs ===")
    for tid in SEEDS:
        spec_p = os.path.join(SPECS_DIR, f"{tid}.json")
        with open(spec_p) as f:
            candidate = json.load(f)

        res = verifier.verify_candidate_v6(candidate)
        print(f"[{res['seed_status']}] {tid} (Causality: {res['causality_status']}, Ground Truth V3: {res['gates']['gate7_external_ground_truth_v3']}, Semantic V2: {res['gates']['gate8_semantic_coherence_v2']})")
        results.append(res)

    with open(OUT_FILE, "w") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")

    accept_count = sum(1 for r in results if r["seed_status"] == "SEED_ACCEPT")
    rebuild_count = sum(1 for r in results if r["seed_status"] == "REBUILD")
    reject_count = sum(1 for r in results if r["seed_status"] == "REJECT")

    print("\n==================================================")
    print("TransitionVerifierV6 Summary:")
    print(f"  SEED_ACCEPT: {accept_count}")
    print(f"  REBUILD:     {rebuild_count}")
    print(f"  REJECT:      {reject_count}")
    print(f"  Saved to {OUT_FILE}")
    print("==================================================")


if __name__ == "__main__":
    run()
