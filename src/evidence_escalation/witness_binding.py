"""
src/evidence_escalation/witness_binding.py

Claim Witness Binding & AST Dataflow Analysis Engine for Protocol V2.2-V1.2:
- Builds AST witness graphs for candidate test functions:
  Subject Construction -> Variable Propagation -> Operation Call -> Result -> Assertion.
- Integrates fine-grained BehavioralRequirement semantics (OPERATION, ATTRIBUTE_STATE, CONSTRUCTOR_ARGUMENT, DEFAULT_VALUE, RETURN_RELATION, SEQUENCE).
- Eliminates assumption that empty operations equals 100% operation coverage.
- Enforces strict multi-requirement verification for state and default semantics.
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
from .contract_semantics import (
    BehavioralRequirement,
    BehavioralRequirementType,
    ContractSemanticsExtractor
)

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
    semantic_requirements: List[Dict[str, Any]] = field(default_factory=list)
    requirement_count: int = 0
    requirements_satisfied: int = 0
    requirement_coverage: float = 0.0
    operation_requirement_applicable: bool = True
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
            "semantic_requirements": self.semantic_requirements,
            "requirement_count": self.requirement_count,
            "requirements_satisfied": self.requirements_satisfied,
            "requirement_coverage": self.requirement_coverage,
            "operation_requirement_applicable": self.operation_requirement_applicable,
            "binding_strength": self.binding_strength.value if isinstance(self.binding_strength, BindingStrength) else str(self.binding_strength),
            "binding_reasons": self.binding_reasons
        }


class WitnessBindingAnalyzer:
    """Analyzes AST witness graphs to establish provable ClaimWitnessBinding."""

    @staticmethod
    def extract_critical_operations(claim: MemoryClaim) -> List[str]:
        """Extracts specific method calls and operation tokens from claim statement and object."""
        ops = []
        text = f"{claim.object or ''} {claim.raw_statement or ''}"

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
        text = f"{claim.object or ''} {claim.raw_statement or ''}"

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
        reqs = ContractSemanticsExtractor.extract_requirements(claim)

        has_op_reqs = any(r.req_type == BehavioralRequirementType.OPERATION for r in reqs) or bool(critical_ops)

        binding = ClaimWitnessBinding(
            claim_id=claim.claim_id,
            subject=subject,
            operation_tokens=critical_ops,
            expected_literals=exp_literals,
            expected_attributes=exp_kws,
            test_file=candidate.test_file,
            test_name=candidate.test_name,
            test_function_sha256=candidate.test_function_sha256,
            semantic_requirements=[r.to_dict() for r in reqs],
            requirement_count=len(reqs),
            operation_requirement_applicable=has_op_reqs
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
                        direct_subject_calls.append(node.value)
                    elif isinstance(node.value.func, ast.Attribute) and node.value.func.attr == subject:
                        is_subject_val = True
                        direct_subject_calls.append(node.value)
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

                    # Direct attribute access inside assert: assert var.attr == ...
                    elif isinstance(inner, ast.Attribute):
                        recv = inner.value
                        if (isinstance(recv, ast.Name) and recv.id in subject_vars) or (isinstance(recv, ast.Call) and isinstance(recv.func, ast.Name) and recv.func.id == subject):
                            has_direct_assert_dataflow = True
                            for op in critical_ops:
                                if inner.attr.lower() == op.lower():
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
        # Phase 4: Semantic Requirements Evaluation
        # -------------------------------------------------------------
        satisfied_req_ids: Set[str] = set()

        for req in reqs:
            # 1. CONSTRUCTOR_ARGUMENT
            if req.req_type == BehavioralRequirementType.CONSTRUCTOR_ARGUMENT:
                if req.expected_value == "0_args":
                    # Check for subject instantiation with zero positional and zero keyword args
                    zero_args_found = False
                    for call_node in direct_subject_calls:
                        if len(call_node.args) == 0 and len(call_node.keywords) == 0:
                            zero_args_found = True
                            break
                    if zero_args_found:
                        satisfied_req_ids.add(req.req_id)
                elif req.target_name != "input_arg":
                    # Check for keyword arg matching target_name
                    kw_found = False
                    for call_node in direct_subject_calls:
                        for kw in call_node.keywords:
                            if kw.arg == req.target_name:
                                if req.expected_value is None:
                                    kw_found = True
                                elif isinstance(kw.value, ast.Constant) and str(kw.value.value).lower() == str(req.expected_value).lower():
                                    kw_found = True
                                elif isinstance(kw.value, ast.Name) and kw.value.id.lower() == str(req.expected_value).lower():
                                    kw_found = True
                    if kw_found:
                        satisfied_req_ids.add(req.req_id)
                else:
                    # input_arg (e.g. instantiated with string)
                    if any(len(c.args) > 0 for c in direct_subject_calls):
                        satisfied_req_ids.add(req.req_id)

            # 2. OPERATION
            elif req.req_type == BehavioralRequirementType.OPERATION:
                op_t = req.target_name
                if op_t in covered_operations or op_t in asserted_operations:
                    satisfied_req_ids.add(req.req_id)

            # 3. SEQUENCE
            elif req.req_type == BehavioralRequirementType.SEQUENCE:
                # Target name format: "op1 -> op2"
                seq_ops = [s.strip() for s in req.target_name.split("->")]
                if len(seq_ops) >= 2 and all(op in covered_operations or op in asserted_operations for op in seq_ops):
                    satisfied_req_ids.add(req.req_id)

            # 4. ATTRIBUTE_STATE & DEFAULT_VALUE
            elif req.req_type in (BehavioralRequirementType.ATTRIBUTE_STATE, BehavioralRequirementType.DEFAULT_VALUE):
                attr_t = req.target_name
                exp_v = req.expected_value
                attr_verified = False

                # Search in asserts
                for node in ast.walk(tree):
                    if isinstance(node, ast.Assert):
                        for inner in ast.walk(node):
                            # assert var.attr == exp_v or assert var.attr is exp_v
                            if isinstance(inner, ast.Attribute):
                                if inner.attr.lower() == attr_t.lower():
                                    recv = inner.value
                                    if (isinstance(recv, ast.Name) and recv.id in subject_vars) or (isinstance(recv, ast.Call) and isinstance(recv.func, ast.Name) and recv.func.id == subject):
                                        if exp_v is None:
                                            attr_verified = True
                                        else:
                                            # Check if expected value is present in the assert comparison
                                            assert_str = ast.unparse(node) if hasattr(ast, "unparse") else ""
                                            if exp_v.lower() in assert_str.lower():
                                                attr_verified = True

                if attr_verified:
                    satisfied_req_ids.add(req.req_id)

            # 5. RETURN_RELATION
            elif req.req_type == BehavioralRequirementType.RETURN_RELATION:
                # Verify that operation output is compared in assertion
                if has_direct_assert_dataflow or len(asserted_operations) > 0:
                    satisfied_req_ids.add(req.req_id)

        binding.requirements_satisfied = len(satisfied_req_ids)
        binding.requirement_coverage = (
            len(satisfied_req_ids) / float(len(reqs)) if reqs else 0.0
        )

        # -------------------------------------------------------------
        # Phase 5: Compute Witness Metrics & Decision Strength
        # -------------------------------------------------------------
        binding.operation_binding = (len(covered_operations) > 0)
        binding.assertion_binding = (has_direct_assert_dataflow or len(asserted_operations) > 0)
        binding.dataflow_binding = (binding.subject_binding and binding.assertion_binding)
        binding.assertion_local_coverage = len(asserted_operations)

        if critical_ops:
            cov_ratio = len(covered_operations.intersection(set(critical_ops))) / float(len(critical_ops))
        else:
            cov_ratio = 0.0  # Protocol V2.2-V1.2: No automatic 1.0 for empty ops
        binding.critical_operation_coverage_ratio = cov_ratio

        # Determine final binding strength
        if claim.claim_type == ClaimType.BEHAVIORAL_CONTRACT:
            if len(reqs) > 0:
                # All critical requirements must be satisfied for STRONG
                if binding.requirement_coverage >= 1.0 and binding.dataflow_binding:
                    binding.binding_strength = BindingStrength.STRONG
                    binding.binding_reasons.append(f"All {len(reqs)} semantic requirements satisfied with verified assertion dataflow.")
                elif binding.requirements_satisfied > 0 or binding.subject_binding:
                    binding.binding_strength = BindingStrength.WEAK
                    binding.binding_reasons.append(f"Partial semantic requirement satisfaction ({binding.requirements_satisfied}/{len(reqs)} requirements verified).")
                else:
                    binding.binding_strength = BindingStrength.UNBOUND
                    binding.binding_reasons.append("Zero semantic requirements satisfied.")
            else:
                # Fallback if no requirements extracted
                if cov_ratio >= 1.0 and binding.assertion_binding and binding.dataflow_binding:
                    binding.binding_strength = BindingStrength.STRONG
                    binding.binding_reasons.append("Full operation coverage with assertion dataflow.")
                elif binding.subject_binding:
                    binding.binding_strength = BindingStrength.WEAK
                else:
                    binding.binding_strength = BindingStrength.UNBOUND

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
            cand.semantic_requirements = witness.semantic_requirements
            cand.requirement_count = witness.requirement_count
            cand.requirements_satisfied = witness.requirements_satisfied
            cand.requirement_coverage = witness.requirement_coverage
            cand.operation_requirement_applicable = witness.operation_requirement_applicable
            evaluated.append((cand, witness))

        # Ranking Hierarchy:
        # 1. Witness binding strength (STRONG=2, WEAK=1, UNBOUND=0)
        # 2. Semantic requirement coverage ratio (1.0 > 0.5 > 0.0)
        # 3. Critical operation coverage ratio (1.0 > 0.5 > 0.0)
        # 4. Assertion-local operation coverage (number of asserted operations)
        # 5. Subject-dataflow connectivity (boolean)
        # 6. Test name similarity to claim operations / subject
        # 7. Raw mention count (weak tie-breaker)
        # 8. Assertion count (last tie-breaker)
        def ranking_key(item: Tuple[TestCandidate, ClaimWitnessBinding]) -> Tuple[int, float, float, int, int, int, int, int]:
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
                wit.requirement_coverage,
                wit.critical_operation_coverage_ratio,
                wit.assertion_local_coverage,
                df_val,
                name_sim,
                cand.subject_mentions + cand.object_mentions,
                cand.assertion_count
            )

        sorted_pairs = sorted(evaluated, key=ranking_key, reverse=True)
        return [pair[0] for pair in sorted_pairs]
