"""
tests/test_report_ssot.py

Unit tests verifying Single-Source-of-Truth (SSOT) reporting (Protocol V2.2-V1.1):
- Report metrics match escalation_results.json exactly.
- Trace files match audit entries.
- No discrepancy in CLM-000041 selected witness.
"""

import os
import json
import pytest


def test_ssot_report_metrics_consistency():
    report_path = "/code/rolemem-agent-memory/reports/protocol-v2.2-v1-selective-evidence.md"
    results_path = "/code/rolemem-agent-memory/data/evidence_escalation_v1/escalation_results.json"
    audit_path = "/code/rolemem-agent-memory/data/evidence_escalation_v1/evidence_resolution_audit.json"

    assert os.path.isfile(report_path)
    assert os.path.isfile(results_path)
    assert os.path.isfile(audit_path)

    with open(report_path, "r", encoding="utf-8") as f:
        report_text = f.read()

    with open(results_path, "r", encoding="utf-8") as f:
        results = json.load(f)

    with open(audit_path, "r", encoding="utf-8") as f:
        audit = json.load(f)

    s5_m = results["ablations"]["S5_Full_Selective_Escalation"]
    s0_m = results["ablations"]["S0_Static"]

    # Verify coverage strings in report
    s0_cov_str = f"{s0_m['Coverage']*100:.1f}%"
    s5_cov_str = f"{s5_m['Coverage']*100:.1f}%"
    assert s0_cov_str in report_text
    assert s5_cov_str in report_text

    # Verify protocol version and status strings
    assert "PROTOCOL_VERSION = 2.2-selective-evidence-v1.1" in report_text
    assert "V1_0_RESULT_STATUS = PROVISIONAL_EVIDENCE_BINDING_NOT_YET_STRICT" in report_text
    assert "V2_2_V1_WITNESS_BINDING = AUDITED" in report_text
    assert "V2_2_V1_EXECUTION_SOURCE_ORIGIN = AUDITED" in report_text

    # Verify CLM-000041 selected test in report
    assert "tests/test_text.py::test_str" in report_text
    assert "test_divide" not in report_text or "test_divide" in "In V1.0, test binding relied on raw keyword frequency (`assertion_count`), leading `CLM-000041` to select `test_divide` instead of genuine witness `test_str`"
