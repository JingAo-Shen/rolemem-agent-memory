"""
src/evidence_escalation/test_binding.py

Claim-Test Binding Engine for Protocol V2.2-V1.1 Evidence Escalation:
- Bridges TestCandidate ranking and evaluation with WitnessBindingAnalyzer.
- Determines binding strength (STRONG, WEAK, UNBOUND) with AST dataflow witness graphs.
"""

from __future__ import annotations
from typing import Dict, Any, List, Optional, Set, Tuple

from src.claim_validity.types import MemoryClaim, ClaimType
from .types import BindingStrength, TestCandidate
from .witness_binding import WitnessBindingAnalyzer, ClaimWitnessBinding


class ClaimTestBinder:
    """Evaluates semantic witness binding between MemoryClaim and TestCandidate."""

    def __init__(self):
        self.analyzer = WitnessBindingAnalyzer()

    @staticmethod
    def extract_operation_tokens(claim: MemoryClaim) -> List[str]:
        return WitnessBindingAnalyzer.extract_critical_operations(claim)

    def evaluate_binding(
        self,
        claim: MemoryClaim,
        candidate: TestCandidate,
        dependency_symbol: Optional[str] = None
    ) -> TestCandidate:
        """Evaluates and assigns binding strength for candidate against claim."""
        witness = self.analyzer.analyze_witness(claim, candidate, dependency_symbol=dependency_symbol)
        candidate.witness_binding = witness.to_dict()
        candidate.binding_strength = witness.binding_strength
        candidate.discovery_reason = "; ".join(witness.binding_reasons)
        return candidate

    def bind_and_rank_candidates(
        self,
        claim: MemoryClaim,
        candidates: List[TestCandidate],
        dependency_symbol: Optional[str] = None
    ) -> List[TestCandidate]:
        """Binds and ranks test candidates in descending order of genuine witness relevance."""
        return self.analyzer.rank_candidates(claim, candidates, dependency_symbol=dependency_symbol)
