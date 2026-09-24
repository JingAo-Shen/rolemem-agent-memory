"""
tests/test_witness_binding.py

Regression and unit tests for strict witness binding (Protocol V2.2-V1.1):
- CLM-000041 regression test: Text str() witness binding (test_str > test_divide).
- CLM-000037 regression test: HelpFormatter write_text() + getvalue() critical chain.
- CLM-000040 regression test: Console print() + export_text(record=True) multi-operation.
- Generic built-in de-weighting test.
"""

import pytest
from src.claim_validity.types import MemoryClaim, ClaimType
from src.evidence_escalation.types import BindingStrength, TestCandidate
from src.evidence_escalation.witness_binding import WitnessBindingAnalyzer
from src.evidence_escalation.test_binding import ClaimTestBinder


def test_clm_000041_witness_binding_regression():
    """
    CLM-000041 Regression Test:
    Statement: "Text object converts to string representation containing its plain text via str()."
    Subject: "Text"
    Operations: ["str"]
    Candidate A: test_str (assert str(Text("foo")) == "foo")
    Candidate B: test_divide (10 assertions, 15 mentions of Text, but none assert str(Text(...)))
    """
    claim = MemoryClaim(
        claim_id="CLM-000041",
        claim_type=ClaimType.BEHAVIORAL_CONTRACT,
        subject="Text",
        predicate="converts_to",
        object="str",
        raw_statement="Text object converts to string representation containing its plain text via str()."
    )

    test_str_src = '''
def test_str():
    assert str(Text("foo")) == "foo"
'''

    test_divide_src = '''
def test_divide():
    text = Text("Hello World")
    t1, t2 = text.divide([5])
    assert len(t1) == 5
    assert len(t2) == 6
    assert t1.plain == "Hello"
    assert t2.plain == " World"
    # mentions Text multiple times
    t3 = Text("Another Text")
    t4, t5 = t3.divide([7])
    assert len(t4) == 7
'''

    analyzer = WitnessBindingAnalyzer()
    cand_str = TestCandidate(
        test_file="tests/test_text.py",
        test_name="test_str",
        subject_mentions=1,
        object_mentions=2,
        dependency_mentions=0,
        assertion_count=1,
        target_commit="commit1",
        source_hash="hash1",
        binding_strength=BindingStrength.UNBOUND,
        discovery_reason="test_str",
        test_source=test_str_src
    )
    cand_divide = TestCandidate(
        test_file="tests/test_text.py",
        test_name="test_divide",
        subject_mentions=10,
        object_mentions=0,
        dependency_mentions=0,
        assertion_count=6,
        target_commit="commit1",
        source_hash="hash2",
        binding_strength=BindingStrength.UNBOUND,
        discovery_reason="test_divide",
        test_source=test_divide_src
    )

    res_str = analyzer.analyze_witness(claim=claim, candidate=cand_str)
    res_divide = analyzer.analyze_witness(claim=claim, candidate=cand_divide)

    assert res_str.binding_strength == BindingStrength.STRONG
    assert res_str.subject_binding is True
    assert res_str.operation_binding is True
    assert res_str.assertion_binding is True
    assert res_str.dataflow_binding is True
    assert res_str.critical_operation_coverage_ratio == 1.0

    # test_divide has no str() assertion with dataflow from Text
    assert res_divide.binding_strength in (BindingStrength.WEAK, BindingStrength.UNBOUND)
    assert res_divide.critical_operation_coverage_ratio == 0.0

    # Test ranking: test_str must be ranked higher than test_divide
    binder = ClaimTestBinder()
    ranked = binder.bind_and_rank_candidates(claim, [cand_divide, cand_str])
    assert ranked[0].test_name == "test_str"
    assert ranked[0].binding_strength == BindingStrength.STRONG


def test_clm_000037_multi_operation_critical_chain():
    """
    CLM-000037: HelpFormatter write_text() + getvalue()
    Requires both write_text and getvalue in the witness.
    """
    claim = MemoryClaim(
        claim_id="CLM-000037",
        claim_type=ClaimType.BEHAVIORAL_CONTRACT,
        subject="HelpFormatter",
        predicate="satisfies_contract",
        object=", text buffered with write_text() can be retrieved via getvalue().",
        raw_statement="When HelpFormatter is initialized, text buffered with write_text() can be retrieved via getvalue()."
    )

    complete_witness = '''
def test_help_formatter_write_text():
    formatter = HelpFormatter()
    formatter.write_text("Hello World")
    result = formatter.getvalue()
    assert result == "Hello World"
'''

    incomplete_witness = '''
def test_help_formatter_only_write():
    formatter = HelpFormatter()
    formatter.write_text("Hello World")
    assert formatter is not None
'''

    analyzer = WitnessBindingAnalyzer()
    cand_comp = TestCandidate(
        test_file="tests/test_formatting.py",
        test_name="test_help_formatter_write_text",
        subject_mentions=1,
        object_mentions=1,
        dependency_mentions=0,
        assertion_count=1,
        target_commit="commit1",
        source_hash="hash1",
        binding_strength=BindingStrength.UNBOUND,
        discovery_reason="",
        test_source=complete_witness
    )
    cand_incomp = TestCandidate(
        test_file="tests/test_formatting.py",
        test_name="test_help_formatter_only_write",
        subject_mentions=1,
        object_mentions=1,
        dependency_mentions=0,
        assertion_count=1,
        target_commit="commit1",
        source_hash="hash2",
        binding_strength=BindingStrength.UNBOUND,
        discovery_reason="",
        test_source=incomplete_witness
    )

    res_complete = analyzer.analyze_witness(claim=claim, candidate=cand_comp)
    res_incomplete = analyzer.analyze_witness(claim=claim, candidate=cand_incomp)

    assert res_complete.binding_strength == BindingStrength.STRONG
    assert res_complete.critical_operation_coverage_ratio == 1.0
    assert res_incomplete.critical_operation_coverage_ratio < 1.0


def test_clm_000040_console_export_text():
    """
    CLM-000040: Console print() and export_text(record=True)
    """
    claim = MemoryClaim(
        claim_id="CLM-000040",
        claim_type=ClaimType.BEHAVIORAL_CONTRACT,
        subject="Console",
        predicate="exports_text",
        object="export_text",
        raw_statement="Console exports plain text of printed content via export_text when record=True."
    )

    test_src = '''
def test_export_text():
    console = Console(record=True)
    console.print("foo")
    assert console.export_text() == "foo\\n"
'''

    analyzer = WitnessBindingAnalyzer()
    cand = TestCandidate(
        test_file="tests/test_console.py",
        test_name="test_export_text",
        subject_mentions=1,
        object_mentions=1,
        dependency_mentions=0,
        assertion_count=1,
        target_commit="commit1",
        source_hash="hash1",
        binding_strength=BindingStrength.UNBOUND,
        discovery_reason="",
        test_source=test_src
    )

    res = analyzer.analyze_witness(claim=claim, candidate=cand)
    assert res.binding_strength == BindingStrength.STRONG
    assert res.dataflow_binding is True
    assert res.assertion_binding is True


def test_generic_builtin_deweighting():
    """
    Generic tokens ('len', 'str', 'get') without dataflow to subject must not be marked STRONG.
    """
    claim = MemoryClaim(
        claim_id="CLM-TEST-GENERIC",
        claim_type=ClaimType.BEHAVIORAL_CONTRACT,
        subject="MySpecialObject",
        predicate="has_len",
        object="len",
        raw_statement="MySpecialObject supports len()."
    )

    # test has len() of a generic list, not MySpecialObject
    unrelated_src = '''
def test_unrelated():
    obj = MySpecialObject()
    other_list = [1, 2, 3]
    assert len(other_list) == 3
'''

    analyzer = WitnessBindingAnalyzer()
    cand = TestCandidate(
        test_file="tests/test_misc.py",
        test_name="test_unrelated",
        subject_mentions=1,
        object_mentions=1,
        dependency_mentions=0,
        assertion_count=1,
        target_commit="commit1",
        source_hash="hash1",
        binding_strength=BindingStrength.UNBOUND,
        discovery_reason="",
        test_source=unrelated_src
    )

    res = analyzer.analyze_witness(claim=claim, candidate=cand)
    assert res.binding_strength != BindingStrength.STRONG


def test_clm_000044_regression():
    """
    CLM-000044 Regression Test:
    Statement: "PoolManager initializes connection pools with default configuration when no arguments provided."
    Subject: "PoolManager"
    Requirements:
      - CONSTRUCTOR_ARGUMENT (0 arguments / no arguments)
      - DEFAULT_VALUE / ATTRIBUTE_STATE (default configuration)
    Candidate test_poolmanager_blocksize passes custom blocksize=10, satisfying constructor arg count
    but failing default configuration semantics. Must be WEAK, not STRONG.
    """
    claim = MemoryClaim(
        claim_id="CLM-000044",
        claim_type=ClaimType.BEHAVIORAL_CONTRACT,
        subject="PoolManager",
        predicate="initializes_with_default",
        object="default configuration",
        raw_statement="PoolManager initializes connection pools with default configuration when no arguments provided."
    )

    test_src = '''
def test_poolmanager_blocksize():
    p = PoolManager(blocksize=10)
    assert p.connection_pools is not None
'''

    analyzer = WitnessBindingAnalyzer()
    cand = TestCandidate(
        test_file="test/test_poolmanager.py",
        test_name="test_poolmanager_blocksize",
        subject_mentions=1,
        object_mentions=0,
        dependency_mentions=0,
        assertion_count=1,
        target_commit="commit1",
        source_hash="hash1",
        binding_strength=BindingStrength.UNBOUND,
        discovery_reason="",
        test_source=test_src
    )

    res = analyzer.analyze_witness(claim=claim, candidate=cand)
    assert res.binding_strength == BindingStrength.WEAK
    assert res.binding_strength != BindingStrength.STRONG


def test_state_default_contract():
    """
    State/default contract test:
    FastAPI() initialized with default title="FastAPI".
    Candidate A asserts app.title == "FastAPI" -> STRONG
    Candidate B only asserts app.routes is not None -> WEAK
    """
    claim = MemoryClaim(
        claim_id="CLM-TEST-DEFAULT-ATTR",
        claim_type=ClaimType.BEHAVIORAL_CONTRACT,
        subject="FastAPI",
        predicate="has_default_attribute",
        object="title='FastAPI'",
        raw_statement="FastAPI initializes with default title 'FastAPI' when instantiated without parameters."
    )

    strong_src = '''
def test_fastapi_default_title():
    app = FastAPI()
    assert app.title == "FastAPI"
'''

    weak_src = '''
def test_fastapi_routes():
    app = FastAPI()
    assert app.routes is not None
'''

    analyzer = WitnessBindingAnalyzer()
    cand_strong = TestCandidate(
        test_file="tests/test_main.py",
        test_name="test_fastapi_default_title",
        subject_mentions=1,
        object_mentions=1,
        dependency_mentions=0,
        assertion_count=1,
        target_commit="commit1",
        source_hash="hash1",
        binding_strength=BindingStrength.UNBOUND,
        discovery_reason="",
        test_source=strong_src
    )

    cand_weak = TestCandidate(
        test_file="tests/test_main.py",
        test_name="test_fastapi_routes",
        subject_mentions=1,
        object_mentions=0,
        dependency_mentions=0,
        assertion_count=1,
        target_commit="commit1",
        source_hash="hash2",
        binding_strength=BindingStrength.UNBOUND,
        discovery_reason="",
        test_source=weak_src
    )

    res_strong = analyzer.analyze_witness(claim=claim, candidate=cand_strong)
    res_weak = analyzer.analyze_witness(claim=claim, candidate=cand_weak)

    assert res_strong.binding_strength == BindingStrength.STRONG
    assert res_weak.binding_strength != BindingStrength.STRONG


def test_sequence_reversed():
    """
    Negative test for SEQUENCE requirement:
    When HelpFormatter is initialized, write_text() must precede getvalue().
    Reversing the order causes SEQUENCE requirement to fail -> WEAK binding.
    """
    claim = MemoryClaim(
        claim_id="CLM-000037",
        claim_type=ClaimType.BEHAVIORAL_CONTRACT,
        subject="HelpFormatter",
        predicate="satisfies_contract",
        object=", text buffered with write_text() can be retrieved via getvalue().",
        raw_statement="When HelpFormatter is initialized, text buffered with write_text() can be retrieved via getvalue()."
    )

    reversed_order_src = '''
def test_help_formatter_reversed():
    formatter = HelpFormatter()
    result = formatter.getvalue()
    formatter.write_text("Hello World")
    assert result == "Hello World"
'''
    analyzer = WitnessBindingAnalyzer()
    cand = TestCandidate(
        test_file="tests/test_formatting.py",
        test_name="test_help_formatter_reversed",
        subject_mentions=1,
        object_mentions=1,
        dependency_mentions=0,
        assertion_count=1,
        target_commit="commit1",
        source_hash="hash_rev",
        binding_strength=BindingStrength.UNBOUND,
        discovery_reason="",
        test_source=reversed_order_src
    )

    res = analyzer.analyze_witness(claim=claim, candidate=cand)
    assert res.binding_strength in (BindingStrength.WEAK, BindingStrength.UNBOUND)
    assert res.binding_strength != BindingStrength.STRONG


def test_return_relation_wrong_output():
    """
    Negative test for RETURN_RELATION requirement:
    Text instance initialized with a string returns the plain string content when converted via str().
    Constructor input is "foo", assertion expects "bar" -> unsatisfied -> WEAK binding.
    """
    claim = MemoryClaim(
        claim_id="CLM-000041",
        claim_type=ClaimType.BEHAVIORAL_CONTRACT,
        subject="Text",
        predicate="satisfies_contract",
        object="with a string returns the plain string content when converted via str().",
        raw_statement="Text instance initialized with a string returns the plain string content when converted via str()."
    )

    wrong_output_src = '''
def test_wrong_output():
    assert str(Text("foo")) == "bar"
'''
    analyzer = WitnessBindingAnalyzer()
    cand = TestCandidate(
        test_file="tests/test_text.py",
        test_name="test_wrong_output",
        subject_mentions=1,
        object_mentions=1,
        dependency_mentions=0,
        assertion_count=1,
        target_commit="commit1",
        source_hash="hash_wrong_out",
        binding_strength=BindingStrength.UNBOUND,
        discovery_reason="",
        test_source=wrong_output_src
    )

    res = analyzer.analyze_witness(claim=claim, candidate=cand)
    assert res.binding_strength in (BindingStrength.WEAK, BindingStrength.UNBOUND)
    assert res.binding_strength != BindingStrength.STRONG


def test_constructor_wrong_input_shape():
    """
    Negative test for CONSTRUCTOR_ARGUMENT requirement:
    Text instance initialized with a string returns the plain string content when converted via str().
    Requires STRING input in constructor, but 123 (integer) is passed -> unsatisfied -> WEAK binding.
    """
    claim = MemoryClaim(
        claim_id="CLM-000041",
        claim_type=ClaimType.BEHAVIORAL_CONTRACT,
        subject="Text",
        predicate="satisfies_contract",
        object="with a string returns the plain string content when converted via str().",
        raw_statement="Text instance initialized with a string returns the plain string content when converted via str()."
    )

    wrong_shape_src = '''
def test_wrong_constructor_arg():
    assert str(Text(123)) == "123"
'''
    analyzer = WitnessBindingAnalyzer()
    cand = TestCandidate(
        test_file="tests/test_text.py",
        test_name="test_wrong_constructor_arg",
        subject_mentions=1,
        object_mentions=1,
        dependency_mentions=0,
        assertion_count=1,
        target_commit="commit1",
        source_hash="hash_wrong_shape",
        binding_strength=BindingStrength.UNBOUND,
        discovery_reason="",
        test_source=wrong_shape_src
    )

    res = analyzer.analyze_witness(claim=claim, candidate=cand)
    assert res.binding_strength in (BindingStrength.WEAK, BindingStrength.UNBOUND)
    assert res.binding_strength != BindingStrength.STRONG


def test_attribute_state_wrong_value():
    """
    Negative test for ATTRIBUTE_STATE requirement:
    FastAPI initializes with default title 'FastAPI'.
    Assertion checks app.title == 'WrongTitle' -> unsatisfied -> WEAK binding.
    """
    claim = MemoryClaim(
        claim_id="CLM-TEST-DEFAULT-ATTR",
        claim_type=ClaimType.BEHAVIORAL_CONTRACT,
        subject="FastAPI",
        predicate="satisfies_contract",
        object="with default title attribute set to 'FastAPI'.",
        raw_statement="FastAPI application instance initializes with default title attribute set to 'FastAPI'."
    )

    wrong_val_src = '''
def test_wrong_attr_value():
    app = FastAPI()
    assert app.title == "WrongTitle"
'''
    analyzer = WitnessBindingAnalyzer()
    cand = TestCandidate(
        test_file="tests/test_main.py",
        test_name="test_wrong_attr_value",
        subject_mentions=1,
        object_mentions=1,
        dependency_mentions=0,
        assertion_count=1,
        target_commit="commit1",
        source_hash="hash_wrong_val",
        binding_strength=BindingStrength.UNBOUND,
        discovery_reason="",
        test_source=wrong_val_src
    )

    res = analyzer.analyze_witness(claim=claim, candidate=cand)
    assert res.binding_strength in (BindingStrength.WEAK, BindingStrength.UNBOUND)
    assert res.binding_strength != BindingStrength.STRONG


def test_default_value_explicitly_passed():
    """
    Negative test for DEFAULT_VALUE requirement:
    Starlette application has debug disabled by default.
    Candidate explicitly passes debug=False in constructor -> DEFAULT_VALUE unsatisfied -> WEAK binding.
    """
    claim = MemoryClaim(
        claim_id="CLM-TEST-STARLETTE-DEFAULT",
        claim_type=ClaimType.BEHAVIORAL_CONTRACT,
        subject="Starlette",
        predicate="satisfies_contract",
        object="with default debug mode set to False.",
        raw_statement="Starlette application instance initializes with default debug mode set to False."
    )

    explicit_src = '''
def test_explicit_debug():
    app = Starlette(debug=False)
    assert app.debug is False
'''
    default_src = '''
def test_default_debug():
    app = Starlette()
    assert app.debug is False
'''
    analyzer = WitnessBindingAnalyzer()
    cand_explicit = TestCandidate(
        test_file="tests/test_app.py",
        test_name="test_explicit_debug",
        subject_mentions=1,
        object_mentions=1,
        dependency_mentions=0,
        assertion_count=1,
        target_commit="commit1",
        source_hash="hash_explicit",
        binding_strength=BindingStrength.UNBOUND,
        discovery_reason="",
        test_source=explicit_src
    )
    cand_default = TestCandidate(
        test_file="tests/test_app.py",
        test_name="test_default_debug",
        subject_mentions=1,
        object_mentions=1,
        dependency_mentions=0,
        assertion_count=1,
        target_commit="commit1",
        source_hash="hash_default",
        binding_strength=BindingStrength.UNBOUND,
        discovery_reason="",
        test_source=default_src
    )

    res_explicit = analyzer.analyze_witness(claim=claim, candidate=cand_explicit)
    res_default = analyzer.analyze_witness(claim=claim, candidate=cand_default)

    assert res_explicit.binding_strength in (BindingStrength.WEAK, BindingStrength.UNBOUND)
    assert res_explicit.binding_strength != BindingStrength.STRONG
    assert res_default.binding_strength == BindingStrength.STRONG


def test_unrelated_literal_in_assert():
    """
    Negative test: unrelated literal match in assertion does not bind attribute state.
    """
    claim = MemoryClaim(
        claim_id="CLM-TEST-DEFAULT-ATTR",
        claim_type=ClaimType.BEHAVIORAL_CONTRACT,
        subject="FastAPI",
        predicate="has_default_attribute",
        object="title='FastAPI'",
        raw_statement="FastAPI initializes with default title 'FastAPI' when instantiated without parameters."
    )

    unrelated_src = '''
def test_unrelated():
    app = FastAPI()
    label = "FastAPI"
    assert app.debug is True or label == "FastAPI"
'''
    analyzer = WitnessBindingAnalyzer()
    cand = TestCandidate(
        test_file="tests/test_main.py",
        test_name="test_unrelated",
        subject_mentions=1,
        object_mentions=1,
        dependency_mentions=0,
        assertion_count=1,
        target_commit="commit1",
        source_hash="hash_unrelated",
        binding_strength=BindingStrength.UNBOUND,
        discovery_reason="",
        test_source=unrelated_src
    )

    res = analyzer.analyze_witness(claim=claim, candidate=cand)
    assert res.binding_strength in (BindingStrength.WEAK, BindingStrength.UNBOUND)
    assert res.binding_strength != BindingStrength.STRONG


