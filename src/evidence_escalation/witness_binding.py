"""
src/evidence_escalation/witness_binding.py

Claim Witness Binding & AST Dataflow Analysis Engine for Protocol V2.2-V1.1:
- Builds AST witness graphs for candidate test functions:
  Subject Construction -> Variable Propagation -> Operation Call -> Result -> Assertion.
- Evaluates strict subject binding, operation binding, assertion binding, and dataflow connectivity.
- Enforces critical operation coverage (e.g. write_text AND getvalue).
- De-weights generic built-in operations (str, len, print, etc.) unless proven to receive direct subject dataflow.
- Ranks candidate tests by genuine witness strength rather than raw keyword counts.
"""

from __future__ import annotations
import re
import ast
import hashlib
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional, Set, Tuple

from src.claim_validity.types import MemoryClaim, ClaimType
from .types import BindingStrength, TestCandidate

GENERIC_BUILTIN_OPS = {"str", "len", "print", "get", "set", "list", "dict", "bool", "repr", "int", "float"}


@dataclass
class ClaimWitnessBinding:
    claim_id: str
    subject: str
    operation_tokens: List[str]
    expected_literals: List[str] = field(default_factory=list)
    expected_attributes: List[str] = field(default_factory=list)
    test_file: str = ""
    test_name: str = ""
    test_function_sha256: str = ""
    subject_binding: bool = False
    operation_binding: bool = False
    assertion_binding: bool = False
    dataflow_binding: bool = False
    critical_operation_coverage_ratio: float = 0.0
    assertion_local_coverage: int = 0
    binding_strength: BindingStrength = BindingStrength.UNBOUND
    binding_reasons: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "subject": self.subject,
            "operation_tokens": self.operation_tokens,
            "expected_literals": self.expected_literals,
            "expected_attributes": self.expected_attributes,
            "test_file": self.test_file,
            "test_name": self.test_name,
            "test_function_sha256": self.test_function_sha256,
            "subject_binding": self.subject_binding,
            "operation_binding": self.operation_binding,
            "assertion_binding": self.assertion_binding,
            "dataflow_binding": self.dataflow_binding,
            "critical_operation_coverage_ratio": self.critical_operation_coverage_ratio,
            "assertion_local_coverage": self.assertion_local_coverage,
            "binding_strength": self.binding_strength.value if isinstance(self.binding_strength, BindingStrength) else str(self.binding_strength),
            "binding_reasons": self.binding_reasons
        }


class WitnessBindingAnalyzer:
    """Analyzes AST witness graphs to establish provable ClaimWitnessBinding."""

    @staticmethod
    def extract_critical_operations(claim: MemoryClaim) -> List[str]:
        """Extracts specific method calls and operation tokens from claim statement and object."""
        ops = []
        text = f"{claim.object} {claim.raw_statement}"

        # 1. Matches fn() tokens: e.g. write_text(), getvalue(), export_text(), str(), len()
        fn_matches = re.findall(r"([a-zA-Z_][a-zA-Z0-9_]*)\s*\(\)", text)
        for m in fn_matches:
            if m not in ops:
                ops.append(m)

        # 2. Matches `method` or 'method'
        quote_matches = re.findall(r"[`'\"]([a-zA-Z_][a-zA-Z0-9_]*)['`\"]", text)
        for q in quote_matches:
            if len(q) > 1 and q not in ops and q != claim.subject:
                ops.append(q)

        # 3. Matches explicit attribute phrases: e.g. "method attribute", "title attribute"
        attr_matches = re.findall(r"([a-zA-Z_][a-zA-Z0-9_]*)\s+(?:attribute|mode|property|parameter)", text, re.IGNORECASE)
        for a in attr_matches:
            if a not in ops and a != claim.subject:
                ops.append(a)

        # Filter stopwords
        stopwords = {"the", "and", "via", "with", "for", "set", "can", "when", "from", "that", "this", "is", "returns", "instance"}
        return [o for o in ops if o.lower() not in stopwords]

    @staticmethod
    def extract_expected_literals_and_keywords(claim: MemoryClaim) -> Tuple[List[str], List[str]]:
        """Extracts expected literals (e.g. 'FastAPI', False, 'foo') and keywords (e.g. record=True)."""
        literals = []
        keywords = []
        text = f"{claim.object} {claim.raw_statement}"

        # Extract string literals in quotes
        str_literals = re.findall(r"['\"]([^'\"]+)['\"]", text)
        for s in str_literals:
            if s and s != claim.subject:
                literals.append(s)

        # Extract keyword assignments like record=True, debug=False
        kw_matches = re.findall(r"([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*([a-zA-Z0-9_]+)", text)
        for k, v in kw_matches:
            keywords.append(f"{k}={v}")

        return literals, keywords

    def analyze_witness(
        self,
        claim: MemoryClaim,
        candidate: TestCandidate,
        dependency_symbol: Optional[str] = None
    ) -> ClaimWitnessBinding:
        """
        Builds and traverses an AST witness graph for candidate against claim.
        """
        subject = claim.subject.split(".")[-1] if claim.subject else ""
        critical_ops = self.extract_critical_operations(claim)
        exp_literals, exp_kws = self.extract_expected_literals_and_keywords(claim)

        binding = ClaimWitnessBinding(
            claim_id=claim.claim_id,
            subject=subject,
            operation_tokens=critical_ops,
            expected_literals=exp_literals,
            expected_attributes=exp_kws,
            test_file=candidate.test_file,
            test_name=candidate.test_name,
            test_function_sha256=candidate.test_function_sha256
        )

        test_src = candidate.test_source or ""
        if not test_src:
            binding.binding_strength = BindingStrength.UNBOUND
            binding.binding_reasons.append("Missing test function source code")
            return binding

        try:
            tree = ast.parse(test_src)
        except Exception as ex:
            binding.binding_strength = BindingStrength.UNBOUND
            binding.binding_reasons.append(f"Failed to parse test function AST: {ex}")
            return binding

        # -------------------------------------------------------------
        # Phase 1: Track Subject Construction & Variable Propagation
        # -------------------------------------------------------------
        subject_vars: Set[str] = set()
        direct_subject_calls: List[ast.Call] = []
        subject_nodes_found = 0

        # Scan AST for Subject usage
        for node in ast.walk(tree):
            # Exclude docstrings
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                continue

            # Check direct instantiation in Call: Subject(...)
            if isinstance(node, ast.Call):
                func_name = ""
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    func_name = node.func.attr
                if func_name == subject:
                    direct_subject_calls.append(node)
                    subject_nodes_found += 1

            # Check variable assignments: var = Subject(...) or var = Subject
            elif isinstance(node, ast.Assign):
                is_subject_val = False
                if isinstance(node.value, ast.Call):
                    if isinstance(node.value.func, ast.Name) and node.value.func.id == subject:
                        is_subject_val = True
                    elif isinstance(node.value.func, ast.Attribute) and node.value.func.attr == subject:
                        is_subject_val = True
                elif isinstance(node.value, ast.Name) and node.value.id == subject:
                    is_subject_val = True

                if is_subject_val:
                    subject_nodes_found += 1
                    for tgt in node.targets:
                        if isinstance(tgt, ast.Name):
                            subject_vars.add(tgt.id)

        # 1-hop variable propagation: e.g. alias_var = var
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                if isinstance(node.value, ast.Name) and node.value.id in subject_vars:
                    for tgt in node.targets:
                        if isinstance(tgt, ast.Name):
                            subject_vars.add(tgt.id)

        binding.subject_binding = (subject_nodes_found > 0 or len(subject_vars) > 0 or len(direct_subject_calls) > 0)
        if not binding.subject_binding:
            binding.binding_strength = BindingStrength.UNBOUND
            binding.binding_reasons.append(f"Subject '{subject}' not instantiated or called in test code.")
            return binding

        # -------------------------------------------------------------
        # Phase 2: Track Operations on Subject Instance & Dataflow
        # -------------------------------------------------------------
        covered_operations: Set[str] = set()
        asserted_operations: Set[str] = set()
        result_vars_to_assert: Set[str] = set()
        has_direct_assert_dataflow = False

        # Check operations applied directly to subject variable or direct Call
        for node in ast.walk(tree):
            # Check attribute method calls: var.op(...)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                recv = node.func.value
                attr_name = node.func.attr
                recv_is_subject = False
                if isinstance(recv, ast.Name) and recv.id in subject_vars:
                    recv_is_subject = True
                elif isinstance(recv, ast.Call) and isinstance(recv.func, ast.Name) and recv.func.id == subject:
                    recv_is_subject = True

                if recv_is_subject:
                    for op in critical_ops:
                        if attr_name.lower() == op.lower():
                            covered_operations.add(op)

            # Check built-in calls: op(var) or op(Subject(...))
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                fn_name = node.func.id
                # Check if first arg is subject
                if node.args:
                    first_arg = node.args[0]
                    arg_is_subject = False
                    if isinstance(first_arg, ast.Name) and first_arg.id in subject_vars:
                        arg_is_subject = True
                    elif isinstance(first_arg, ast.Call) and isinstance(first_arg.func, ast.Name) and first_arg.func.id == subject:
                        arg_is_subject = True

                    if arg_is_subject:
                        for op in critical_ops:
                            if fn_name.lower() == op.lower():
                                covered_operations.add(op)

            # Check assignments capturing operation results: res = var.op(...) or res = op(var)
            if isinstance(node, ast.Assign):
                val = node.value
                op_captured = None
                if isinstance(val, ast.Call):
                    if isinstance(val.func, ast.Attribute):
                        recv = val.func.value
                        if (isinstance(recv, ast.Name) and recv.id in subject_vars) or (isinstance(recv, ast.Call) and isinstance(recv.func, ast.Name) and recv.func.id == subject):
                            op_captured = val.func.attr
                    elif isinstance(val.func, ast.Name):
                        if val.args and ((isinstance(val.args[0], ast.Name) and val.args[0].id in subject_vars) or (isinstance(val.args[0], ast.Call) and isinstance(val.args[0].func, ast.Name) and val.args[0].func.id == subject)):
                            op_captured = val.func.id

                if op_captured:
                    for tgt in node.targets:
                        if isinstance(tgt, ast.Name):
                            result_vars_to_assert.add(tgt.id)
                            for op in critical_ops:
                                if op_captured.lower() == op.lower():
                                    covered_operations.add(op)

        # -------------------------------------------------------------
        # Phase 3: Track Assertions & Verifiable Witness Paths
        # -------------------------------------------------------------
        for node in ast.walk(tree):
            if isinstance(node, ast.Assert):
                # Walk expression inside assert
                for inner in ast.walk(node):
                    # Direct call inside assert: assert var.op() == ... or assert op(Subject(...)) == ...
                    if isinstance(inner, ast.Call):
                        if isinstance(inner.func, ast.Attribute):
                            recv = inner.func.value
                            if (isinstance(recv, ast.Name) and recv.id in subject_vars) or (isinstance(recv, ast.Call) and isinstance(recv.func, ast.Name) and recv.func.id == subject):
                                has_direct_assert_dataflow = True
                                for op in critical_ops:
                                    if inner.func.attr.lower() == op.lower():
                                        asserted_operations.add(op)
                        elif isinstance(inner.func, ast.Name):
                            if inner.args and ((isinstance(inner.args[0], ast.Name) and inner.args[0].id in subject_vars) or (isinstance(inner.args[0], ast.Call) and isinstance(inner.args[0].func, ast.Name) and inner.args[0].func.id == subject)):
                                has_direct_assert_dataflow = True
                                for op in critical_ops:
                                    if inner.func.id.lower() == op.lower():
                                        asserted_operations.add(op)

                    # Result variable evaluated in assert: assert res == ...
                    elif isinstance(inner, ast.Name) and inner.id in result_vars_to_assert:
                        has_direct_assert_dataflow = True
                        for op in covered_operations:
                            asserted_operations.add(op)

        # For dependency contract: check if subject and dependency both present
        if claim.claim_type == ClaimType.DEPENDENCY_CONTRACT and dependency_symbol:
            dep_clean = dependency_symbol.split(".")[-1]
            has_dep = False
            for node in ast.walk(tree):
                if isinstance(node, ast.Name) and node.id == dep_clean:
                    has_dep = True
                elif isinstance(node, ast.Attribute) and node.attr == dep_clean:
                    has_dep = True
            if has_dep:
                covered_operations.add(dep_clean)
                asserted_operations.add(dep_clean)

        # -------------------------------------------------------------
        # Phase 4: Compute Witness Metrics & Decision Strength
        # -------------------------------------------------------------
        binding.operation_binding = len(covered_operations) > 0 or len(critical_ops) == 0
        binding.assertion_binding = (has_direct_assert_dataflow or len(asserted_operations) > 0)
        binding.dataflow_binding = (binding.subject_binding and binding.assertion_binding)
        binding.assertion_local_coverage = len(asserted_operations)

        if critical_ops:
            cov_ratio = len(covered_operations.intersection(set(critical_ops))) / float(len(critical_ops))
        else:
            cov_ratio = 1.0
        binding.critical_operation_coverage_ratio = cov_ratio

        # Determine final binding strength
        if claim.claim_type == ClaimType.BEHAVIORAL_CONTRACT:
            # Case 1: Multi-operation behavioral contracts (e.g. write_text AND getvalue, or print AND export_text)
            if len(critical_ops) >= 2:
                if cov_ratio >= 1.0 and binding.assertion_binding and binding.dataflow_binding:
                    binding.binding_strength = BindingStrength.STRONG
                    binding.binding_reasons.append(f"Full critical operation chain covered {critical_ops} with direct assertion dataflow.")
                else:
                    binding.binding_strength = BindingStrength.WEAK
                    binding.binding_reasons.append(f"Partial critical operation coverage ({len(covered_operations)}/{len(critical_ops)} ops).")

            # Case 2: Single-operation or generic built-in (e.g. str(Text("foo")))
            elif len(critical_ops) == 1:
                op = critical_ops[0]
                if op in GENERIC_BUILTIN_OPS:
                    if (op in asserted_operations or op in covered_operations) and has_direct_assert_dataflow:
                        binding.binding_strength = BindingStrength.STRONG
                        binding.binding_reasons.append(f"Direct verified dataflow from Subject to generic operation '{op}' inside assertion.")
                    else:
                        binding.binding_strength = BindingStrength.WEAK
                        binding.binding_reasons.append(f"Generic operation '{op}' lacks direct assertion-local subject dataflow.")
                else:
                    if op in asserted_operations and binding.dataflow_binding:
                        binding.binding_strength = BindingStrength.STRONG
                        binding.binding_reasons.append(f"Verified operation '{op}' asserting subject state.")
                    else:
                        binding.binding_strength = BindingStrength.WEAK
                        binding.binding_reasons.append(f"Operation '{op}' executed without direct assertion binding.")

            # Case 3: Attribute/State verification (e.g. default title or debug mode)
            else:
                if binding.assertion_binding and binding.dataflow_binding:
                    binding.binding_strength = BindingStrength.STRONG
                    binding.binding_reasons.append("Direct assertion verification on subject instance state.")
                else:
                    binding.binding_strength = BindingStrength.WEAK
                    binding.binding_reasons.append("Subject instantiated without direct claim attribute assertion.")

        elif claim.claim_type == ClaimType.DEPENDENCY_CONTRACT:
            dep_clean = dependency_symbol.split(".")[-1] if dependency_symbol else ""
            if binding.subject_binding and (dep_clean in asserted_operations or dep_clean in covered_operations) and binding.assertion_binding:
                binding.binding_strength = BindingStrength.STRONG
                binding.binding_reasons.append(f"Direct dependency linkage between '{subject}' and '{dependency_symbol}' verified in assertion flow.")
            else:
                binding.binding_strength = BindingStrength.WEAK
                binding.binding_reasons.append("Dependency linkage not fully asserted in dataflow.")

        else:
            if binding.subject_binding and binding.assertion_binding:
                binding.binding_strength = BindingStrength.STRONG
                binding.binding_reasons.append("Direct symbol assertion in test body.")
            elif binding.subject_binding:
                binding.binding_strength = BindingStrength.WEAK
            else:
                binding.binding_strength = BindingStrength.UNBOUND

        return binding

    def rank_candidates(
        self,
        claim: MemoryClaim,
        candidates: List[TestCandidate],
        dependency_symbol: Optional[str] = None
    ) -> List[TestCandidate]:
        """Ranks test candidates using the structured ClaimWitnessBinding hierarchy."""
        evaluated: List[Tuple[TestCandidate, ClaimWitnessBinding]] = []

        for cand in candidates:
            witness = self.analyze_witness(claim, cand, dependency_symbol=dependency_symbol)
            cand.witness_binding = witness.to_dict()
            cand.binding_strength = witness.binding_strength
            cand.discovery_reason = "; ".join(witness.binding_reasons)
            evaluated.append((cand, witness))

        # Ranking Hierarchy:
        # 1. Witness binding strength (STRONG=2, WEAK=1, UNBOUND=0)
        # 2. Critical operation coverage ratio (1.0 > 0.5 > 0.0)
        # 3. Assertion-local operation coverage (number of asserted operations)
        # 4. Subject-dataflow connectivity (boolean)
        # 5. Test name similarity to claim operations / subject
        # 6. Raw mention count (weak tie-breaker)
        # 7. Assertion count (last tie-breaker)
        def ranking_key(item: Tuple[TestCandidate, ClaimWitnessBinding]) -> Tuple[int, float, int, int, int, int, int]:
            cand, wit = item
            s_val = 2 if wit.binding_strength == BindingStrength.STRONG else (1 if wit.binding_strength == BindingStrength.WEAK else 0)
            df_val = 1 if wit.dataflow_binding else 0

            # Test name similarity
            name_sim = 0
            t_name_lower = cand.test_name.lower()
            for op in wit.operation_tokens:
                if op.lower() in t_name_lower:
                    name_sim += 2
            if wit.subject.lower() in t_name_lower:
                name_sim += 1

            return (
                s_val,
                wit.critical_operation_coverage_ratio,
                wit.assertion_local_coverage,
                df_val,
                name_sim,
                cand.subject_mentions + cand.object_mentions,
                cand.assertion_count
            )

        sorted_pairs = sorted(evaluated, key=ranking_key, reverse=True)
        return [pair[0] for pair in sorted_pairs]
