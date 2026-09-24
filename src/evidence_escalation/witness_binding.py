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


@dataclass
class OperationEvent:
    operation: str
    lineno: int
    receiver_or_subject: Optional[str] = None
    result_var: Optional[str] = None


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

    @staticmethod
    def _extract_node_constant(node: ast.AST, var_assignments: Dict[str, Any]) -> Any:
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Name):
            if node.id in var_assignments:
                return var_assignments[node.id]
            if node.id.lower() == "true":
                return True
            if node.id.lower() == "false":
                return False
            if node.id.lower() == "none":
                return None
            return node.id
        return None

    @staticmethod
    def _is_attr_of_subject(node: ast.AST, attr_name: str, subject_vars: Set[str], subject_name: str) -> bool:
        if isinstance(node, ast.Attribute):
            if node.attr.lower() == attr_name.lower():
                recv = node.value
                if isinstance(recv, ast.Name) and (recv.id in subject_vars or recv.id == subject_name):
                    return True
                if isinstance(recv, ast.Call) and isinstance(recv.func, ast.Name) and recv.func.id == subject_name:
                    return True
        return False

    @staticmethod
    def _matches_expected_val(node: ast.AST, expected_val: Optional[str], var_assignments: Dict[str, Any]) -> bool:
        if expected_val is None:
            return True
        c_val = WitnessBindingAnalyzer._extract_node_constant(node, var_assignments)
        if c_val is not None:
            if isinstance(c_val, bool) or str(expected_val).lower() in ("true", "false"):
                return str(c_val).lower() == str(expected_val).lower()
            return str(c_val) == str(expected_val)
        if isinstance(node, ast.Name):
            return node.id.lower() == str(expected_val).lower()
        return False

    @staticmethod
    def _check_constructor_input_shape(call_node: ast.Call, expected_semantic: str, var_assignments: Dict[str, Any]) -> bool:
        if len(call_node.args) == 0:
            return False
        first_arg = call_node.args[0]
        if expected_semantic == "STRING":
            if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
                return True
            if isinstance(first_arg, ast.Name):
                val = var_assignments.get(first_arg.id)
                return isinstance(val, str)
            return False
        elif expected_semantic in ("MAPPING", "ENVIRON"):
            if isinstance(first_arg, ast.Dict):
                return True
            if isinstance(first_arg, ast.Call) and isinstance(first_arg.func, ast.Name) and first_arg.func.id == "dict":
                return True
            if isinstance(first_arg, ast.Name):
                val = var_assignments.get(first_arg.id)
                if isinstance(val, dict):
                    return True
                if "environ" in first_arg.id.lower() or "env" in first_arg.id.lower():
                    return True
            return False
        elif expected_semantic == "RANGE":
            if isinstance(first_arg, ast.Call) and isinstance(first_arg.func, ast.Name) and first_arg.func.id == "range":
                return True
            if isinstance(first_arg, ast.Name):
                val = var_assignments.get(first_arg.id)
                if isinstance(val, dict) and val.get("type") == "range":
                    return True
            return False
        elif expected_semantic == "ITERABLE":
            if isinstance(first_arg, (ast.List, ast.Tuple, ast.Set, ast.Dict)):
                return True
            if isinstance(first_arg, ast.Call) and isinstance(first_arg.func, ast.Name) and first_arg.func.id == "range":
                return True
            if isinstance(first_arg, ast.Name):
                val = var_assignments.get(first_arg.id)
                if isinstance(val, (list, tuple, set, dict)) or (isinstance(val, dict) and val.get("type") == "range"):
                    return True
            return False
        return True

    @staticmethod
    def _verify_operation_sequence(seq_ops: List[str], events: List[OperationEvent]) -> bool:
        if len(seq_ops) < 2:
            return True
        receivers = set(e.receiver_or_subject for e in events if e.receiver_or_subject)
        if not receivers:
            receivers = {None}
        for r in receivers:
            r_events = [e for e in events if e.receiver_or_subject == r or r is None]
            last_lineno = -1
            for op in seq_ops:
                found = False
                for e in r_events:
                    if e.operation.lower() == op.lower() and e.lineno > last_lineno:
                        last_lineno = e.lineno
                        found = True
                        break
                if not found:
                    break
            else:
                return True
        return False

    @staticmethod
    def _extract_str_call_or_result(node: ast.AST, subject_vars: Set[str], subject_name: str, var_assignments: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "str":
            if node.args:
                arg0 = node.args[0]
                if isinstance(arg0, ast.Name) and (arg0.id in subject_vars or arg0.id == subject_name):
                    return True, None
                if isinstance(arg0, ast.Call) and isinstance(arg0.func, ast.Name) and arg0.func.id == subject_name:
                    return True, None
        if isinstance(node, ast.Name):
            val = var_assignments.get(node.id)
            if isinstance(val, dict) and val.get("type") == "str_call":
                return True, None
        return False, None

    @staticmethod
    def _is_len_call_on_subject(node: ast.AST, subject_vars: Set[str], subject_name: str, var_assignments: Dict[str, Any]) -> bool:
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "len":
            if node.args:
                arg0 = node.args[0]
                if isinstance(arg0, ast.Name) and (arg0.id in subject_vars or arg0.id == subject_name):
                    return True
                if isinstance(arg0, ast.Call) and isinstance(arg0.func, ast.Name) and arg0.func.id == subject_name:
                    return True
        if isinstance(node, ast.Name):
            val = var_assignments.get(node.id)
            if isinstance(val, dict) and val.get("type") == "len_call":
                return True
        return False

    @staticmethod
    def _is_len_call_on_var(node: ast.AST, var_name: str) -> bool:
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "len":
            if node.args and isinstance(node.args[0], ast.Name) and node.args[0].id == var_name:
                return True
        return False

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

        # Protocol V2.2-V1.2: operation_requirement_applicable is strictly determined by OPERATION requirements
        has_op_reqs = any(r.req_type == BehavioralRequirementType.OPERATION for r in reqs)

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
        # Phase 1: Track Variable Assignments, Subject Construction & Aliases
        # -------------------------------------------------------------
        var_assignments: Dict[str, Any] = {}
        subject_vars: Set[str] = set()
        direct_subject_calls: List[ast.Call] = []
        subject_nodes_found = 0
        operation_events: List[OperationEvent] = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                # Track basic literal constants
                val = node.value
                val_repr = None
                if isinstance(val, ast.Constant):
                    val_repr = val.value
                elif isinstance(val, ast.Call) and isinstance(val.func, ast.Name):
                    if val.func.id == "range":
                        stop_val = None
                        if val.args and isinstance(val.args[0], ast.Constant):
                            stop_val = val.args[0].value
                        val_repr = {"type": "range", "stop": stop_val}
                    elif val.func.id == "str":
                        val_repr = {"type": "str_call"}
                    elif val.func.id == "len":
                        val_repr = {"type": "len_call"}
                elif isinstance(val, (ast.List, ast.Tuple, ast.Set)):
                    val_repr = [WitnessBindingAnalyzer._extract_node_constant(elt, var_assignments) for elt in getattr(val, "elts", [])]

                if val_repr is not None:
                    for tgt in node.targets:
                        if isinstance(tgt, ast.Name):
                            var_assignments[tgt.id] = val_repr

                # Check variable assignments to Subject
                is_subject_val = False
                if isinstance(val, ast.Call):
                    if isinstance(val.func, ast.Name) and val.func.id == subject:
                        is_subject_val = True
                        direct_subject_calls.append(val)
                    elif isinstance(val.func, ast.Attribute) and val.func.attr == subject:
                        is_subject_val = True
                        direct_subject_calls.append(val)
                elif isinstance(val, ast.Name) and val.id == subject:
                    is_subject_val = True

                if is_subject_val:
                    subject_nodes_found += 1
                    for tgt in node.targets:
                        if isinstance(tgt, ast.Name):
                            subject_vars.add(tgt.id)

            elif isinstance(node, ast.Call):
                func_name = ""
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    func_name = node.func.attr
                if func_name == subject:
                    direct_subject_calls.append(node)
                    subject_nodes_found += 1

        # 1-hop alias propagation: e.g. alias_var = var
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
        # Phase 2: Track Operations on Subject Instance & Statement Events
        # -------------------------------------------------------------
        covered_operations: Set[str] = set()
        asserted_operations: Set[str] = set()
        result_vars_to_assert: Set[str] = set()
        has_direct_assert_dataflow = False

        for node in ast.walk(tree):
            lineno = getattr(node, "lineno", 0)

            # 1. Method call: var.op(...)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                recv = node.func.value
                attr_name = node.func.attr
                recv_is_subject = False
                receiver_name = None

                if isinstance(recv, ast.Name) and recv.id in subject_vars:
                    recv_is_subject = True
                    receiver_name = recv.id
                elif isinstance(recv, ast.Call) and isinstance(recv.func, ast.Name) and recv.func.id == subject:
                    recv_is_subject = True
                    receiver_name = subject

                if recv_is_subject:
                    covered_operations.add(attr_name)
                    operation_events.append(OperationEvent(
                        operation=attr_name,
                        lineno=lineno,
                        receiver_or_subject=receiver_name
                    ))

            # 2. Built-in call: op(var) or op(Subject(...))
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                fn_name = node.func.id
                if node.args:
                    first_arg = node.args[0]
                    arg_is_subject = False
                    receiver_name = None
                    if isinstance(first_arg, ast.Name) and first_arg.id in subject_vars:
                        arg_is_subject = True
                        receiver_name = first_arg.id
                    elif isinstance(first_arg, ast.Call) and isinstance(first_arg.func, ast.Name) and first_arg.func.id == subject:
                        arg_is_subject = True
                        receiver_name = subject

                    if arg_is_subject:
                        covered_operations.add(fn_name)
                        operation_events.append(OperationEvent(
                            operation=fn_name,
                            lineno=lineno,
                            receiver_or_subject=receiver_name
                        ))

            # 3. Assignments capturing operation results: res = var.op(...) or res = op(var)
            if isinstance(node, ast.Assign):
                val = node.value
                op_captured = None
                receiver_name = None
                if isinstance(val, ast.Call):
                    if isinstance(val.func, ast.Attribute):
                        recv = val.func.value
                        if isinstance(recv, ast.Name) and recv.id in subject_vars:
                            op_captured = val.func.attr
                            receiver_name = recv.id
                        elif isinstance(recv, ast.Call) and isinstance(recv.func, ast.Name) and recv.func.id == subject:
                            op_captured = val.func.attr
                            receiver_name = subject
                    elif isinstance(val.func, ast.Name):
                        if val.args:
                            arg0 = val.args[0]
                            if isinstance(arg0, ast.Name) and arg0.id in subject_vars:
                                op_captured = val.func.id
                                receiver_name = arg0.id
                            elif isinstance(arg0, ast.Call) and isinstance(arg0.func, ast.Name) and arg0.func.id == subject:
                                op_captured = val.func.id
                                receiver_name = subject

                if op_captured:
                    covered_operations.add(op_captured)
                    for tgt in node.targets:
                        if isinstance(tgt, ast.Name):
                            result_vars_to_assert.add(tgt.id)
                            operation_events.append(OperationEvent(
                                operation=op_captured,
                                lineno=lineno,
                                receiver_or_subject=receiver_name,
                                result_var=tgt.id
                            ))

        # -------------------------------------------------------------
        # Phase 3: Track Assertions & Verifiable Witness Paths
        # -------------------------------------------------------------
        for node in ast.walk(tree):
            if isinstance(node, ast.Assert):
                for inner in ast.walk(node):
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

                    elif isinstance(inner, ast.Name) and inner.id in result_vars_to_assert:
                        has_direct_assert_dataflow = True
                        for op in covered_operations:
                            asserted_operations.add(op)

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
                    zero_args_found = False
                    for call_node in direct_subject_calls:
                        if len(call_node.args) == 0 and len(call_node.keywords) == 0:
                            zero_args_found = True
                            break
                    if zero_args_found:
                        satisfied_req_ids.add(req.req_id)
                elif req.target_name == "input_arg":
                    # Verify argument shape against expected semantic type
                    shape_ok = any(
                        WitnessBindingAnalyzer._check_constructor_input_shape(c, req.expected_value or "UNKNOWN", var_assignments)
                        for c in direct_subject_calls
                    )
                    if shape_ok:
                        satisfied_req_ids.add(req.req_id)
                else:
                    # Keyword argument matching
                    kw_found = False
                    for call_node in direct_subject_calls:
                        for kw in call_node.keywords:
                            if kw.arg == req.target_name:
                                if req.expected_value is None:
                                    kw_found = True
                                else:
                                    c_kw = WitnessBindingAnalyzer._extract_node_constant(kw.value, var_assignments)
                                    if str(c_kw).lower() == str(req.expected_value).lower():
                                        kw_found = True
                    if kw_found:
                        satisfied_req_ids.add(req.req_id)

            # 2. OPERATION
            elif req.req_type == BehavioralRequirementType.OPERATION:
                op_t = req.target_name
                if op_t in covered_operations or op_t in asserted_operations:
                    satisfied_req_ids.add(req.req_id)

            # 3. SEQUENCE
            elif req.req_type == BehavioralRequirementType.SEQUENCE:
                seq_ops = [s.strip() for s in req.target_name.split("->")]
                if WitnessBindingAnalyzer._verify_operation_sequence(seq_ops, operation_events):
                    satisfied_req_ids.add(req.req_id)

            # 4. ATTRIBUTE_STATE
            elif req.req_type == BehavioralRequirementType.ATTRIBUTE_STATE:
                attr_t = req.target_name
                exp_v = req.expected_value
                attr_verified = False

                for node in ast.walk(tree):
                    if isinstance(node, ast.Assert):
                        test_expr = node.test
                        # 1. Compare: left == comp or left is comp
                        if isinstance(test_expr, ast.Compare):
                            left = test_expr.left
                            for op, comp in zip(test_expr.ops, test_expr.comparators):
                                if isinstance(op, (ast.Eq, ast.Is)):
                                    if WitnessBindingAnalyzer._is_attr_of_subject(left, attr_t, subject_vars, subject) and WitnessBindingAnalyzer._matches_expected_val(comp, exp_v, var_assignments):
                                        attr_verified = True
                                    elif WitnessBindingAnalyzer._is_attr_of_subject(comp, attr_t, subject_vars, subject) and WitnessBindingAnalyzer._matches_expected_val(left, exp_v, var_assignments):
                                        attr_verified = True
                        # 2. UnaryOp Not: assert not var.attr
                        elif isinstance(test_expr, ast.UnaryOp) and isinstance(test_expr.op, ast.Not):
                            if WitnessBindingAnalyzer._is_attr_of_subject(test_expr.operand, attr_t, subject_vars, subject):
                                if exp_v is not None and str(exp_v).lower() == "false":
                                    attr_verified = True
                        # 3. Bare attribute: assert var.attr
                        elif WitnessBindingAnalyzer._is_attr_of_subject(test_expr, attr_t, subject_vars, subject):
                            if exp_v is None or str(exp_v).lower() == "true":
                                attr_verified = True

                if attr_verified:
                    satisfied_req_ids.add(req.req_id)

            # 5. DEFAULT_VALUE
            elif req.req_type == BehavioralRequirementType.DEFAULT_VALUE:
                attr_t = req.target_name
                exp_v = req.expected_value
                default_verified = False

                if attr_t == "default_configuration":
                    # Check for subject instantiation with zero positional and zero keyword args
                    # and verified assertion on default configuration / pools attributes
                    zero_args_found = False
                    for call_node in direct_subject_calls:
                        if len(call_node.args) == 0 and len(call_node.keywords) == 0:
                            zero_args_found = True
                            break

                    config_attr_verified = False
                    if zero_args_found:
                        for node in ast.walk(tree):
                            if isinstance(node, ast.Assert):
                                for inner in ast.walk(node):
                                    if isinstance(inner, ast.Attribute):
                                        if inner.attr in ("connection_pool_kw", "connection_pools", "default_config", "default_configuration"):
                                            recv = inner.value
                                            if isinstance(recv, ast.Name) and (recv.id in subject_vars or recv.id == subject):
                                                config_attr_verified = True
                                                break
                    if zero_args_found and config_attr_verified:
                        default_verified = True
                else:
                    # Check attribute state was verified
                    attr_verified = False
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Assert):
                            test_expr = node.test
                            if isinstance(test_expr, ast.Compare):
                                left = test_expr.left
                                for op, comp in zip(test_expr.ops, test_expr.comparators):
                                    if isinstance(op, (ast.Eq, ast.Is)):
                                        if WitnessBindingAnalyzer._is_attr_of_subject(left, attr_t, subject_vars, subject) and WitnessBindingAnalyzer._matches_expected_val(comp, exp_v, var_assignments):
                                            attr_verified = True
                                        elif WitnessBindingAnalyzer._is_attr_of_subject(comp, attr_t, subject_vars, subject) and WitnessBindingAnalyzer._matches_expected_val(left, exp_v, var_assignments):
                                            attr_verified = True
                            elif isinstance(test_expr, ast.UnaryOp) and isinstance(test_expr.op, ast.Not):
                                if WitnessBindingAnalyzer._is_attr_of_subject(test_expr.operand, attr_t, subject_vars, subject):
                                    if exp_v is not None and str(exp_v).lower() == "false":
                                        attr_verified = True
                            elif WitnessBindingAnalyzer._is_attr_of_subject(test_expr, attr_t, subject_vars, subject):
                                if exp_v is None or str(exp_v).lower() == "true":
                                    attr_verified = True

                    # Verify that constructor did NOT explicitly pass the keyword
                    not_explicitly_configured = True
                    for call_node in direct_subject_calls:
                        if any(kw.arg == attr_t for kw in call_node.keywords):
                            not_explicitly_configured = False
                            break

                    if attr_verified and not_explicitly_configured:
                        default_verified = True

                if default_verified:
                    satisfied_req_ids.add(req.req_id)

            # 6. RETURN_RELATION
            elif req.req_type == BehavioralRequirementType.RETURN_RELATION:
                rel_ok = False
                if req.expected_value == "plain_content":
                    # Verify literal-preserving string conversion
                    input_str = None
                    for call_node in direct_subject_calls:
                        if len(call_node.args) > 0:
                            arg = call_node.args[0]
                            if isinstance(arg, ast.Constant):
                                input_str = arg.value
                                break
                            elif isinstance(arg, ast.Name):
                                val = var_assignments.get(arg.id)
                                if isinstance(val, str):
                                    input_str = val
                                    break

                    for node in ast.walk(tree):
                        if isinstance(node, ast.Assert):
                            test_expr = node.test
                            if isinstance(test_expr, ast.Compare):
                                left = test_expr.left
                                for op, comp in zip(test_expr.ops, test_expr.comparators):
                                    if isinstance(op, (ast.Eq, ast.Is)):
                                        is_str_left, _ = WitnessBindingAnalyzer._extract_str_call_or_result(left, subject_vars, subject, var_assignments)
                                        is_str_right, _ = WitnessBindingAnalyzer._extract_str_call_or_result(comp, subject_vars, subject, var_assignments)

                                        if is_str_left:
                                            c_val = WitnessBindingAnalyzer._extract_node_constant(comp, var_assignments)
                                            if input_str is not None and c_val == input_str:
                                                rel_ok = True
                                        if is_str_right:
                                            l_val = WitnessBindingAnalyzer._extract_node_constant(left, var_assignments)
                                            if input_str is not None and l_val == input_str:
                                                rel_ok = True

                elif req.expected_value == "total_count":
                    input_cardinality = None
                    input_var_name = None
                    for call_node in direct_subject_calls:
                        if len(call_node.args) > 0:
                            arg = call_node.args[0]
                            if isinstance(arg, ast.Call) and isinstance(arg.func, ast.Name) and arg.func.id == "range":
                                if arg.args and isinstance(arg.args[0], ast.Constant):
                                    input_cardinality = arg.args[0].value
                            elif isinstance(arg, ast.Name):
                                input_var_name = arg.id
                                val = var_assignments.get(arg.id)
                                if isinstance(val, dict) and val.get("type") == "range":
                                    input_cardinality = val.get("stop")
                                elif isinstance(val, (list, tuple, set, dict)):
                                    input_cardinality = len(val)

                    for node in ast.walk(tree):
                        if isinstance(node, ast.Assert):
                            test_expr = node.test
                            if isinstance(test_expr, ast.Compare):
                                left = test_expr.left
                                for op, comp in zip(test_expr.ops, test_expr.comparators):
                                    if isinstance(op, (ast.Eq, ast.Is)):
                                        is_len_left = WitnessBindingAnalyzer._is_len_call_on_subject(left, subject_vars, subject, var_assignments)
                                        is_len_right = WitnessBindingAnalyzer._is_len_call_on_subject(comp, subject_vars, subject, var_assignments)

                                        if is_len_left:
                                            c_val = WitnessBindingAnalyzer._extract_node_constant(comp, var_assignments)
                                            if input_cardinality is not None and c_val == input_cardinality:
                                                rel_ok = True
                                            if input_var_name and WitnessBindingAnalyzer._is_len_call_on_var(comp, input_var_name):
                                                rel_ok = True
                                        if is_len_right:
                                            l_val = WitnessBindingAnalyzer._extract_node_constant(left, var_assignments)
                                            if input_cardinality is not None and l_val == input_cardinality:
                                                rel_ok = True
                                            if input_var_name and WitnessBindingAnalyzer._is_len_call_on_var(left, input_var_name):
                                                rel_ok = True

                elif has_direct_assert_dataflow or len(asserted_operations) > 0:
                    rel_ok = True

                if rel_ok:
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
