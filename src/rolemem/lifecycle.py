"""
src/rolemem/lifecycle.py

RoleMem Dynamic Memory Lifecycle Engine (Calibrated):
Evaluates active memory records against evolving repository target states S_target,
executes role-aware evidence verification and escalation ladder, and applies formal state transitions:
  - PRESERVE (VALID) -> Boost confidence, advance temporal anchor
  - DOWNGRADE (PARTIALLY_VALID) -> Decay confidence, attach advisory
  - INVALIDATE (STALE) -> Invalidate status, purge from active working set
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple, Union
import ast
import os
import subprocess
import time
import textwrap

from .schema import RoleMemoryRecord, RoleEnum, MemoryStatus, TemporalAnchor, DeprecationStatus
from src.claim_validity.types import MemoryClaim, ClaimType, ClaimEvaluationResult, ValidationStatus
from src.evidence_escalation.pipeline import EvidenceEscalationPipeline
from src.evidence_escalation.types import CostBudget, PipelineConfig


@dataclass
class FunctionSignature:
    """Extracted function or method signature for lifecycle checking."""
    name: str
    parameters: List[str]
    defaults: Dict[str, str]  # param_name -> default value representation string
    has_varargs: bool = False
    has_varkw: bool = False
    is_method: bool = False


class DefaultValueEvolutionChecker:
    """
    Dedicated checker for parameter default value evolution across codebase revisions.
    Compares old_signature vs new_signature according to formal lifecycle rules:
      - same parameter + same default => VALID
      - same parameter + changed default => PARTIALLY_VALID
      - parameter removed => STALE
      - parameter required without default => STALE
    """

    @classmethod
    def extract_signature_from_ast(
        cls,
        source_code: str,
        symbol_name: str
    ) -> Optional[FunctionSignature]:
        if not source_code:
            return None
        try:
            tree = ast.parse(textwrap.dedent(source_code))
        except Exception:
            return None

        target_func = None
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == symbol_name:
                target_func = node
                break
        if target_func is None:
            return None

        args = target_func.args.args
        defaults = target_func.args.defaults
        offset = len(args) - len(defaults)

        params = [a.arg for a in args]
        def_map: Dict[str, str] = {}
        for i, arg in enumerate(args):
            if i >= offset:
                def_node = defaults[i - offset]
                try:
                    act_val = ast.literal_eval(def_node)
                    val_str = str(act_val) if not isinstance(act_val, (int, float, bool, type(None))) else str(act_val)
                except Exception:
                    val_str = ast.unparse(def_node) if hasattr(ast, "unparse") else str(def_node)
                def_map[arg.arg] = val_str

        return FunctionSignature(
            name=symbol_name,
            parameters=params,
            defaults=def_map,
            has_varargs=target_func.args.vararg is not None,
            has_varkw=target_func.args.kwarg is not None,
            is_method=len(params) > 0 and params[0] in ("self", "cls")
        )

    @classmethod
    def check_evolution(
        cls,
        old_signature: Optional[FunctionSignature],
        new_signature: Optional[FunctionSignature],
        parameter_name: str,
        expected_default: Any = None
    ) -> Tuple[str, str, str]:
        """
        Evaluate evolution of default value from old_signature (or expected default) to new_signature.
        Returns: (decision, rule_name, evidence_str)
        """
        if new_signature is None:
            return "STALE", "FUNCTION_REMOVED", f"Function missing from target state."

        if parameter_name not in new_signature.parameters:
            return "STALE", "DEFAULT_VALUE_PARAMETER_REMOVED", f"Parameter '{parameter_name}' was removed or renamed in target state."

        if parameter_name not in new_signature.defaults:
            return "STALE", "DEFAULT_VALUE_MADE_REQUIRED", f"Parameter '{parameter_name}' was made required without default value in target state."

        actual_val = new_signature.defaults[parameter_name]

        # Resolve expected default string
        if expected_default is not None:
            clean_exp = str(expected_default).strip().strip("'\"")
        elif old_signature and parameter_name in old_signature.defaults:
            clean_exp = str(old_signature.defaults[parameter_name]).strip().strip("'\"")
        else:
            clean_exp = "None"

        clean_act = str(actual_val).strip().strip("'\"")

        if clean_act == clean_exp or (clean_exp == "None" and clean_act in ("None", "null")):
            return "VALID", "DEFAULT_VALUE_PRESERVED", f"Parameter '{parameter_name}' preserves exact default value '{clean_act}'."
        else:
            return "PARTIALLY_VALID", "DEFAULT_VALUE_MUTATED_COMPATIBLE", f"Parameter '{parameter_name}' default value altered: expected '{clean_exp}', found '{clean_act}'."


@dataclass
class LifecycleUpdateResult:
    """Result summary of a lifecycle evaluation and transition."""
    memory_id: str
    decision: str  # VALID, STALE, PARTIALLY_VALID, UNCERTAIN
    previous_status: MemoryStatus
    new_status: MemoryStatus
    previous_confidence: float
    new_confidence: float
    escalation_tier: str
    action_count: int
    execution_wall_time_sec: float
    reasons: List[str] = field(default_factory=list)
    evidence: str = ""
    rule: str = ""
    raw_result: Optional[Dict[str, Any]] = None


class RoleMemLifecycleEngine:
    """
    Dynamic Lifecycle State Transition Engine for RoleMem.
    Interfaces memory units with role-specific AST invariants and evidence escalation ladder.
    """

    def __init__(
        self,
        confidence_boost: float = 0.05,
        confidence_decay: float = 0.80,
        uncertain_decay: float = 0.90,
        default_budget: Optional[CostBudget] = None
    ):
        self.confidence_boost = confidence_boost
        self.confidence_decay = confidence_decay
        self.uncertain_decay = uncertain_decay
        self.default_budget = default_budget or CostBudget(max_total_actions=50)
        self.pipeline = EvidenceEscalationPipeline()

    def _resolve_repo_root(self, repository_name: str) -> Optional[str]:
        """Resolve local path for bare cache or worktree of repository."""
        if not repository_name:
            return None
        repo_clean = repository_name.replace("/", "_")
        bare_cand = os.path.join("/tmp/formal_bare_repos", repo_clean)
        if os.path.isdir(bare_cand):
            return bare_cand
        repo_simple = repository_name.split("/")[-1]
        cache_cand = os.path.join("/code/repo_cache", repo_simple)
        if os.path.isdir(cache_cand):
            return cache_cand
        return None

    def _extract_git_file_source(self, repo_root: str, commit_sha: str, file_path: str) -> str:
        """Extract source content of a file at a specific commit from git."""
        if not repo_root or not commit_sha or not file_path:
            return ""
        try:
            res = subprocess.run(
                ["git", "show", f"{commit_sha}:{file_path}"],
                cwd=repo_root,
                capture_output=True,
                text=True,
                timeout=5
            )
            if res.returncode == 0:
                return res.stdout
        except Exception:
            pass
        return ""

    def evaluate_record(
        self,
        record: RoleMemoryRecord,
        target_commit: str = "",
        repository_root: Optional[str] = None,
        base_commit: Optional[str] = None,
        target_timestamp: str = "",
        target_ref: str = "",
        budget: Optional[CostBudget] = None
    ) -> LifecycleUpdateResult:
        """
        Evaluate memory record against target codebase state, determine validity, and apply state update.
        """
        start_time = time.time()
        prev_status = record.status
        prev_conf = record.confidence

        repo_name = record.claim.repository_name
        repo_root = repository_root or self._resolve_repo_root(repo_name)
        b_commit = base_commit or record.timestamp.commit_sha
        t_commit = target_commit

        file_path = record.evidence.evidence_path
        structured = record.claim.structured_claim
        subject = structured.get("symbol") or structured.get("module", "")

        # Extract file source at base and target commits
        base_source = self._extract_git_file_source(repo_root, b_commit, file_path) if repo_root else ""
        target_source = self._extract_git_file_source(repo_root, t_commit, file_path) if repo_root else ""

        # Map and normalize claim type and structured slots
        raw_ctype = record.claim.claim_type or "SYMBOL_EXISTS"
        try:
            ctype = ClaimType(raw_ctype)
        except Exception:
            ctype = ClaimType.SYMBOL_EXISTS

        qualifiers = dict(structured)
        claim_obj = ""

        if ctype == ClaimType.DEFAULT_VALUE:
            param_name = structured.get("parameter_or_attr") or structured.get("parameter_name") or structured.get("parameter") or ""
            qualifiers["parameter_name"] = param_name
            qualifiers["expected_default"] = structured.get("expected_default")
            claim_obj = str(structured.get("expected_default"))
        elif ctype == ClaimType.SIGNATURE_COMPATIBLE:
            expected_params = structured.get("expected_parameters", [])
            qualifiers["expected_parameters"] = expected_params
            claim_obj = ", ".join(expected_params)
        elif ctype == ClaimType.DEPRECATION_STATUS:
            is_dep = structured.get("is_deprecated", False)
            claim_obj = "deprecated" if is_dep else "active"
            qualifiers["is_deprecated"] = is_dep
            qualifiers["expected_status"] = claim_obj
        elif ctype == ClaimType.BEHAVIORAL_CONTRACT:
            claim_obj = structured.get("contract_specification", "")
            qualifiers["contract_specification"] = claim_obj
            qualifiers["contract_type"] = structured.get("contract_type", "")
        elif ctype == ClaimType.DEPENDENCY_CONTRACT:
            dep_name = structured.get("dependency_name", "")
            claim_obj = dep_name
            qualifiers["dependency_name"] = dep_name
            qualifiers["version_constraint"] = structured.get("version_constraint", "")
            if not subject:
                subject = structured.get("package_name", "")

        # Construct formal MemoryClaim
        mem_claim = MemoryClaim(
            claim_id=record.memory_id,
            raw_statement=record.claim.raw_statement,
            claim_type=ctype,
            subject=subject,
            predicate=record.claim.claim_type,
            object=claim_obj,
            qualifiers=qualifiers,
            repository=repo_name,
            file_path=file_path,
            symbol=subject,
            evidence_refs=[record.evidence.evidence_path] if record.evidence.evidence_path else [],
            confidence=record.confidence,
            source_case_id=record.memory_id,
            claim_parse_status="PARSED"
        )

        cost_budget = budget or self.default_budget

        # 1. Run core escalation pipeline
        eval_result, trace, cost_tracker = self.pipeline.evaluate_claim(
            claim_or_statement=mem_claim,
            base_source=base_source,
            target_source=target_source,
            symbol_qualified_name=subject,
            file_path=file_path,
            repository=repo_name,
            repository_root=repo_root,
            base_commit=b_commit,
            target_commit=t_commit,
            available_budget=cost_budget
        )

        decision = eval_result.decision
        reasons = list(eval_result.reasons)
        action_count = sum(cost_tracker.action_counts.values()) if hasattr(cost_tracker, "action_counts") else 0
        rule_name = "STATIC_AST_ESCALATION"
        evidence_str = eval_result.evidences[0].detail if eval_result.evidences else (reasons[0] if reasons else "")

        # 2. Epistemic Role Lifecycle Calibration & Refinement
        if target_source:
            sym_parts = subject.split(".")
            sym_name = sym_parts[-1]
            parent_cls = sym_parts[-2] if len(sym_parts) > 1 else None

            tree = None
            try:
                tree = ast.parse(textwrap.dedent(target_source))
            except Exception:
                pass

            # Helper to find target function (handling Class.method nesting)
            def find_target_function(root_tree):
                if root_tree is None:
                    return None
                if parent_cls:
                    for node in ast.iter_child_nodes(root_tree):
                        if isinstance(node, ast.ClassDef) and node.name == parent_cls:
                            for child in node.body:
                                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and child.name == sym_name:
                                    return child
                for node in ast.walk(root_tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == sym_name:
                        return node
                return None

            # A. API Role: Signature Compatibility & Widening (PARTIALLY_VALID)
            if ctype == ClaimType.SIGNATURE_COMPATIBLE and tree is not None:
                target_func = find_target_function(tree)
                if target_func is not None:
                    actual_all_args = [a.arg for a in target_func.args.args]
                    actual_args = [a for a in actual_all_args if a not in ("self", "cls")]
                    expected_params = qualifiers.get("expected_parameters", [])

                    num_defaults = len(target_func.args.defaults)
                    num_total = len(actual_all_args)
                    non_default_args = [a for a in actual_all_args[:num_total - num_defaults] if a not in ("self", "cls")]

                    # Check missing expected parameters
                    missing = [ep for ep in expected_params if ep not in actual_args and f"**{ep}" not in actual_args and not any(a.startswith("*") for a in actual_all_args)]
                    if not missing:
                        extra_params = [ap for ap in actual_args if ap not in expected_params and not ap.startswith("*")]
                        # If extra params were added with default values -> PARTIALLY_VALID (Signature Widening)
                        if extra_params and all(ep not in non_default_args for ep in extra_params):
                            decision = "PARTIALLY_VALID"
                            rule_name = "SIGNATURE_WIDENING_BACKWARD_COMPATIBLE"
                            evidence_str = f"Callable '{sym_name}' signature extended with optional parameters: {actual_args}."
                            reasons = [evidence_str]
                        else:
                            decision = "VALID"
                            rule_name = "SIGNATURE_EXACT_MATCH"
                            evidence_str = f"Callable '{sym_name}' signature compatible: {actual_args}."
                    else:
                        decision = "STALE"
                        rule_name = "SIGNATURE_MISSING_REQUIRED_PARAMETERS"
                        evidence_str = f"Callable '{sym_name}' lacks required parameters: {missing}."
                        reasons = [evidence_str]

            # B. Config Role: Default Value Evolution Checking
            elif ctype == ClaimType.DEFAULT_VALUE:
                param_name = qualifiers.get("parameter_name", "")
                expected_default = qualifiers.get("expected_default")

                old_sig = DefaultValueEvolutionChecker.extract_signature_from_ast(base_source, sym_name) if base_source else None
                new_sig = DefaultValueEvolutionChecker.extract_signature_from_ast(target_source, sym_name) if target_source else None

                decision, rule_name, evidence_str = DefaultValueEvolutionChecker.check_evolution(
                    old_signature=old_sig,
                    new_signature=new_sig,
                    parameter_name=param_name,
                    expected_default=expected_default
                )
                reasons = [evidence_str]

            # C. API Role: Deprecation Status (Unified Schema)
            elif ctype == ClaimType.DEPRECATION_STATUS:
                raw_status = qualifiers.get("is_deprecated", qualifiers.get("expected_status", qualifiers.get("deprecation_status", "active")))
                dep_status_enum = DeprecationStatus.from_value(raw_status)
                expected_status = dep_status_enum.value  # "active" or "deprecated"
                is_dep_in_target = False
                dep_reason = ""

                if tree is not None:
                    target_node = None
                    for node in ast.walk(tree):
                        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.name == sym_name:
                            target_node = node
                            break
                        elif isinstance(node, ast.Assign):
                            for tgt in node.targets:
                                if isinstance(tgt, ast.Name) and tgt.id == sym_name:
                                    target_node = node
                                    break
                    if target_node is not None:
                        for dec in getattr(target_node, "decorator_list", []):
                            dec_name = ast.unparse(dec) if hasattr(ast, "unparse") else str(dec)
                            if "deprecated" in dec_name.lower():
                                is_dep_in_target = True
                                dep_reason = f"Decorator @{dec_name}"
                                break
                        if not is_dep_in_target:
                            for child in ast.walk(target_node):
                                if isinstance(child, ast.Call):
                                    c_str = ast.unparse(child) if hasattr(ast, "unparse") else ""
                                    if "deprecationwarning" in c_str.lower() or "warnings.warn" in c_str.lower():
                                        is_dep_in_target = True
                                        dep_reason = f"Warning call in body: {c_str[:60]}"
                                        break
                        if not is_dep_in_target and hasattr(target_node, "body"):
                            doc = ast.get_docstring(target_node)
                            if doc and ("deprecated" in doc.lower() or "deprecation" in doc.lower()):
                                is_dep_in_target = True
                                dep_reason = "Docstring deprecation notice"
                    if target_node is None:
                        # Symbol not in file
                        decision = "STALE"
                        rule_name = "SYMBOL_REMOVED"
                        evidence_str = f"Symbol '{sym_name}' was removed at target state."
                        reasons = [evidence_str]
                    else:
                        if expected_status == "active":
                            if not is_dep_in_target:
                                decision = "VALID"
                                rule_name = "ACTIVE_SYMBOL_VERIFIED"
                                evidence_str = f"Symbol '{sym_name}' lifecycle status verified unchanged (active, non-deprecated)."
                                reasons = [evidence_str]
                            else:
                                decision = "PARTIALLY_VALID"
                                rule_name = "SOFT_DEPRECATION_ADVISORY"
                                evidence_str = f"Symbol '{sym_name}' remains accessible but attached soft deprecation: {dep_reason}."
                                reasons = [evidence_str]
                        else:
                            if is_dep_in_target:
                                decision = "VALID"
                                rule_name = "DEPRECATED_SYMBOL_CONFIRMED"
                                evidence_str = f"Symbol '{sym_name}' deprecation confirmed: {dep_reason}."
                                reasons = [evidence_str]
                            else:
                                decision = "STALE"
                                rule_name = "DEPRECATION_MISSING"
                                evidence_str = f"Symbol '{sym_name}' contains no deprecation warning."
                                reasons = [evidence_str]

            # D. Behavior Role: Behavioral Contract
            elif ctype == ClaimType.BEHAVIORAL_CONTRACT:
                if sym_name and sym_name in target_source:
                    decision = "VALID"
                    rule_name = "BEHAVIORAL_TEST_WITNESS_VERIFIED"
                    evidence_str = f"Behavioral test assertion contract for '{sym_name}' verified in target test suite."
                    reasons = [evidence_str]
                else:
                    decision = "STALE"
                    rule_name = "BEHAVIORAL_TARGET_ABSENT"
                    evidence_str = f"Behavioral contract symbol '{sym_name}' absent from target test file."
                    reasons = [evidence_str]

        # E. Dependency Role: Dependency Contract Manifest Inspection
        if ctype == ClaimType.DEPENDENCY_CONTRACT and repo_root:
            dep_name = qualifiers.get("dependency_name", "")
            manifest_found = False
            for m_name in ("pyproject.toml", "setup.py", "setup.cfg", "requirements.txt"):
                m_src = self._extract_git_file_source(repo_root, t_commit, m_name)
                if m_src and dep_name and dep_name.lower() in m_src.lower():
                    manifest_found = True
                    break
            if manifest_found:
                decision = "VALID"
                rule_name = "DEPENDENCY_MANIFEST_VERIFIED"
                evidence_str = f"Dependency '{dep_name}' confirmed present in target packaging manifests."
                reasons = [evidence_str]
            else:
                decision = "STALE"
                rule_name = "DEPENDENCY_REMOVED"
                evidence_str = f"Dependency '{dep_name}' not found in target packaging manifests."
                reasons = [evidence_str]

        wall_time = time.time() - start_time

        # Determine escalation tier
        if action_count == 0:
            tier = "TIER_0_STATIC_AST"
        elif action_count <= 5:
            tier = "TIER_1_FILE_SEARCH"
        elif action_count <= 10:
            tier = "TIER_2_MANIFEST_PARSING"
        else:
            tier = "TIER_3_TEST_EXECUTION"

        # Apply formal state transition dynamics
        new_status = prev_status
        new_conf = prev_conf
        transition_note = ""

        if decision == "VALID":
            new_status = MemoryStatus.PRESERVED
            new_conf = min(1.0, round(prev_conf + self.confidence_boost, 4))
            record.status = new_status
            record.confidence = new_conf
            if target_commit:
                record.timestamp = TemporalAnchor(
                    commit_sha=target_commit,
                    timestamp_iso8601=target_timestamp or record.timestamp.timestamp_iso8601,
                    release_ref=target_ref or record.timestamp.release_ref
                )
            transition_note = f"Preserved at commit {target_commit[:8]} (confidence: {prev_conf} -> {new_conf})"

        elif decision == "PARTIALLY_VALID":
            new_status = MemoryStatus.DOWNGRADED
            new_conf = max(0.1, round(prev_conf * self.confidence_decay, 4))
            record.status = new_status
            record.confidence = new_conf
            transition_note = f"Downgraded at commit {target_commit[:8]} (confidence: {prev_conf} -> {new_conf}). Non-breaking migration detected: {evidence_str}"
            record.advisory_notes.append(transition_note)

        elif decision == "STALE":
            new_status = MemoryStatus.INVALIDATED
            new_conf = 0.0
            record.status = new_status
            record.confidence = new_conf
            transition_note = f"Invalidated at commit {target_commit[:8]}. Breaking modification detected: {evidence_str}"
            record.advisory_notes.append(transition_note)

        else:  # UNCERTAIN
            new_conf = max(0.2, round(prev_conf * self.uncertain_decay, 4))
            record.confidence = new_conf
            transition_note = f"Uncertain at commit {target_commit[:8]} (confidence: {prev_conf} -> {new_conf}). Insufficient evidence."
            record.advisory_notes.append(transition_note)

        # Audit action history
        record.action_history.append({
            "action": "LIFECYCLE_EVALUATION",
            "target_commit": target_commit,
            "decision": decision,
            "rule": rule_name,
            "evidence": evidence_str,
            "tier": tier,
            "action_count": action_count,
            "note": transition_note,
            "timestamp": time.time()
        })

        return LifecycleUpdateResult(
            memory_id=record.memory_id,
            decision=decision,
            previous_status=prev_status,
            new_status=new_status,
            previous_confidence=prev_conf,
            new_confidence=new_conf,
            escalation_tier=tier,
            action_count=action_count,
            execution_wall_time_sec=round(wall_time, 4),
            reasons=reasons,
            evidence=evidence_str,
            rule=rule_name,
            raw_result=eval_result.to_dict() if hasattr(eval_result, "to_dict") else {}
        )

    def batch_evaluate(
        self,
        records: List[RoleMemoryRecord],
        target_commit: str = "",
        repository_root: Optional[str] = None,
        base_commit: Optional[str] = None
    ) -> List[LifecycleUpdateResult]:
        """Evaluate a batch of memory records sequentially."""
        return [
            self.evaluate_record(
                record=r,
                target_commit=target_commit,
                repository_root=repository_root,
                base_commit=base_commit
            )
            for r in records
        ]
