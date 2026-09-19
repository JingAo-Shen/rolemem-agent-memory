#!/usr/bin/env python3
"""
scripts/run_historical_memory_writer_v4.py

Executes HistoricalMemoryWriterV4 across all 10 Track A reconstructed transitions
for seeds 42, 123, 999, enforcing pure historical framing, hard failure, and
recording raw generation telemetry in runs/historical-memory-writer-v4/<tid>/<seed>.json.
"""

import os
import sys
import json
import torch

sys.path.insert(0, "/code/rolemem-agent-memory")
from src.historical_memory_writer_v4 import HistoricalMemoryWriterV4
from transformers import AutoTokenizer, AutoModelForCausalLM

MANIFEST_PATH = "/code/rolemem-agent-memory/data/track_a_reconstructed_manifest.jsonl"
OUT_BASE = "/code/rolemem-agent-memory/runs/historical-memory-writer-v4"
SEEDS = [42, 123, 999]

# Mapping of transitions to base-state canonical symbols to inspect
HISTORICAL_SYMBOLS = {
    "trans_track_a_01_click_stream_deprecations": "get_binary_stream",
    "trans_track_a_02_flask_should_ignore_error": "should_ignore_error",
    "trans_track_a_03_werkzeug_environ_property": "environ_property",
    "trans_track_a_04_jinja_version_deprecation": "__version__",
    "trans_track_a_05_itsdangerous_version_removal": "__version__",
    "trans_track_a_06_markupsafe_version_removal": "__version__",
    "trans_track_a_07_pluggy_varnames_noself": "varnames",
    "trans_track_a_08_attrs_py313_replace_control": "evolve",
    "trans_track_a_09_virtualenv_drop_py38_control": "CPython3Posix.pyvenv_launch_patch_active",
    "trans_track_a_10_httpx_client_proxies_deprecation": "proxies",
}

def main():
    model_dir = "/code/rolemem-agent-memory/models/qwen2.5-coder-7b"
    print(f"Loading Qwen2.5-Coder-7B from {model_dir}...")
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

    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        transitions = [json.loads(line) for line in f if line.strip()]

    print(f"Loaded {len(transitions)} transitions. Running HistoricalMemoryWriterV4...")

    summary = {}

    for item in transitions:
        tid = item["transition_id"]
        repo_name = item["repo_name"].split("/")[-1]
        repo_path = f"/code/repo_cache/{repo_name}"
        base_commit = item["base_commit"]
        primary_file = item["primary_file"]
        changed_files = item.get("changed_files", [primary_file])
        symbol = HISTORICAL_SYMBOLS.get(tid, item["changed_symbols"][0])

        print(f"\n--- {tid} (sym: {symbol}) ---")
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

            status = telemetry.get("verdict") or telemetry.get("status")
            statement = telemetry.get("statement", "")
            print(f"  Seed {seed}: status={status} | stmt={statement[:60]}...")
            summary[tid][seed] = {
                "status": status,
                "statement": statement,
                "symbol": telemetry.get("symbol"),
                "criteria": telemetry.get("criteria")
            }

    print("\nAll historical memory runs completed.")

if __name__ == "__main__":
    main()
