"""
src/claim_validity/engine.py

Protocol V2.2 Claim-Aware Validity Engine:
- Coordinates Claim Extraction, Grounding, Validation, Impact Tracing, and Evidence Aggregation.
- Enforces strict fail-uncertain guarantees: no internal UNCERTAIN -> VALID conversions.
- Returns rich ClaimEvaluationResult.
"""

from typing import Optional, Dict, Any, List, Union
from .types import (
    ClaimType,
    GroundingStatus,
    ValidationStatus,
    EvidenceType,
    MemoryClaim,
    GroundedClaim,
    ClaimEvidence,
    ClaimImpact,
    ClaimEvaluationResult
)
from .claim_extractor import DeterministicClaimExtractor
from .grounding import ClaimGrounder
from .validators import VALIDATOR_REGISTRY, BaseClaimValidator
from .impact import ASTDependencyImpactTracer
from .evidence import EvidenceAggregator


class ClaimAwareValidityEngine:
    """Core Claim-Aware Memory Validity Evaluator for Protocol V2.2."""

    def __init__(self):
        self.extractor = DeterministicClaimExtractor()
        self.grounder = ClaimGrounder()
        self.impact_tracer = ASTDependencyImpactTracer()
        self.aggregator = EvidenceAggregator()
        self.validators: Dict[ClaimType, BaseClaimValidator] = {
            ctype: vclass() for ctype, vclass in VALIDATOR_REGISTRY.items()
        }

    def evaluate(
        self,
        claim_or_statement: Union[MemoryClaim, str],
        base_source: str = "",
        target_source: str = "",
        diff_hunk: str = "",
        symbol_qualified_name: str = "",
        file_path: str = "",
        repository: str = "",
        repository_root: Optional[str] = None,
        base_commit: Optional[str] = None,
        target_commit: Optional[str] = None,
        dependency_symbols: Optional[List[str]] = None,
        execution_artifact: Optional[Dict[str, Any]] = None,
        source_case_id: Optional[str] = None,
        explicit_metadata: Optional[Dict[str, Any]] = None
    ) -> ClaimEvaluationResult:
        import os
        import subprocess

        # 1. Claim Extraction
        if isinstance(claim_or_statement, MemoryClaim):
            claim = claim_or_statement
        else:
            claim = self.extractor.extract(
                raw_statement=claim_or_statement,
                repository=repository,
                file_path=file_path,
                symbol=symbol_qualified_name,
                source_case_id=source_case_id,
                explicit_metadata=explicit_metadata
            )

        cid = claim.claim_id
        target_file_path = file_path or claim.file_path
        target_repo_name = repository or claim.repository

        if not repository_root and target_repo_name:
            repo_clean = target_repo_name.split("/")[-1]
            cand = os.path.join("/code/repo_cache", repo_clean)
            if os.path.isdir(cand):
                repository_root = cand

        # If repository_root and target_commit are available, load full target file from git history
        if repository_root and target_file_path and target_commit:
            res_git = subprocess.run(
                ["git", "show", f"{target_commit}:{target_file_path}"],
                cwd=repository_root,
                capture_output=True,
                text=True
            )
            if res_git.returncode == 0 and res_git.stdout.strip():
                target_source = res_git.stdout

        if repository_root and target_file_path and base_commit:
            res_base_git = subprocess.run(
                ["git", "show", f"{base_commit}:{target_file_path}"],
                cwd=repository_root,
                capture_output=True,
                text=True
            )
            if res_base_git.returncode == 0 and res_base_git.stdout.strip():
                base_source = res_base_git.stdout

        # If claim could not be parsed deterministically
        if claim.claim_parse_status == "UNRESOLVED" or claim.claim_type == ClaimType.UNKNOWN_CLAIM_TYPE:
            return ClaimEvaluationResult(
                claim_id=cid,
                decision="UNCERTAIN",
                grounding_status=GroundingStatus.UNRESOLVED,
                validation_status=ValidationStatus.INSUFFICIENT_EVIDENCE,
                confidence=0.50,
                evidences=[],
                reasons=[f"Claim statement could not be deterministically parsed into supported claim types."]
            )

        # 2. Claim Grounding
        grounded = self.grounder.ground(
            claim=claim,
            target_source=target_source,
            repository_root=repository_root or "",
            file_path=target_file_path
        )

        all_evidences: List[ClaimEvidence] = []
        validation_status = ValidationStatus.INSUFFICIENT_EVIDENCE

        # 3. Validator Execution
        validator = self.validators.get(claim.claim_type)
        if validator is not None:
            v_status, v_evidences, v_detail = validator.validate(
                grounded_claim=grounded,
                base_source=base_source,
                target_source=target_source,
                diff_hunk=diff_hunk,
                execution_artifact=execution_artifact
            )
            validation_status = v_status
            all_evidences.extend(v_evidences)
        else:
            validation_status = ValidationStatus.INSUFFICIENT_EVIDENCE

        # 4. AST Dependency Impact Tracing
        impact = self.impact_tracer.trace_impact(
            grounded_claim=grounded,
            base_source=base_source,
            target_source=target_source,
            diff_hunk=diff_hunk,
            dependency_symbols=dependency_symbols
        )

        # If downstream AST dependency was broken, record CONTRADICTS evidence
        if impact.dependency_path_changed:
            ev_dep = ClaimEvidence(
                evidence_type=EvidenceType.DEPENDENCY,
                source="ast_dependency_impact",
                claim_id=cid,
                supports_or_contradicts="CONTRADICTS",
                confidence=0.92,
                artifact_hash="",
                detail=f"AST dependency path altered or removed in diff for symbol `{claim.subject}`."
            )
            all_evidences.append(ev_dep)

        # 5. Evidence Aggregation & Decision
        decision, confidence, reasons = self.aggregator.aggregate(
            evidences=all_evidences,
            grounding_status=grounded.grounding_status
        )

        return ClaimEvaluationResult(
            claim_id=cid,
            decision=decision,
            grounding_status=grounded.grounding_status,
            validation_status=validation_status,
            confidence=confidence,
            evidences=all_evidences,
            reasons=reasons,
            impact=impact
        )
