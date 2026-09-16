"""
Gate 2 Automated Tests: Cross-Method State Isolation and Method-Order Invariance.
"""

import copy
import random
import pytest
from src.schema_v1 import MemoryRecordV1
from src.baselines_v1 import BaselineRunnerV1
from src.budgeter import MemoryBudgeter


def make_evolving_memory_fixture():
    """Create a realistic memory fixture with supersedes chains and artifact references."""
    m1 = MemoryRecordV1(
        memory_id="mem_01_old_cfg",
        artifact_uri="src/config.py",
        artifact_type="config",
        symbol="PORT",
        source_commit="c1",
        observed_at=100.0,
        evidence_type="diff",
        evidence_ref="c1.diff",
        valid_from=100.0,
        valid_to=float('inf'),
        statement="Default port is 8080.",
        artifact_digest="hash_cfg_v1"
    )

    m2 = MemoryRecordV1(
        memory_id="mem_02_new_cfg",
        artifact_uri="src/config.py",
        artifact_type="config",
        symbol="PORT",
        source_commit="c2",
        observed_at=200.0,
        evidence_type="spec",
        evidence_ref="rfc_port.md",
        valid_from=200.0,
        valid_to=float('inf'),
        supersedes="mem_01_old_cfg",
        statement="Default port updated to 9000. Port 8080 is deprecated.",
        artifact_digest="hash_cfg_v2"
    )

    m3 = MemoryRecordV1(
        memory_id="mem_03_auth",
        artifact_uri="src/auth.py",
        artifact_type="file",
        symbol="KEY",
        source_commit="c1",
        observed_at=150.0,
        evidence_type="test",
        evidence_ref="auth.log",
        valid_from=150.0,
        valid_to=float('inf'),
        statement="Use Bearer token authentication.",
        artifact_digest="hash_auth_v1"
    )

    return [m1, m2, m3]


def test_original_memories_are_never_mutated():
    """Verify that calling any baseline leaves original MemoryRecord objects completely untouched."""
    original_mems = make_evolving_memory_fixture()
    mems_snapshot_before = [copy.deepcopy(m.to_dict()) for m in original_mems]
    ws = {"src/config.py": "new_content", "src/auth.py": "auth_content"}

    # Execute F (which mutates stores and invalidates records internally)
    BaselineRunnerV1.run_F_rolemem_full("port", "coder", 500.0, ws, original_mems)
    # Execute B5
    BaselineRunnerV1.run_B5_memstrata_temporal_supersession("port", "coder", 500.0, ws, original_mems)
    # Execute B3
    BaselineRunnerV1.run_B3_bm25_unscoped("port", "coder", 500.0, ws, original_mems)

    mems_snapshot_after = [m.to_dict() for m in original_mems]
    assert mems_snapshot_before == mems_snapshot_after, "Original memory records were mutated in-place by baselines!"


def test_method_order_invariance():
    """
    Method-Order Invariance Test:
    Running B3 -> B5 -> F must yield EXACTLY the same results as F -> B5 -> B3.
    """
    ws = {"src/config.py": "new_content", "src/auth.py": "auth_content"}
    query = "port configuration and auth"
    role = "coder"
    t = 500.0

    # Order 1: B3 -> B5 -> F
    mems_order1 = make_evolving_memory_fixture()
    res_b3_order1, tok_b3_1 = BaselineRunnerV1.run_B3_bm25_unscoped(query, role, t, ws, mems_order1)
    res_b5_order1, tok_b5_1 = BaselineRunnerV1.run_B5_memstrata_temporal_supersession(query, role, t, ws, mems_order1)
    res_f_order1, tok_f_1 = BaselineRunnerV1.run_F_rolemem_full(query, role, t, ws, mems_order1)

    # Order 2: F -> B5 -> B3
    mems_order2 = make_evolving_memory_fixture()
    res_f_order2, tok_f_2 = BaselineRunnerV1.run_F_rolemem_full(query, role, t, ws, mems_order2)
    res_b5_order2, tok_b5_2 = BaselineRunnerV1.run_B5_memstrata_temporal_supersession(query, role, t, ws, mems_order2)
    res_b3_order2, tok_b3_2 = BaselineRunnerV1.run_B3_bm25_unscoped(query, role, t, ws, mems_order2)

    # Strict Equality Assertions
    assert res_f_order1 == res_f_order2, "F output differed between execution orders!"
    assert tok_f_1 == tok_f_2
    assert res_b5_order1 == res_b5_order2, "B5 output differed between execution orders!"
    assert tok_b5_1 == tok_b5_2
    assert res_b3_order1 == res_b3_order2, "B3 output differed between execution orders!"
    assert tok_b3_1 == tok_b3_2


def test_random_permutation_order_invariance():
    """Test invariance across 10 random permutations of method execution."""
    ws = {"src/config.py": "new_content", "src/auth.py": "auth_content"}
    query = "port"
    role = "coder"
    t = 500.0

    baseline_funcs = {
        "B1": BaselineRunnerV1.run_B1_recent_raw_history,
        "B2": BaselineRunnerV1.run_B2_chronological_history,
        "B3": BaselineRunnerV1.run_B3_bm25_unscoped,
        "B4": BaselineRunnerV1.run_B4_bm25_temporal,
        "B5": BaselineRunnerV1.run_B5_memstrata_temporal_supersession,
        "F": BaselineRunnerV1.run_F_rolemem_full,
    }

    # Collect reference outputs
    ref_mems = make_evolving_memory_fixture()
    reference_outputs = {}
    for name, func in baseline_funcs.items():
        txt, tok = func(query, role, t, ws, ref_mems)
        reference_outputs[name] = (txt, tok)

    # Test 10 random execution permutations
    rng = random.Random(42)
    for trial in range(10):
        shared_mems = make_evolving_memory_fixture()
        method_names = list(baseline_funcs.keys())
        rng.shuffle(method_names)

        for name in method_names:
            func = baseline_funcs[name]
            txt, tok = func(query, role, t, ws, shared_mems)
            ref_txt, ref_tok = reference_outputs[name]
            assert txt == ref_txt, f"Method {name} produced divergent text in permutation trial {trial}!"
            assert tok == ref_tok, f"Method {name} produced divergent token count in permutation trial {trial}!"
