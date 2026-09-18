import os
import pytest
from src.historical_memory_writer import HistoricalMemoryWriter

def test_base_state_evidence_extraction():
    # Test on local git repository (click)
    repo_path = "/code/repo_cache/click"
    base_commit = "333c28d79cd982990ee98eef61ec20ab1a4f38ba"
    target_file = "src/click/testing.py"
    symbol = "isolated_filesystem"

    writer = HistoricalMemoryWriter.__new__(HistoricalMemoryWriter)
    evidence = writer.get_base_state_evidence(repo_path, base_commit, target_file, symbol)
    assert evidence["base_commit"] == base_commit
    assert evidence["target_file"] == target_file
    assert "isolated_filesystem" in evidence["code_context"]
    assert len(evidence["artifact_digest"]) == 64
