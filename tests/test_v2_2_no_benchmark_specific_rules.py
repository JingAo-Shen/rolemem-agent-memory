"""
tests/test_v2_2_no_benchmark_specific_rules.py

Comprehensive anti-coupling unit test:
- Dynamically extracts repository names, case IDs, and symbols from development claims.
- Parses src/claim_validity/**/*.py and src/evidence_escalation/**/*.py ASTs to verify that
  NO production control-flow / condition branches contain hardcoded benchmark-specific literals.
- Asserts zero benchmark-specific coupling in production logic.
"""

import os
import ast
import json
import re
import pytest

SRC_DIRS = [
    "/code/rolemem-agent-memory/src/claim_validity",
    "/code/rolemem-agent-memory/src/evidence_escalation"
]
INPUTS_PATH = "/code/rolemem-agent-memory/data/claim_validity_v2_2/dev_claim_inputs_v2r1.jsonl"


def get_benchmark_literals():
    with open(INPUTS_PATH, "r", encoding="utf-8") as f:
        dev_claims = [json.loads(line) for line in f if line.strip()]

    repo_names = set(c["repository"] for c in dev_claims)
    case_ids = set(c["source_case_id"] for c in dev_claims if c.get("source_case_id"))
    symbols = set(c["symbol"] for c in dev_claims)
    # Rare symbols specific to benchmark transitions
    specific_symbols = set(s.split(".")[-1] for s in symbols if len(s.split(".")[-1]) > 3)

    return repo_names, case_ids, specific_symbols


def test_no_benchmark_literals_in_conditions():
    """Verify that no benchmark repos, case IDs, or specific symbol names are used in if/match/compare expressions."""
    repo_names, case_ids, specific_symbols = get_benchmark_literals()

    banned_in_conditions = set(repo_names) | set(case_ids) | {"hookspec", "varnames"}

    for sdir in SRC_DIRS:
        for root, _, files in os.walk(sdir):
            for f in files:
                if not f.endswith(".py"):
                    continue
                fp = os.path.join(root, f)
                with open(fp, "r", encoding="utf-8") as file:
                    code = file.read()

                tree = ast.parse(code, filename=fp)

                # Traverse all conditional nodes
                for node in ast.walk(tree):
                    cond_node = None
                    if isinstance(node, (ast.If, ast.While)):
                        cond_node = node.test
                    elif isinstance(node, ast.IfExp):
                        cond_node = node.test
                    elif isinstance(node, ast.match_case):
                        cond_node = node.pattern

                    if cond_node is not None:
                        for sub in ast.walk(cond_node):
                            if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
                                val = sub.value.lower()
                                for b in banned_in_conditions:
                                    assert b.lower() not in val, (
                                        f"Found hardcoded benchmark literal '{b}' in condition at {fp}:{getattr(node, 'lineno', '?')}"
                                    )


def test_no_case_ids_in_src_claim_validity_and_escalation():
    """Ensure no benchmark case IDs (MV21-*, MV20-*) are present anywhere in src/claim_validity or src/evidence_escalation."""
    case_pattern = re.compile(r"MV2[0-9]-[0-9]{6}")
    for sdir in SRC_DIRS:
        for root, _, files in os.walk(sdir):
            for f in files:
                if f.endswith(".py"):
                    fp = os.path.join(root, f)
                    with open(fp, "r", encoding="utf-8") as file:
                        content = file.read()
                        matches = case_pattern.findall(content)
                        assert not matches, f"Found hardcoded case IDs in {fp}: {matches}"


def test_no_banned_keyword_hacks_in_src():
    """Ensure banned keyword hacks (hookspec, varnames) do not appear in production code."""
    banned_tokens = ["hookspec", "varnames"]
    for sdir in SRC_DIRS:
        for root, _, files in os.walk(sdir):
            for f in files:
                if f.endswith(".py"):
                    fp = os.path.join(root, f)
                    with open(fp, "r", encoding="utf-8") as file:
                        lines = file.readlines()
                        for line_idx, line in enumerate(lines, 1):
                            lower_line = line.lower()
                            # Ignore comments
                            if lower_line.strip().startswith("#") or lower_line.strip().startswith('"""'):
                                continue
                            for tok in banned_tokens:
                                assert tok not in lower_line, f"Found banned token '{tok}' in {fp}:{line_idx}: {line.strip()}"

