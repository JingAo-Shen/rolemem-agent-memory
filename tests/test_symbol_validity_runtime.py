import pytest
import hashlib
from src.schema_v1 import MemoryRecordV1
from src.rolemem_core_v1 import RoleMemStoreV1
from src.symbol_validity import SymbolDigestExtractor


def test_symbol_unchanged_file_changed_preserved_in_symbol_mode():
    base_code = """def target_function(x):
    return x * 2

def other_function():
    return 1
"""
    target_code = """def target_function(x):
    return x * 2

def other_function():
    # Modified other function
    return 999
"""
    
    base_file_sha = hashlib.sha256(base_code.encode("utf-8")).hexdigest()
    b_digs = SymbolDigestExtractor.extract_symbol_digests(base_code)
    target_sym_dig = b_digs["target_function"]["symbol_digest"]

    store = RoleMemStoreV1()
    rec = MemoryRecordV1(
        memory_id="m1",
        artifact_uri="helper.py",
        artifact_type="symbol",
        symbol="target_function",
        symbol_qualified_name="target_function",
        symbol_digest=target_sym_dig,
        validity_granularity="symbol",
        source_commit="commit1",
        observed_at=10.0,
        evidence_type="diff",
        evidence_ref="pr",
        valid_from=10.0,
        statement="target_function doubles the input.",
        artifact_digest=base_file_sha
    )
    store.add_record(rec)

    # 1. File mode: should be invalidated because whole file changed
    retrieved_file = store.retrieve(
        query="doubles the input",
        role="coder",
        current_time=20.0,
        workspace_files={"helper.py": target_code},
        validity_mode="file"
    )
    assert len(retrieved_file) == 0

    # Reset status for symbol mode test
    rec.status = "ACTIVE"
    # 2. Symbol mode: should remain ACTIVE because target_function is unchanged
    retrieved_sym = store.retrieve(
        query="doubles the input",
        role="coder",
        current_time=20.0,
        workspace_files={"helper.py": target_code},
        validity_mode="symbol"
    )
    assert len(retrieved_sym) == 1
    assert retrieved_sym[0].memory_id == "m1"


def test_symbol_modified_invalidated_in_symbol_mode():
    base_code = """def target_function(x):
    return x * 2
"""
    target_code = """def target_function(x):
    # Signature modified
    return x * 3
"""
    base_file_sha = hashlib.sha256(base_code.encode("utf-8")).hexdigest()
    b_digs = SymbolDigestExtractor.extract_symbol_digests(base_code)
    target_sym_dig = b_digs["target_function"]["symbol_digest"]

    store = RoleMemStoreV1()
    rec = MemoryRecordV1(
        memory_id="m2",
        artifact_uri="helper.py",
        artifact_type="symbol",
        symbol="target_function",
        symbol_qualified_name="target_function",
        symbol_digest=target_sym_dig,
        validity_granularity="symbol",
        source_commit="commit1",
        observed_at=10.0,
        evidence_type="diff",
        evidence_ref="pr",
        valid_from=10.0,
        statement="target_function doubles input",
        artifact_digest=base_file_sha
    )
    store.add_record(rec)

    retrieved = store.retrieve(
        query="target_function",
        role="coder",
        current_time=20.0,
        workspace_files={"helper.py": target_code},
        validity_mode="symbol"
    )
    assert len(retrieved) == 0


def test_symbol_removed_invalidated_in_symbol_mode():
    base_code = """def target_function(x):
    return x * 2
"""
    target_code = """def completely_new_function():
    return 42
"""
    base_file_sha = hashlib.sha256(base_code.encode("utf-8")).hexdigest()
    b_digs = SymbolDigestExtractor.extract_symbol_digests(base_code)
    target_sym_dig = b_digs["target_function"]["symbol_digest"]

    store = RoleMemStoreV1()
    rec = MemoryRecordV1(
        memory_id="m3",
        artifact_uri="helper.py",
        artifact_type="symbol",
        symbol="target_function",
        symbol_qualified_name="target_function",
        symbol_digest=target_sym_dig,
        validity_granularity="symbol",
        source_commit="commit1",
        observed_at=10.0,
        evidence_type="diff",
        evidence_ref="pr",
        valid_from=10.0,
        statement="target_function doubles input",
        artifact_digest=base_file_sha
    )
    store.add_record(rec)

    retrieved = store.retrieve(
        query="target_function",
        role="coder",
        current_time=20.0,
        workspace_files={"helper.py": target_code},
        validity_mode="symbol"
    )
    assert len(retrieved) == 0
