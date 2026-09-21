#!/usr/bin/env python3
"""
scripts/prepare_human_annotation_package_v2_1.py

Generates unlabelled human annotation packages for independent multi-annotator evaluation:
- data/memory_validity_v2_1/human_annotation_package_v2_1.jsonl
- data/memory_validity_v2_1/human_annotation_template_annotator_a.csv
- data/memory_validity_v2_1/human_annotation_template_annotator_b.csv

Strict Raw Evidence Only:
- base_commit, target_commit, base_source_excerpt, target_source_excerpt, diff_hunk
- execution: {base_exit_code, target_exit_code, stderr_excerpt}
- ZERO category, ZERO gold labels, ZERO expected answers, ZERO researcher conclusion strings.
"""

import os
import sys
import csv
import json

sys.path.insert(0, "/code/rolemem-agent-memory")

BLIND_INPUTS_PATH = "/code/rolemem-agent-memory/data/memory_validity_v2_1/blind_inputs.jsonl"
OUT_DIR = "/code/rolemem-agent-memory/data/memory_validity_v2_1"


def prepare_package():
    with open(BLIND_INPUTS_PATH, "r", encoding="utf-8") as f:
        cases = [json.loads(line) for line in f if line.strip()]

    pkg_jsonl = os.path.join(OUT_DIR, "human_annotation_package_v2_1.jsonl")
    csv_a = os.path.join(OUT_DIR, "human_annotation_template_annotator_a.csv")
    csv_b = os.path.join(OUT_DIR, "human_annotation_template_annotator_b.csv")

    # 1. Package JSONL
    with open(pkg_jsonl, "w", encoding="utf-8") as f:
        for c in cases:
            case_id = c["case_id"]

            # Extract raw execution evidence if available from artifacts
            exec_info = {
                "base_exit_code": None,
                "target_exit_code": None,
                "stderr_excerpt": ""
            }
            for sub in ["contracts", "counterfactuals", "behavior_breaks"]:
                art_path = os.path.join(OUT_DIR, sub, f"{case_id}.json")
                if os.path.exists(art_path):
                    try:
                        with open(art_path, "r", encoding="utf-8") as af:
                            art_data = json.load(af)
                            b_exec = art_data.get("base_execution") or {}
                            t_exec = art_data.get("target_execution") or {}
                            exec_info = {
                                "base_exit_code": b_exec.get("exit_code"),
                                "target_exit_code": t_exec.get("exit_code"),
                                "stderr_excerpt": (t_exec.get("stderr") or "")[:500].strip()
                            }
                    except Exception:
                        pass
                    break

            pkg_item = {
                "case_id": case_id,
                "repository": c["repository"],
                "base_commit": c.get("base_commit", ""),
                "target_commit": c.get("target_commit", ""),
                "file_path": c["file_path"],
                "symbol_qualified_name": c["symbol_qualified_name"],
                "memory_statement": c["memory_statement"],
                "base_source_excerpt": c.get("base_source_excerpt", ""),
                "target_source_excerpt": c.get("target_source_excerpt", ""),
                "diff_hunk": c.get("diff_hunk", ""),
                "execution": exec_info
            }
            f.write(json.dumps(pkg_item) + "\n")

    # 2. Blank CSV Templates
    headers = [
        "case_id",
        "annotator_id",
        "decision",  # VALID, STALE, UNCERTAIN
        "confidence",  # 0.0 - 1.0
        "rationale",
        "affected_by_file_diff",  # YES, NO, UNCERTAIN
        "affected_by_symbol_edit",  # YES, NO, UNCERTAIN
        "affected_by_dependency_break"  # YES, NO, UNCERTAIN
    ]

    for cpath, annotator_name in [(csv_a, "Annotator_A"), (csv_b, "Annotator_B")]:
        with open(cpath, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            for c in cases:
                writer.writerow([
                    c["case_id"],
                    annotator_name,
                    "",  # blank decision
                    "",  # blank confidence
                    "",  # blank rationale
                    "",
                    "",
                    ""
                ])

    print(f"=== Human Annotation Package V2.1 Generated ({len(cases)} cases) ===")
    print(f"  Package JSONL: {pkg_jsonl}")
    print(f"  Annotator A CSV Template: {csv_a}")
    print(f"  Annotator B CSV Template: {csv_b}")


if __name__ == "__main__":
    prepare_package()
