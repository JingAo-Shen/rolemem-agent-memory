#!/usr/bin/env python3
"""
scripts/migrate_v2_1_to_dev_claims.py

Migrates the 55 Protocol V2.1 development benchmark cases into Protocol V2.2 Claim Fixtures:
- data/claim_validity_v2_2/dev_claims.jsonl

Strict Non-Mutation Rule:
- Does NOT alter V2.1 memory_statement strings or labels.
- Unparsable statements are marked as claim_parse_status = "UNRESOLVED".
"""

import os
import sys
import json

sys.path.insert(0, "/code/rolemem-agent-memory")
from src.claim_validity.claim_extractor import DeterministicClaimExtractor
from src.claim_validity.types import ClaimType

V2_1_BLIND_PATH = "/code/rolemem-agent-memory/data/memory_validity_v2_1/blind_inputs.jsonl"
V2_1_GOLD_PATH = "/code/rolemem-agent-memory/data/memory_validity_v2_1/gold_labels.jsonl"
OUT_DIR = "/code/rolemem-agent-memory/data/claim_validity_v2_2"

os.makedirs(OUT_DIR, exist_ok=True)


def migrate_cases():
    with open(V2_1_BLIND_PATH, "r", encoding="utf-8") as f:
        blind_cases = [json.loads(line) for line in f if line.strip()]

    with open(V2_1_GOLD_PATH, "r", encoding="utf-8") as f:
        gold_map = {r["case_id"]: r for r in [json.loads(line) for line in f if line.strip()]}

    extractor = DeterministicClaimExtractor()
    dev_claims = []

    parsed_count = 0
    unresolved_count = 0
    claim_type_counts = {}

    for idx, c in enumerate(blind_cases, start=1):
        cid = c["case_id"]
        gold = gold_map.get(cid, {})
        raw_stmt = c["memory_statement"]
        sym = c["symbol_qualified_name"]
        repo = c["repository"]
        fpath = c["file_path"]

        claim = extractor.extract(
            raw_statement=raw_stmt,
            claim_id=f"CLM-{idx:06d}",
            repository=repo,
            file_path=fpath,
            symbol=sym,
            source_case_id=cid
        )

        if claim.claim_parse_status == "PARSED":
            parsed_count += 1
        else:
            unresolved_count += 1

        ct_val = claim.claim_type.value if hasattr(claim.claim_type, "value") else str(claim.claim_type)
        claim_type_counts[ct_val] = claim_type_counts.get(ct_val, 0) + 1

        record = {
            **claim.to_dict(),
            "base_commit": c.get("base_commit", ""),
            "target_commit": c.get("target_commit", ""),
            "gold_label": gold.get("gold_label", "UNKNOWN"),
            "category": gold.get("category", "UNKNOWN")
        }
        dev_claims.append(record)

    out_file = os.path.join(OUT_DIR, "dev_claims.jsonl")
    with open(out_file, "w", encoding="utf-8") as f:
        for r in dev_claims:
            f.write(json.dumps(r) + "\n")

    print(f"=== Protocol V2.2 Dev Claims Generated ({len(dev_claims)} cases) ===")
    print(f"  Target File: {out_file}")
    print(f"  Parsed Claims: {parsed_count}/{len(dev_claims)} ({parsed_count/len(dev_claims)*100:.1f}%)")
    print(f"  Unresolved Claims: {unresolved_count}/{len(dev_claims)} ({unresolved_count/len(dev_claims)*100:.1f}%)")
    print("  Claim Type Breakdown:")
    for ct, count in claim_type_counts.items():
        print(f"    - {ct}: {count}")


if __name__ == "__main__":
    migrate_cases()
