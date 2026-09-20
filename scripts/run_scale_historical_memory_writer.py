#!/usr/bin/env python3
"""
scripts/run_scale_historical_memory_writer.py

Runs HistoricalMemoryWriterV4 on selected Scale Challenge candidates (seeds 42, 123, 999)
using strictly base snapshot and historical commits (no target PR, diff, or spec strings).
Evaluates results with fail-closed HistoricalClaimFactualityAuditorV2.
Outputs to runs/historical-memory-writer-scale/<tid>/<seed>.json
"""

import os
import sys
import json
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

sys.path.insert(0, "/code/rolemem-agent-memory")
from src.historical_memory_writer_v4 import HistoricalMemoryWriterV4
from src.historical_claim_factuality_v2 import HistoricalClaimFactualityAuditorV2

MANIFEST_PATH = "/code/rolemem-agent-memory/data/track_a_scale_manifest.jsonl"
OUT_BASE = "/code/rolemem-agent-memory/runs/historical-memory-writer-scale"
SEEDS = [42, 123, 999]

CANDIDATE_TIDS = [
    "trans_track_a_15_more_itertools_zip_equal_removal",
    "trans_track_a_16_rich_file_proxy_isatty",
    "trans_track_a_20_iniconfig_strip_inline_comments",
    "trans_track_a_24_cachelib_timeout_timedelta",
    "trans_track_a_25_uvicorn_wsgi_middleware_deprecation",
    "trans_track_a_26_rich_render_group_to_group"
]

CANDIDATE_BASE_SYMBOLS = {
    "trans_track_a_15_more_itertools_zip_equal_removal": "zip_equal",
    "trans_track_a_16_rich_file_proxy_isatty": "FileProxy",
    "trans_track_a_20_iniconfig_strip_inline_comments": "IniConfig",
    "trans_track_a_24_cachelib_timeout_timedelta": "BaseCache",
    "trans_track_a_25_uvicorn_wsgi_middleware_deprecation": "WSGIMiddleware",
    "trans_track_a_26_rich_render_group_to_group": "RenderGroup"
}

def main():
    model_dir = "/code/rolemem-agent-memory/models/qwen2.5-coder-7b"
    print(f"Loading Qwen2.5-Coder-7B from {model_dir}...")
    tokenizer = AutoTokenizer.from_remote_code = True
    tokenizer = AutoTokenizer.from_pretrained(model_dir, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        model_dir,
        torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
        device_map="auto" if torch.cuda.is_available() else None
    )
    model.eval()

    writer = HistoricalMemoryWriterV4(
        model_dir=model_dir,
        tokenizer=tokenizer,
        model=model
    )
    auditor = HistoricalClaimFactualityAuditorV2(
        use_llm=True,
        model=model,
        tokenizer=tokenizer
    )

    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        all_manifest = [json.loads(line) for line in f if line.strip()]

    target_items = [item for item in all_manifest if item["transition_id"] in CANDIDATE_TIDS]
    print(f"Selected {len(target_items)} candidate transitions for Scale Historical Memory generation.")

    summary = {}

    for item in target_items:
        tid = item["transition_id"]
        repo_name = item["repo_name"].split("/")[-1]
        repo_path = f"/code/repo_cache/{repo_name}"
        base_commit = item["base_commit"]
        primary_file = item["primary_file"]
        changed_files = item.get("changed_files", [primary_file])
        symbol = CANDIDATE_BASE_SYMBOLS.get(tid, item["symbol"].split(".")[-1])

        print(f"\n==================== {tid} (sym: {symbol}) ====================")
        summary[tid] = {}

        for seed in SEEDS:
            rec, telemetry = writer.write_historical_memory(
                repo_path=repo_path,
                base_commit=base_commit,
                target_file=primary_file,
                symbol=symbol,
                task_id=tid,
                max_retries=3,
                seed=seed,
                candidate_files=changed_files
            )

            statement = telemetry.get("statement", "")
            base_source_hunk = telemetry.get("base_source_hunk", "")
            history_commits = telemetry.get("history_commits", [])

            # Get base content for auditing
            import subprocess
            try:
                base_content = subprocess.check_output(
                    ["git", "-C", repo_path, "show", f"{base_commit}:{primary_file}"],
                    env={**os.environ, "GIT_NO_LAZY_FETCH": "1"}
                ).decode("utf-8", errors="ignore")
            except Exception:
                base_content = base_source_hunk

            # Audit with Fail-Closed Factuality Auditor V2
            audit_res = auditor.audit_claim(
                statement=statement,
                spec=item,
                base_content=base_content,
                base_source_hunk=base_source_hunk,
                relevant_history=history_commits
            )

            telemetry["tier_a_temporal_isolation"] = audit_res["temporal_isolation_pass"]
            telemetry["tier_b_structural_grounding"] = audit_res["structural_evidence_grounded"]
            telemetry["tier_c_semantic_factuality"] = audit_res["semantic_factuality_pass"]
            telemetry["factuality_status"] = audit_res["semantic_factuality_status"]
            telemetry["factuality_explanation"] = audit_res["explanation"]

            # Save to runs/historical-memory-writer-scale/<tid>/<seed>.json
            out_dir = os.path.join(OUT_BASE, tid)
            os.makedirs(out_dir, exist_ok=True)
            out_file = os.path.join(out_dir, f"{seed}.json")
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(telemetry, f, indent=2)

            print(f"  Seed {seed}:")
            print(f"    Statement: {statement[:70]}...")
            print(f"    Tier A (Temporal): {audit_res['temporal_isolation_pass']}")
            print(f"    Tier B (Grounding): {audit_res['structural_evidence_grounded']}")
            print(f"    Tier C (Factuality): {audit_res['semantic_factuality_pass']} ({audit_res['semantic_factuality_status']})")
            print(f"    Saved -> {out_file}")

            summary[tid][seed] = {
                "statement": statement,
                "tier_a": audit_res["temporal_isolation_pass"],
                "tier_b": audit_res["structural_evidence_grounded"],
                "tier_c": audit_res["semantic_factuality_pass"],
                "status": audit_res["semantic_factuality_status"]
            }

    print("\nScale Historical Memory Generation complete.")

if __name__ == "__main__":
    main()
