"""
src/evidence_escalation/test_binding.py

Claim-Test Binding Engine for Protocol V2.2-V1 Evidence Escalation:
- Analyzes candidate test ASTs against claim subjects, predicate semantics, and object operation tokens.
- Determines binding strength (STRONG, WEAK, UNBOUND) with transparent scoring rationale.
- Strongly-bound tests can subsequently undergo targeted execution to produce deterministic VALID/STALE evidence.
"""

from __future__ import annotations
import re
import ast
from typing import Dict, Any, List, Optional, Set, Tuple

from src.claim_validity.types import MemoryClaim, ClaimType
from .types import BindingStrength, TestCandidate


class ClaimTestBinder:
    """Evaluates semantic binding between MemoryClaim and TestCandidate."""

    def __init__(self):
        pass

    @staticmethod
    def extract_operation_tokens(claim: MemoryClaim) -> List[str]:
        """Extracts recognizable method names, attribute names, and identifier tokens from claim object and raw statement."""
        tokens = set()
        text = f"{claim.object} {claim.raw_statement}"

        # 1. Match tokens followed by () e.g. write_text(), getvalue(), export_text(), len()
        fn_matches = re.findall(r"([a-zA-Z_][a-zA-Z0-9_]*)\s*\(\)", text)
        for m in fn_matches:
            if len(m) > 1:
                tokens.add(m)

        # 2. Match backtick or quoted tokens e.g. `title`, 'FastAPI', `record=True`
        quote_matches = re.findall(r"[`'\"]([a-zA-Z_][a-zA-Z0-9_]*)['`\"]", text)
        for q in quote_matches:
            if len(q) > 1:
                tokens.add(q)

        # 3. Match attribute references e.g. "method attribute", "title attribute", "debug mode"
        attr_matches = re.findall(r"([a-zA-Z_][a-zA-Z0-9_]*)\s+(?:attribute|mode|property|parameter)", text, re.IGNORECASE)
        for a in attr_matches:
            if len(a) > 1:
                tokens.add(a)

        # 4. Filter out common English stopwords
        stopwords = {"the", "and", "via", "with", "for", "set", "can", "when", "with", "from", "that", "this"}
        tokens = {t for t in tokens if t.lower() not in stopwords}

        return sorted(list(tokens))

    def evaluate_binding(
        self,
        claim: MemoryClaim,
        candidate: TestCandidate,
        dependency_symbol: Optional[str] = None
    ) -> TestCandidate:
        """
        Evaluates and assigns binding strength for candidate against claim.
        """
        subject = claim.subject.split(".")[-1] if claim.subject else ""
        op_tokens = self.extract_operation_tokens(claim)
        obj_toks_set = set(t.lower() for t in op_tokens if len(t) > 1)
        test_src = candidate.test_source or ""

        # Parse AST of test_src to count code references (ignoring docstrings)
        subj_matches = 0
        dep_matches = 0
        matched_op_tokens = []
        try:
            tree = ast.parse(test_src)
            for inner in ast.walk(tree):
                if isinstance(inner, ast.Expr) and isinstance(inner.value, ast.Constant) and isinstance(inner.value.value, str):
                    continue
                if isinstance(inner, ast.Name):
                    if subject and inner.id == subject:
                        subj_matches += 1
                    if dependency_symbol and inner.id == dependency_symbol.split(".")[-1]:
                        dep_matches += 1
                    if inner.id.lower() in obj_toks_set:
                        matched_op_tokens.append(inner.id)
                elif isinstance(inner, ast.Attribute):
                    if subject and inner.attr == subject:
                        subj_matches += 1
                    if dependency_symbol and inner.attr == dependency_symbol.split(".")[-1]:
                        dep_matches += 1
                    if inner.attr.lower() in obj_toks_set:
                        matched_op_tokens.append(inner.attr)
                elif isinstance(inner, ast.Call):
                    if isinstance(inner.func, ast.Name) and inner.func.id.lower() in obj_toks_set:
                        matched_op_tokens.append(inner.func.id)
        except Exception:
            # Fallback to regex if test_src snippet cannot be parsed standalone
            if subject:
                subj_matches = len(re.findall(rf"\b{re.escape(subject)}\b", test_src))
            if dependency_symbol:
                dep_matches = len(re.findall(rf"\b{re.escape(dependency_symbol.split('.')[-1])}\b", test_src))
            for tok in op_tokens:
                if re.search(rf"\b{re.escape(tok)}\b", test_src, re.IGNORECASE):
                    matched_op_tokens.append(tok)

        candidate.subject_mentions = subj_matches
        candidate.dependency_mentions = dep_matches
        candidate.object_mentions = len(set(matched_op_tokens))

        # Determine binding strength
        if claim.claim_type == ClaimType.DEPENDENCY_CONTRACT:
            if subj_matches >= 1 and dep_matches >= 1 and candidate.assertion_count >= 1:
                candidate.binding_strength = BindingStrength.STRONG
                candidate.discovery_reason = (
                    f"Strong dependency binding: '{subject}' and '{dependency_symbol}' both referenced "
                    f"with {candidate.assertion_count} assertions in {candidate.test_file}:{candidate.test_name}"
                )
            elif subj_matches >= 1 or dep_matches >= 1:
                candidate.binding_strength = BindingStrength.WEAK
                candidate.discovery_reason = f"Weak dependency binding: partial symbol overlap in {candidate.test_file}:{candidate.test_name}"
            else:
                candidate.binding_strength = BindingStrength.UNBOUND

        elif claim.claim_type == ClaimType.BEHAVIORAL_CONTRACT:
            # Behavioral contract binding requires subject AND (at least one operation token or specific test name match)
            test_name_matches_subject = subject.lower() in candidate.test_name.lower()
            has_matching_op = len(matched_op_tokens) >= 1

            if subj_matches >= 1 and (has_matching_op or test_name_matches_subject) and candidate.assertion_count >= 1:
                candidate.binding_strength = BindingStrength.STRONG
                candidate.discovery_reason = (
                    f"Strong behavioral binding: '{subject}' instantiated/referenced with operation tokens "
                    f"{matched_op_tokens} and {candidate.assertion_count} assertions in {candidate.test_file}:{candidate.test_name}"
                )
            elif subj_matches >= 1:
                candidate.binding_strength = BindingStrength.WEAK
                candidate.discovery_reason = (
                    f"Weak behavioral binding: '{subject}' mentioned without direct claim operation verification in "
                    f"{candidate.test_file}:{candidate.test_name}"
                )
            else:
                candidate.binding_strength = BindingStrength.UNBOUND
        else:
            # General symbol / attribute claims
            if subj_matches >= 1 and candidate.assertion_count >= 1:
                candidate.binding_strength = BindingStrength.STRONG
                candidate.discovery_reason = f"Strong symbol binding for '{subject}' with {candidate.assertion_count} assertions"
            elif subj_matches >= 1:
                candidate.binding_strength = BindingStrength.WEAK
            else:
                candidate.binding_strength = BindingStrength.UNBOUND

        return candidate

    def bind_and_rank_candidates(
        self,
        claim: MemoryClaim,
        candidates: List[TestCandidate],
        dependency_symbol: Optional[str] = None
    ) -> List[TestCandidate]:
        """Binds and ranks test candidates in descending order of relevance."""
        evaluated = [
            self.evaluate_binding(claim, c, dependency_symbol=dependency_symbol)
            for c in candidates
        ]

        # Ranking key: STRONG > WEAK > UNBOUND, then object mentions, then assertions
        def sort_key(c: TestCandidate) -> Tuple[int, int, int]:
            s_val = 2 if c.binding_strength == BindingStrength.STRONG else (1 if c.binding_strength == BindingStrength.WEAK else 0)
            return (s_val, c.object_mentions, c.assertion_count)

        return sorted(evaluated, key=sort_key, reverse=True)
