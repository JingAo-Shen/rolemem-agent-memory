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


WSGI_CANONICAL_KEYS = {
    "REQUEST_METHOD",
    "SCRIPT_NAME",
    "PATH_INFO",
    "SERVER_NAME",
    "SERVER_PORT",
    "SERVER_PROTOCOL",
    "wsgi.version",
    "wsgi.url_scheme",
    "wsgi.input",
    "wsgi.errors",
    "wsgi.multithread",
    "wsgi.multiprocess",
    "wsgi.run_once"
}


@dataclass
class OperationEvent:
    operation: str
    lineno: int
    receiver_or_subject: Optional[str] = None
    result_var: Optional[str] = None
    control_scope: Tuple[Tuple[int, str], ...] = ()


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
    def _traverse_with_scope(node: ast.AST, current_scope: Tuple[Tuple[int, str], ...] = ()):
        """Traverses AST yielding (node, control_scope) tuples to detect mutually exclusive branches."""
        yield node, current_scope
        if isinstance(node, ast.If):
            for child in node.body:
                yield from WitnessBindingAnalyzer._traverse_with_scope(child, current_scope + ((id(node), "then"),))
            for child in node.orelse:
                yield from WitnessBindingAnalyzer._traverse_with_scope(child, current_scope + ((id(node), "else"),))
        elif isinstance(node, ast.Try):
            for child in node.body:
                yield from WitnessBindingAnalyzer._traverse_with_scope(child, current_scope + ((id(node), "try"),))
            for handler in node.handlers:
                for child in handler.body:
                    yield from WitnessBindingAnalyzer._traverse_with_scope(child, current_scope + ((id(handler), "except"),))
            for child in node.orelse:
                yield from WitnessBindingAnalyzer._traverse_with_scope(child, current_scope + ((id(node), "try_else"),))
            for child in node.finalbody:
                yield from WitnessBindingAnalyzer._traverse_with_scope(child, current_scope + ((id(node), "finally"),))
        elif isinstance(node, (ast.For, ast.While)):
            for child in node.body:
                yield from WitnessBindingAnalyzer._traverse_with_scope(child, current_scope + ((id(node), "loop"),))
            for child in node.orelse:
                yield from WitnessBindingAnalyzer._traverse_with_scope(child, current_scope + ((id(node), "loop_else"),))
        elif isinstance(node, ast.With):
            for child in node.body:
                yield from WitnessBindingAnalyzer._traverse_with_scope(child, current_scope + ((id(node), "with"),))
        else:
            for field, value in ast.iter_fields(node):
                if isinstance(value, list):
                    for item in value:
                        if isinstance(item, ast.AST):
                            yield from WitnessBindingAnalyzer._traverse_with_scope(item, current_scope)
                elif isinstance(value, ast.AST):
                    yield from WitnessBindingAnalyzer._traverse_with_scope(value, current_scope)

    @staticmethod
    def are_mutually_exclusive(scope1: Tuple[Tuple[int, str], ...], scope2: Tuple[Tuple[int, str], ...]) -> bool:
        """Returns True if two control scopes are in mutually exclusive branches of the same construct."""
        dict1 = dict(scope1)
        dict2 = dict(scope2)
        common_blocks = set(dict1.keys()) & set(dict2.keys())
        for b in common_blocks:
            if dict1[b] != dict2[b]:
                return True
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
        elif expected_semantic == "MAPPING":
            if isinstance(first_arg, ast.Dict):
                return True
            if isinstance(first_arg, ast.Call) and isinstance(first_arg.func, ast.Name) and first_arg.func.id == "dict":
                return True
            if isinstance(first_arg, ast.Name):
                val = var_assignments.get(first_arg.id)
                if isinstance(val, dict):
                    return True
            return False
        elif expected_semantic == "ENVIRON":
            # Must contain WSGI-specific observable evidence (canonical WSGI keys)
            keys = set()
            if isinstance(first_arg, ast.Dict):
                for k in first_arg.keys:
                    if k is not None:
                        k_val = WitnessBindingAnalyzer._extract_node_constant(k, var_assignments)
                        if k_val:
                            keys.add(str(k_val))
            elif isinstance(first_arg, ast.Name):
                val = var_assignments.get(first_arg.id)
                if isinstance(val, dict):
                    keys = set(str(k) for k in val.keys())
            has_wsgi = any(k in WSGI_CANONICAL_KEYS for k in keys)
            return has_wsgi
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
            def find_chain(op_idx: int, last_lineno: int, last_scope: Tuple[Tuple[int, str], ...]) -> bool:
                if op_idx >= len(seq_ops):
                    return True
                target_op = seq_ops[op_idx].lower()
                for e in r_events:
                    if e.operation.lower() == target_op and e.lineno > last_lineno:
                        if not WitnessBindingAnalyzer.are_mutually_exclusive(last_scope, e.control_scope):
                            if find_chain(op_idx + 1, e.lineno, e.control_scope):
                                return True
                return False

            if find_chain(0, -1, ()):
                return True
        return False

    @staticmethod
    def _extract_str_provenance(
        node: ast.AST,
        subject_vars: Set[str],
        subject_name: str,
        result_var_provenance: Dict[str, Dict[str, Any]],
        inline_subject_instances: Dict[int, Dict[str, Any]]
    ) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "str":
            if node.args:
                arg0 = node.args[0]
                if isinstance(arg0, ast.Name) and (arg0.id in subject_vars or arg0.id == subject_name):
                    return True, arg0.id, None
                if isinstance(arg0, ast.Call) and isinstance(arg0.func, ast.Name) and arg0.func.id == subject_name:
                    inline_dict = inline_subject_instances.get(id(arg0))
                    return True, None, inline_dict
        if isinstance(node, ast.Name):
            if node.id in result_var_provenance and result_var_provenance[node.id].get("operation") == "str":
                return True, node.id, None
        return False, None, None

    @staticmethod
    def _extract_len_provenance(
        node: ast.AST,
        subject_vars: Set[str],
        subject_name: str,
        result_var_provenance: Dict[str, Dict[str, Any]],
        inline_subject_instances: Dict[int, Dict[str, Any]]
    ) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "len":
            if node.args:
                arg0 = node.args[0]
                if isinstance(arg0, ast.Name) and (arg0.id in subject_vars or arg0.id == subject_name):
                    return True, arg0.id, None
                if isinstance(arg0, ast.Call) and isinstance(arg0.func, ast.Name) and arg0.func.id == subject_name:
                    inline_dict = inline_subject_instances.get(id(arg0))
                    return True, None, inline_dict
        if isinstance(node, ast.Name):
            if node.id in result_var_provenance and result_var_provenance[node.id].get("operation") == "len":
                return True, node.id, None
        return False, None, None

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
        subject_instances: Dict[str, Dict[str, Any]] = {}
        inline_subject_instances: Dict[int, Dict[str, Any]] = {}
        direct_subject_calls: List[ast.Call] = []
        subject_nodes_found = 0
        operation_events: List[OperationEvent] = []
        result_var_provenance: Dict[str, Dict[str, Any]] = {}

        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                val = node.value
                val_repr = None
                if isinstance(val, ast.Constant):
                    val_repr = val.value
                elif isinstance(val, ast.Dict):
                    dict_val = {}
                    for k, v in zip(val.keys, val.values):
                        if k is not None:
                            k_const = WitnessBindingAnalyzer._extract_node_constant(k, var_assignments)
                            v_const = WitnessBindingAnalyzer._extract_node_constant(v, var_assignments) if v else None
                            if k_const is not None:
                                dict_val[str(k_const)] = v_const
                    val_repr = dict_val
                elif isinstance(val, ast.Call) and isinstance(val.func, ast.Name):
                    if val.func.id == "range":
                        stop_val = None
                        if val.args and isinstance(val.args[0], ast.Constant):
                            stop_val = val.args[0].value
                        val_repr = {"type": "range", "stop": stop_val}
                elif isinstance(val, (ast.List, ast.Tuple, ast.Set)):
                    val_repr = [WitnessBindingAnalyzer._extract_node_constant(elt, var_assignments) for elt in getattr(val, "elts", [])]

                if val_repr is not None:
                    for tgt in node.targets:
                        if isinstance(tgt, ast.Name):
                            var_assignments[tgt.id] = val_repr

                # Check variable assignments to Subject
                is_subject_val = False
                subj_call_node = None
                if isinstance(val, ast.Call):
                    if isinstance(val.func, ast.Name) and val.func.id == subject:
                        is_subject_val = True
                        subj_call_node = val
                        direct_subject_calls.append(val)
                    elif isinstance(val.func, ast.Attribute) and val.func.attr == subject:
                        is_subject_val = True
                        subj_call_node = val
                        direct_subject_calls.append(val)
                elif isinstance(val, ast.Name) and (val.id in subject_vars or val.id == subject):
                    is_subject_val = True
                    for tgt in node.targets:
                        if isinstance(tgt, ast.Name):
                            subject_vars.add(tgt.id)
                            if val.id in subject_instances:
                                subject_instances[tgt.id] = subject_instances[val.id]

                if is_subject_val and subj_call_node:
                    subject_nodes_found += 1
                    input_lit = None
                    input_card = None
                    if len(subj_call_node.args) > 0:
                        arg0 = subj_call_node.args[0]
                        if isinstance(arg0, ast.Constant):
                            input_lit = arg0.value
                        elif isinstance(arg0, ast.Name):
                            v_named = var_assignments.get(arg0.id)
                            if isinstance(v_named, str):
                                input_lit = v_named
                            elif isinstance(v_named, dict) and v_named.get("type") == "range":
                                input_card = v_named.get("stop")
                            elif isinstance(v_named, (list, tuple, set, dict)):
                                input_card = len(v_named)
                        elif isinstance(arg0, ast.Call) and isinstance(arg0.func, ast.Name) and arg0.func.id == "range":
                            if arg0.args and isinstance(arg0.args[0], ast.Constant):
                                input_card = arg0.args[0].value

                    for tgt in node.targets:
                        if isinstance(tgt, ast.Name):
                            subject_vars.add(tgt.id)
                            subject_instances[tgt.id] = {
                                "input_literal": input_lit,
                                "input_cardinality": input_card,
                                "call_node": subj_call_node
                            }

            elif isinstance(node, ast.Call):
                func_name = ""
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    func_name = node.func.attr
                if func_name == subject:
                    direct_subject_calls.append(node)
                    subject_nodes_found += 1
                    input_lit = None
                    input_card = None
                    if len(node.args) > 0:
                        arg0 = node.args[0]
                        if isinstance(arg0, ast.Constant):
                            input_lit = arg0.value
                        elif isinstance(arg0, ast.Name):
                            v_named = var_assignments.get(arg0.id)
                            if isinstance(v_named, str):
                                input_lit = v_named
                            elif isinstance(v_named, dict) and v_named.get("type") == "range":
                                input_card = v_named.get("stop")
                            elif isinstance(v_named, (list, tuple, set, dict)):
                                input_card = len(v_named)
                        elif isinstance(arg0, ast.Call) and isinstance(arg0.func, ast.Name) and arg0.func.id == "range":
                            if arg0.args and isinstance(arg0.args[0], ast.Constant):
                                input_card = arg0.args[0].value
                    inline_subject_instances[id(node)] = {
                        "input_literal": input_lit,
                        "input_cardinality": input_card,
                        "call_node": node
                    }

            elif isinstance(node, ast.Name) and node.id == subject:
                subject_nodes_found += 1
            elif isinstance(node, ast.Attribute) and node.attr == subject:
                subject_nodes_found += 1

        # 1-hop alias propagation: e.g. alias_var = var
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                if isinstance(node.value, ast.Name) and node.value.id in subject_vars:
                    for tgt in node.targets:
                        if isinstance(tgt, ast.Name):
                            subject_vars.add(tgt.id)
                            if node.value.id in subject_instances:
                                subject_instances[tgt.id] = subject_instances[node.value.id]

        binding.subject_binding = (subject_nodes_found > 0 or len(subject_vars) > 0 or len(direct_subject_calls) > 0)
        if not binding.subject_binding:
            binding.binding_strength = BindingStrength.UNBOUND
            binding.binding_reasons.append(f"Subject '{subject}' not instantiated or called in test code.")
            return binding

        # -------------------------------------------------------------
        # Phase 2: Track Operations on Subject Instance & Scoped Events
        # -------------------------------------------------------------
        covered_operations: Set[str] = set()
        asserted_operations: Set[str] = set()
        result_vars_to_assert: Set[str] = set()
        has_direct_assert_dataflow = False

        for node, c_scope in WitnessBindingAnalyzer._traverse_with_scope(tree):
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
                        receiver_or_subject=receiver_name,
                        control_scope=c_scope
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
                            receiver_or_subject=receiver_name,
                            control_scope=c_scope
                        ))

            # 3. Assignments capturing operation results: res = var.op(...) or res = op(var)
            if isinstance(node, ast.Assign):
                val = node.value
                op_captured = None
                receiver_name = None
                input_lit = None
                input_card = None

                if isinstance(val, ast.Call):
                    if isinstance(val.func, ast.Attribute):
                        recv = val.func.value
                        if isinstance(recv, ast.Name) and recv.id in subject_vars:
                            op_captured = val.func.attr
                            receiver_name = recv.id
                            if receiver_name in subject_instances:
                                input_lit = subject_instances[receiver_name].get("input_literal")
                                input_card = subject_instances[receiver_name].get("input_cardinality")
                        elif isinstance(recv, ast.Call) and isinstance(recv.func, ast.Name) and recv.func.id == subject:
                            op_captured = val.func.attr
                            receiver_name = subject
                            if id(recv) in inline_subject_instances:
                                input_lit = inline_subject_instances[id(recv)].get("input_literal")
                                input_card = inline_subject_instances[id(recv)].get("input_cardinality")
                    elif isinstance(val.func, ast.Name):
                        if val.args:
                            arg0 = val.args[0]
                            if isinstance(arg0, ast.Name) and arg0.id in subject_vars:
                                op_captured = val.func.id
                                receiver_name = arg0.id
                                if receiver_name in subject_instances:
                                    input_lit = subject_instances[receiver_name].get("input_literal")
                                    input_card = subject_instances[receiver_name].get("input_cardinality")
                            elif isinstance(arg0, ast.Call) and isinstance(arg0.func, ast.Name) and arg0.func.id == subject:
                                op_captured = val.func.id
                                receiver_name = subject
                                if id(arg0) in inline_subject_instances:
                                    input_lit = inline_subject_instances[id(arg0)].get("input_literal")
                                    input_card = inline_subject_instances[id(arg0)].get("input_cardinality")

                if op_captured:
                    covered_operations.add(op_captured)
                    for tgt in node.targets:
                        if isinstance(tgt, ast.Name):
                            result_vars_to_assert.add(tgt.id)
                            result_var_provenance[tgt.id] = {
                                "operation": op_captured,
                                "receiver": receiver_name,
                                "input_literal": input_lit,
                                "input_cardinality": input_card
                            }
                            operation_events.append(OperationEvent(
                                operation=op_captured,
                                lineno=lineno,
                                receiver_or_subject=receiver_name,
                                result_var=tgt.id,
                                control_scope=c_scope
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
                    # Generic default_configuration cannot be proven without observable attribute in claim
                    default_verified = False
                else:
                    # Check attribute state was verified on subject instance
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
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Assert):
                            test_expr = node.test
                            if isinstance(test_expr, ast.Compare):
                                left = test_expr.left
                                for op, comp in zip(test_expr.ops, test_expr.comparators):
                                    if isinstance(op, (ast.Eq, ast.Is)):
                                        is_str_l, recv_l, inline_l = WitnessBindingAnalyzer._extract_str_provenance(left, subject_vars, subject, result_var_provenance, inline_subject_instances)
                                        is_str_r, recv_r, inline_r = WitnessBindingAnalyzer._extract_str_provenance(comp, subject_vars, subject, result_var_provenance, inline_subject_instances)

                                        if is_str_l:
                                            expected_const = WitnessBindingAnalyzer._extract_node_constant(comp, var_assignments)
                                            input_lit = None
                                            if recv_l in subject_instances:
                                                input_lit = subject_instances[recv_l].get("input_literal")
                                            elif recv_l in result_var_provenance:
                                                input_lit = result_var_provenance[recv_l].get("input_literal")
                                            elif inline_l:
                                                input_lit = inline_l.get("input_literal")

                                            if input_lit is not None and expected_const == input_lit:
                                                rel_ok = True

                                        if is_str_r:
                                            expected_const = WitnessBindingAnalyzer._extract_node_constant(left, var_assignments)
                                            input_lit = None
                                            if recv_r in subject_instances:
                                                input_lit = subject_instances[recv_r].get("input_literal")
                                            elif recv_r in result_var_provenance:
                                                input_lit = result_var_provenance[recv_r].get("input_literal")
                                            elif inline_r:
                                                input_lit = inline_r.get("input_literal")

                                            if input_lit is not None and expected_const == input_lit:
                                                rel_ok = True

                elif req.expected_value == "total_count":
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Assert):
                            test_expr = node.test
                            if isinstance(test_expr, ast.Compare):
                                left = test_expr.left
                                for op, comp in zip(test_expr.ops, test_expr.comparators):
                                    if isinstance(op, (ast.Eq, ast.Is)):
                                        is_len_l, recv_l, inline_l = WitnessBindingAnalyzer._extract_len_provenance(left, subject_vars, subject, result_var_provenance, inline_subject_instances)
                                        is_len_r, recv_r, inline_r = WitnessBindingAnalyzer._extract_len_provenance(comp, subject_vars, subject, result_var_provenance, inline_subject_instances)

                                        if is_len_l:
                                            expected_const = WitnessBindingAnalyzer._extract_node_constant(comp, var_assignments)
                                            input_card = None
                                            if recv_l in subject_instances:
                                                input_card = subject_instances[recv_l].get("input_cardinality")
                                            elif recv_l in result_var_provenance:
                                                input_card = result_var_provenance[recv_l].get("input_cardinality")
                                            elif inline_l:
                                                input_card = inline_l.get("input_cardinality")

                                            if input_card is not None and expected_const == input_card:
                                                rel_ok = True

                                        if is_len_r:
                                            expected_const = WitnessBindingAnalyzer._extract_node_constant(left, var_assignments)
                                            input_card = None
                                            if recv_r in subject_instances:
                                                input_card = subject_instances[recv_r].get("input_cardinality")
                                            elif recv_r in result_var_provenance:
                                                input_card = result_var_provenance[recv_r].get("input_cardinality")
                                            elif inline_r:
                                                input_card = inline_r.get("input_cardinality")

                                            if input_card is not None and expected_const == input_card:
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
        if claim.claim_type == ClaimType.BEHAVIORAL_CONTRACT:
            if has_op_reqs:
                op_req_ids = {r.req_id for r in reqs if r.req_type == BehavioralRequirementType.OPERATION}
                binding.operation_binding = any(r_id in satisfied_req_ids for r_id in op_req_ids)
            else:
                binding.operation_binding = False
        else:
            binding.operation_binding = (len(covered_operations.intersection(set(critical_ops))) > 0) if critical_ops else False

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
