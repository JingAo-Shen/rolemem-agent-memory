"""
tests/test_v2_2_no_benchmark_specific_rules.py

Unit tests verifying that Protocol V2.2 claim validity code contains zero hardcoded
benchmark-specific rules, case IDs, or dataset-specific coupling.
"""

import os
import re
import pytest

SRC_CLAIM_DIR = "/code/rolemem-agent-memory/src/claim_validity"
EVAL_SCRIPT_PATH = "/code/rolemem-agent-memory/scripts/evaluate_claim_validity_v2_2.py"


def test_no_case_ids_in_src_claim_validity():
    """Ensure no benchmark case IDs (MV21-*, MV20-*) are hardcoded in src/claim_validity."""
    case_pattern = re.compile(r"MV2[0-9]-[0-9]{6}")
    for root, _, files in os.walk(SRC_CLAIM_DIR):
        for f in files:
            if f.endswith(".py"):
                fp = os.path.join(root, f)
                with open(fp, "r", encoding="utf-8") as file:
                    content = file.read()
                    matches = case_pattern.findall(content)
                    assert not matches, f"Found hardcoded case IDs in {fp}: {matches}"


def test_no_benchmark_specific_keywords_in_src():
    """Ensure no benchmark-specific keyword heuristics (hookspec, varnames) are hardcoded in src/claim_validity."""
    banned_tokens = ["hookspec", "varnames"]
    for root, _, files in os.walk(SRC_CLAIM_DIR):
        for f in files:
            if f.endswith(".py"):
                fp = os.path.join(root, f)
                with open(fp, "r", encoding="utf-8") as file:
                    lines = file.readlines()
                    for line_idx, line in enumerate(lines, 1):
                        lower_line = line.lower()
                        for tok in banned_tokens:
                            assert tok not in lower_line, f"Found banned token '{tok}' in {fp}:{line_idx}: {line.strip()}"


def test_no_benchmark_coupling_in_evaluator():
    """Ensure evaluation script does not use conditional hacks on symbol names or repos."""
    if os.path.exists(EVAL_SCRIPT_PATH):
        with open(EVAL_SCRIPT_PATH, "r", encoding="utf-8") as f:
            content = f.read()
            assert "hookspec" not in content.lower(), "Evaluator script must not contain 'hookspec' hack"
            assert "varnames" not in content.lower(), "Evaluator script must not contain 'varnames' hack"
