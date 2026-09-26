"""
src/baselines/majority.py

Baseline-1: Majority Predictor
Always predicts the majority class (VALID) for all incoming claims.
Serves as zero-intelligence prevalence ceiling baseline.
"""

from __future__ import annotations
from typing import Dict, Any, Optional
import time


class MajorityBaselinePredictor:
    """Majority class heuristic baseline."""

    def __init__(self, majority_label: str = "VALID", confidence: float = 0.8333):
        self.majority_label = majority_label
        self.confidence = confidence

    def predict(
        self,
        case_input: Dict[str, Any],
        case_meta: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Produce majority prediction."""
        start_time = time.time()
        case_id = case_input.get("case_id", "UNKNOWN")
        wall_time = time.time() - start_time

        return {
            "case_id": case_id,
            "predicted_label": self.majority_label,
            "confidence": self.confidence,
            "escalation_tier": "TIER_0_STATIC_AST",
            "action_count": 0,
            "execution_wall_time_sec": round(wall_time, 6)
        }
