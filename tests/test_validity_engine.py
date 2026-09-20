"""
tests/test_validity_engine.py

Unit tests for src/validity/ engine, baseline checkers, and edge cases.
Protocol V2.1 specification.
"""

import pytest
from src.validity import (
    FileValidityChecker,
    SymbolValidityChecker,
    DependencyValidityChecker,
    RoleMemValidityEngine,
    ValidityResult
)


def test_file_validity_checker():
    checker = FileValidityChecker()
    code_a = "def foo():\n    return 42\n"
    code_b = "def foo():\n    return 42\n"
    code_c = "def foo():\n    return 43\n"

    res_same = checker.evaluate(code_a, code_b)
    assert res_same.decision == "VALID"
    assert res_same.file_changed is False
    assert res_same.confidence == 1.0

    res_diff = checker.evaluate(code_a, code_c)
    assert res_diff.decision == "STALE"
    assert res_diff.file_changed is True
    assert res_diff.confidence == 1.0


def test_symbol_validity_case1_file_changed_symbol_same():
    checker = SymbolValidityChecker()
    base_src = "def bar():\n    pass\n\ndef foo():\n    return 42\n"
    target_src = "def bar():\n    print('modified')\n\ndef foo():\n    return 42\n"

    res = checker.evaluate(base_src, target_src, "foo")
    assert res.decision == "VALID"
    assert res.symbol_changed is False
    assert res.symbol_removed is False


def test_symbol_validity_case2_symbol_removed():
    checker = SymbolValidityChecker()
    base_src = "def foo():\n    return 42\n"
    target_src = "def bar():\n    return 42\n"

    res = checker.evaluate(base_src, target_src, "foo")
    assert res.decision == "STALE"
    assert res.symbol_removed is True
    assert res.symbol_changed is True


def test_symbol_validity_case3_symbol_internal_change_uncertain():
    checker = SymbolValidityChecker()
    base_src = "def foo(x):\n    return x + 1\n"
    target_src = "def foo(x: int) -> int:\n    return x + 1\n"

    res = checker.evaluate(base_src, target_src, "foo")
    assert res.decision == "UNCERTAIN"
    assert res.symbol_changed is True
    assert res.symbol_removed is False


def test_dependency_validity_case4_dependency_import_removed():
    checker = DependencyValidityChecker()
    base_src = "from os.path import join\n\ndef build_path(a, b):\n    return join(a, b)\n"
    target_src = "def build_path(a, b):\n    return join(a, b)\n"

    res = checker.evaluate(base_src, target_src, "build_path")
    assert res.decision == "STALE"
    assert res.dependency_changed is True


def test_rolemem_validity_engine_end_to_end():
    engine = RoleMemValidityEngine()

    # Case 1: Unchanged symbol, unrelated file edit -> VALID
    base_1 = "# header\ndef helper():\n    return 1\ndef target():\n    return helper()\n"
    target_1 = "# header edited\ndef helper():\n    return 1\ndef target():\n    return helper()\n"
    res1 = engine.evaluate(
        memory_statement="target returns helper",
        symbol_qualified_name="target",
        base_source=base_1,
        target_source=target_1
    )
    assert res1.decision == "VALID"
    assert res1.file_changed is True
    assert res1.symbol_changed is False

    # Case 2: Symbol deleted -> STALE
    base_2 = "def target():\n    return 1\n"
    target_2 = "def other():\n    return 1\n"
    res2 = engine.evaluate(
        memory_statement="target returns 1",
        symbol_qualified_name="target",
        base_source=base_2,
        target_source=target_2
    )
    assert res2.decision == "STALE"
    assert res2.symbol_removed is True

    # Case 3: Symbol modified -> UNCERTAIN
    base_3 = "def target(a):\n    return a * 2\n"
    target_3 = "def target(a, b=0):\n    return a * 2 + b\n"
    res3 = engine.evaluate(
        memory_statement="target doubles a",
        symbol_qualified_name="target",
        base_source=base_3,
        target_source=target_3
    )
    assert res3.decision == "UNCERTAIN"
    assert res3.symbol_changed is True

    # Case 4: Symbol same, imported dependency removed in target -> STALE
    base_4 = "from utils import compute\ndef target():\n    return compute()\n"
    target_4 = "def target():\n    return compute()\n"
    res4 = engine.evaluate(
        memory_statement="target calls compute",
        symbol_qualified_name="target",
        base_source=base_4,
        target_source=target_4
    )
    assert res4.decision == "STALE"
    assert res4.dependency_changed is True
