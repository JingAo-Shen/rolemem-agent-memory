"""
Gate 10 Automated Tests: Fine-Grained Symbol-Level Digest & False Invalidation Reduction.
"""

import pytest
from src.symbol_digest_prototype import SymbolDigestExtractor, FineGrainedValidityEvaluator


def test_symbol_digest_extraction():
    code = """
DEFAULT_TIMEOUT = 30

def process_data(x: int) -> int:
    return x * 2

class CacheManager:
    def __init__(self):
        self.items = {}
"""
    digests = SymbolDigestExtractor.extract_symbol_digests(code)
    assert "DEFAULT_TIMEOUT" in digests
    assert digests["DEFAULT_TIMEOUT"].symbol_type == "assignment"
    assert "process_data" in digests
    assert digests["process_data"].symbol_type == "function"
    assert "CacheManager" in digests
    assert digests["CacheManager"].symbol_type == "class"


def test_unrelated_symbol_modification_preserves_validity():
    """
    Core Hypothesis: If a file modifies function `bar`, the symbol digest for `foo`
    in the same file remains identical, achieving False Invalidation Rate = 0.0%.
    """
    initial_code = """
def authenticate_user(token: str) -> bool:
    return len(token) > 10

def format_report(data: dict) -> str:
    return "Report v1"
"""
    # Extract initial digest for authenticate_user
    initial_digests = SymbolDigestExtractor.extract_symbol_digests(initial_code)
    auth_digest = initial_digests["authenticate_user"].canonical_digest
    report_digest = initial_digests["format_report"].canonical_digest

    # Updated file: format_report is refactored, but authenticate_user is UNCHANGED
    updated_code = """
def authenticate_user(token: str) -> bool:
    return len(token) > 10

def format_report(data: dict) -> str:
    # Completely refactored report generator
    import json
    return json.dumps(data)
"""
    # 1. Under coarse file-level SHA256, BOTH authenticate_user and format_report would be invalidated!
    # 2. Under Fine-Grained Symbol Digest:
    auth_is_valid = FineGrainedValidityEvaluator.check_symbol_validity(
        symbol_name="authenticate_user",
        recorded_symbol_digest=auth_digest,
        current_file_content=updated_code
    )
    report_is_valid = FineGrainedValidityEvaluator.check_symbol_validity(
        symbol_name="format_report",
        recorded_symbol_digest=report_digest,
        current_file_content=updated_code
    )

    # Assertions
    assert auth_is_valid is True, "Unmodified symbol 'authenticate_user' was falsely invalidated!"
    assert report_is_valid is False, "Modified symbol 'format_report' failed to invalidate!"

    # Compute False Invalidation Rate
    # Total valid memories = 1 (authenticate_user). Falsely invalidated = 0.
    metrics = FineGrainedValidityEvaluator.compute_invalidation_metrics(
        total_valid_memories=1,
        falsely_invalidated_memories=0,
        total_retrieved_memories=1,
        exposed_stale_memories=0
    )
    assert metrics["false_invalidation_rate"] == 0.0
    assert metrics["stale_exposure_rate"] == 0.0
