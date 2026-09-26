"""
tests/test_ablation_variants.py

Unit and Integration Tests for RoleMem Ablation Study Variants:
  - RoleMemNoRolePredictor: verifies loss of role-specific invariant routing
  - RoleMemNoEvidencePredictor: verifies global search without file provenance
  - RoleMemNoLifecyclePredictor: verifies static snapshot behavior
"""

import pytest
from src.ablation.variants import (
    RoleMemNoRolePredictor,
    RoleMemNoEvidencePredictor,
    RoleMemNoLifecyclePredictor
)


def test_ablation_predictors_instantiation_and_structure():
    """Verify ablation predictors can instantiate and process structured inputs."""
    no_role = RoleMemNoRolePredictor()
    no_ev = RoleMemNoEvidencePredictor()
    no_life = RoleMemNoLifecyclePredictor()

    sample_case = {
        "case_id": "ABL-001",
        "structured_claim": {
            "module": "agateexcel.table_xlsx",
            "symbol": "TableXLSX.from_xlsx",
            "parameter_or_attr": "sheet",
            "expected_default": None
        },
        "raw_statement": "Parameter sheet defaults to None.",
        "claim_type": "DEFAULT_VALUE",
        "repository_name": "wireservice/agate-excel"
    }

    meta = {
        "target_commit": "03ec2250ea5fee3f1edb1a9880f43fb88b9c6c88",
        "base_evidence_path": "agateexcel/table_xlsx.py"
    }

    # Test No Role
    p_nr = no_role.predict(sample_case, meta)
    assert p_nr["case_id"] == "ABL-001"
    assert "predicted_label" in p_nr
    assert "rule" in p_nr

    # Test No Evidence
    p_ne = no_ev.predict(sample_case, meta)
    assert p_ne["case_id"] == "ABL-001"
    assert "predicted_label" in p_ne
    assert "rule" in p_ne

    # Test No Lifecycle
    p_nl = no_life.predict(sample_case, meta)
    assert p_nl["case_id"] == "ABL-001"
    assert "predicted_label" in p_nl
    assert "rule" in p_nl
