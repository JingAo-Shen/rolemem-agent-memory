"""
src/baselines/__init__.py

Baseline models for RoleMem Temporal Consistency Benchmark:
- MajorityBaselinePredictor
- StaticASTBaselinePredictor
- NaiveRAGBaselinePredictor
"""

from .majority import MajorityBaselinePredictor
from .static_ast import StaticASTBaselinePredictor
from .naive_rag import NaiveRAGBaselinePredictor

__all__ = [
    "MajorityBaselinePredictor",
    "StaticASTBaselinePredictor",
    "NaiveRAGBaselinePredictor",
]
