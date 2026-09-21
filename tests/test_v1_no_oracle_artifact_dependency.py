"""
tests/test_v1_no_oracle_artifact_dependency.py

Scientific Integrity Test:
Verifies that Protocol V2.2-V1 Evidence Escalation modules and evaluation scripts
contain ZERO dependencies or references to V2.1 oracle artifact directories:
- data/memory_validity_v2_1/contracts/
- data/memory_validity_v2_1/counterfactuals/
- data/memory_validity_v2_1/behavior_breaks/
"""

import os
import glob
import pytest

FORBIDDEN_PATTERNS = [
    "memory_validity_v2_1/contracts",
    "memory_validity_v2_1/counterfactuals",
    "memory_validity_v2_1/behavior_breaks",
    "data/memory_validity_v2_1/contracts",
    "data/memory_validity_v2_1/counterfactuals",
    "data/memory_validity_v2_1/behavior_breaks",
    "contracts/",
    "counterfactuals/",
    "behavior_breaks/"
]

SCAN_TARGETS = [
    "/code/rolemem-agent-memory/src/evidence_escalation/**/*.py",
    "/code/rolemem-agent-memory/scripts/evaluate_evidence_escalation_v1.py"
]


def test_no_oracle_artifact_dependencies_in_v1():
    files_to_check = []
    for pattern in SCAN_TARGETS:
        files_to_check.extend(glob.glob(pattern, recursive=True))

    assert len(files_to_check) > 0, "No files found to scan for oracle artifact dependencies!"

    violations = []
    for fpath in files_to_check:
        if not os.path.exists(fpath):
            continue
        with open(fpath, "r", encoding="utf-8") as f:
            content = f.read()

        for pat in FORBIDDEN_PATTERNS:
            if pat in content:
                violations.append(f"Forbidden oracle artifact reference '{pat}' found in {fpath}")

    assert not violations, "\n".join(violations)
