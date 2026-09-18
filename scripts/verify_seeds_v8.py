"""
scripts/verify_seeds_v8.py
Runs TransitionVerifierV8 across all 10 seed specs.
Saves data/seed_status_v8.jsonl with decoupled integrity_status and benchmark_eligibility.
"""

import os
import sys
import json

sys.path.insert(0, "/code/rolemem-agent-memory")
from src.transition_verifier_v8 import TransitionVerifierV8

SPECS_DIR = "/code/rolemem-agent-memory/data/specs"
OUT_FILE = "/code/rolemem-agent-memory/data/seed_status_v8.jsonl"

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
    verifier = TransitionVerifierV8()
    results = []

    print("=== Running TransitionVerifierV8 on 10 Seed Specs ===")
    for tid in SEEDS:
        spec_p = os.path.join(SPECS_DIR, f"{tid}.json")
        with open(spec_p) as f:
            candidate = json.load(f)

        res = verifier.verify_candidate_v8(candidate)
        print(f"[{res['integrity_status']} | {res['benchmark_eligibility']}] {tid}")
        results.append(res)

    with open(OUT_FILE, "w") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")

    print("\n==================================================")
    print("TransitionVerifierV8 Summary:")
    for r in results:
        print(f"  {r['transition_id']}: integrity={r['integrity_status']}, eligibility={r['benchmark_eligibility']}")
    print(f"  Saved to {OUT_FILE}")
    print("==================================================")

if __name__ == "__main__":
    run()
