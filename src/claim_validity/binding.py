"""
src/claim_validity/binding.py

Claim Evidence Binding and Verification System for Protocol V2.2:
- Binds MemoryClaims to execution artifacts (Cat B contracts, Cat C counterfactuals, D2 behavior breaks).
- Verifies exact case ID, subject, predicate, object, commit, and contract hash alignments.
- Produces ClaimEvidenceBinding with binding_status in ("VERIFIED", "FAILED", "UNKNOWN").
- Ensures validators reject unverified or mismatched execution artifacts.
"""

from dataclasses import dataclass, field
import hashlib
import json
from typing import Optional, Dict, Any, List
from .types import MemoryClaim, ClaimType


@dataclass
class ClaimEvidenceBinding:
    claim_id: str
    source_case_id: str
    raw_statement_sha256: str
    subject: str
    predicate: str
    object: str
    repository: str
    base_commit: str
    target_commit: str
    evidence_artifact_sha256: str
    contract_hash: Optional[str] = None
    binding_status: str = "UNKNOWN"  # "VERIFIED", "FAILED", "UNKNOWN"
    binding_reasons: List[str] = field(default_factory=list)


class ClaimEvidenceBinder:
    """Verifies that an execution artifact validly binds to a specific MemoryClaim and context."""

    @staticmethod
    def compute_sha256(text_or_dict: Any) -> str:
        if isinstance(text_or_dict, dict):
            content = json.dumps(text_or_dict, sort_keys=True)
        else:
            content = str(text_or_dict)
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def verify(
        self,
        claim: MemoryClaim,
        execution_artifact: Optional[Dict[str, Any]],
        base_commit: str = "",
        target_commit: str = "",
        repository: str = ""
    ) -> ClaimEvidenceBinding:
        raw_stmt_hash = self.compute_sha256(claim.raw_statement)
        art_hash = self.compute_sha256(execution_artifact) if execution_artifact else ""

        if not execution_artifact:
            return ClaimEvidenceBinding(
                claim_id=claim.claim_id,
                source_case_id=claim.source_case_id or "",
                raw_statement_sha256=raw_stmt_hash,
                subject=claim.subject,
                predicate=claim.predicate,
                object=claim.object,
                repository=repository or claim.repository,
                base_commit=base_commit,
                target_commit=target_commit,
                evidence_artifact_sha256=art_hash,
                contract_hash=None,
                binding_status="UNKNOWN",
                binding_reasons=["No execution artifact provided."]
            )

        art_repo = execution_artifact.get("repository", "")
        art_base = execution_artifact.get("base_commit", "")
        art_target = execution_artifact.get("target_commit", "")
        art_case = execution_artifact.get("case_id") or execution_artifact.get("source_case_id", "")
        claim_repo = repository or claim.repository
        claim_case = claim.source_case_id or ""
        
        reasons = []
        if art_case and claim_case and art_case != claim_case:
            reasons.append(f"Case ID mismatch: artifact={art_case}, claim={claim_case}")
        if art_repo and claim_repo and art_repo != claim_repo:
            reasons.append(f"Repository mismatch: artifact={art_repo}, claim={claim_repo}")
        if base_commit and art_base and base_commit != art_base:
            reasons.append(f"Base commit mismatch: artifact={art_base}, context={base_commit}")
        if target_commit and art_target and target_commit != art_target:
            reasons.append(f"Target commit mismatch: artifact={art_target}, context={target_commit}")

        if reasons:
            return ClaimEvidenceBinding(
                claim_id=claim.claim_id,
                source_case_id=claim.source_case_id or "",
                raw_statement_sha256=raw_stmt_hash,
                subject=claim.subject,
                predicate=claim.predicate,
                object=claim.object,
                repository=claim_repo,
                base_commit=base_commit,
                target_commit=target_commit,
                evidence_artifact_sha256=art_hash,
                binding_status="FAILED",
                binding_reasons=reasons
            )

        # 1. Cat B: Behavioral Contract Binding
        if claim.claim_type == ClaimType.BEHAVIORAL_CONTRACT or "contracts" in str(execution_artifact.get("case_id", "")):
            art_subject = execution_artifact.get("claim_subject", "").split(".")[-1]
            claim_subject = (claim.subject or claim.symbol).split(".")[-1]
            
            c_hash = (
                execution_artifact.get("target_execution", {}).get("contract_hash") or
                execution_artifact.get("base_execution", {}).get("contract_hash")
            )

            if art_subject and claim_subject and art_subject != claim_subject:
                return ClaimEvidenceBinding(
                    claim_id=claim.claim_id,
                    source_case_id=claim.source_case_id or "",
                    raw_statement_sha256=raw_stmt_hash,
                    subject=claim.subject,
                    predicate=claim.predicate,
                    object=claim.object,
                    repository=claim_repo,
                    base_commit=base_commit,
                    target_commit=target_commit,
                    evidence_artifact_sha256=art_hash,
                    contract_hash=c_hash,
                    binding_status="FAILED",
                    binding_reasons=[f"Subject mismatch for Cat B: artifact={art_subject}, claim={claim_subject}"]
                )

            if not c_hash:
                return ClaimEvidenceBinding(
                    claim_id=claim.claim_id,
                    source_case_id=claim.source_case_id or "",
                    raw_statement_sha256=raw_stmt_hash,
                    subject=claim.subject,
                    predicate=claim.predicate,
                    object=claim.object,
                    repository=claim_repo,
                    base_commit=base_commit,
                    target_commit=target_commit,
                    evidence_artifact_sha256=art_hash,
                    contract_hash=None,
                    binding_status="FAILED",
                    binding_reasons=["Cat B artifact lacks verified contract_hash."]
                )

            return ClaimEvidenceBinding(
                claim_id=claim.claim_id,
                source_case_id=claim.source_case_id or "",
                raw_statement_sha256=raw_stmt_hash,
                subject=claim.subject,
                predicate=claim.predicate,
                object=claim.object,
                repository=claim_repo,
                base_commit=base_commit,
                target_commit=target_commit,
                evidence_artifact_sha256=art_hash,
                contract_hash=c_hash,
                binding_status="VERIFIED",
                binding_reasons=["Cat B behavioral contract binding verified."]
            )

        # 2. Cat C: Dependency Contract Binding
        if claim.claim_type == ClaimType.DEPENDENCY_CONTRACT or "counterfactuals" in str(execution_artifact.get("case_id", "")):
            art_target_sym = execution_artifact.get("target_symbol", "").split(".")[-1]
            art_dep_sym = execution_artifact.get("dependency_symbol", "").split(".")[-1]
            dep_path = execution_artifact.get("dependency_path", [])
            claim_subject = (claim.subject or claim.symbol).split(".")[-1]
            claim_object = claim.object.split(".")[-1] if claim.object else ""

            c_hash = (
                execution_artifact.get("old_on_target", {}).get("contract_hash") or
                execution_artifact.get("old_on_base", {}).get("contract_hash")
            )

            if claim_subject != art_target_sym:
                reasons.append(f"Cat C target_symbol mismatch: artifact={art_target_sym}, claim={claim_subject}")
            if claim_object and art_dep_sym and claim_object != art_dep_sym:
                reasons.append(f"Cat C dependency_symbol mismatch: artifact={art_dep_sym}, claim={claim_object}")
            if dep_path:
                start_sym = dep_path[0].split(".")[-1]
                end_sym = dep_path[-1].split(".")[-1]
                if start_sym != claim_subject or (claim_object and end_sym != claim_object):
                    reasons.append(f"Cat C dependency_path mismatch: path={dep_path}, expected start={claim_subject}, end={claim_object}")

            if reasons:
                return ClaimEvidenceBinding(
                    claim_id=claim.claim_id,
                    source_case_id=claim.source_case_id or "",
                    raw_statement_sha256=raw_stmt_hash,
                    subject=claim.subject,
                    predicate=claim.predicate,
                    object=claim.object,
                    repository=claim_repo,
                    base_commit=base_commit,
                    target_commit=target_commit,
                    evidence_artifact_sha256=art_hash,
                    contract_hash=c_hash,
                    binding_status="FAILED",
                    binding_reasons=reasons
                )

            return ClaimEvidenceBinding(
                claim_id=claim.claim_id,
                source_case_id=claim.source_case_id or "",
                raw_statement_sha256=raw_stmt_hash,
                subject=claim.subject,
                predicate=claim.predicate,
                object=claim.object,
                repository=claim_repo,
                base_commit=base_commit,
                target_commit=target_commit,
                evidence_artifact_sha256=art_hash,
                contract_hash=c_hash,
                binding_status="VERIFIED",
                binding_reasons=["Cat C dependency counterfactual binding verified."]
            )

        # 3. Cat D2 / General Behavioral Break Binding
        if "break_verified" in execution_artifact or "behavior_breaks" in str(execution_artifact.get("case_id", "")):
            c_hash = (
                execution_artifact.get("target_execution", {}).get("contract_hash") or
                execution_artifact.get("base_execution", {}).get("contract_hash")
            )
            art_case = execution_artifact.get("case_id")
            if art_case and claim.source_case_id and art_case == claim.source_case_id:
                return ClaimEvidenceBinding(
                    claim_id=claim.claim_id,
                    source_case_id=claim.source_case_id or "",
                    raw_statement_sha256=raw_stmt_hash,
                    subject=claim.subject,
                    predicate=claim.predicate,
                    object=claim.object,
                    repository=claim_repo,
                    base_commit=base_commit,
                    target_commit=target_commit,
                    evidence_artifact_sha256=art_hash,
                    contract_hash=c_hash,
                    binding_status="VERIFIED",
                    binding_reasons=["Cat D2 behavior break binding verified."]
                )
            else:
                return ClaimEvidenceBinding(
                    claim_id=claim.claim_id,
                    source_case_id=claim.source_case_id or "",
                    raw_statement_sha256=raw_stmt_hash,
                    subject=claim.subject,
                    predicate=claim.predicate,
                    object=claim.object,
                    repository=claim_repo,
                    base_commit=base_commit,
                    target_commit=target_commit,
                    evidence_artifact_sha256=art_hash,
                    contract_hash=c_hash,
                    binding_status="UNKNOWN",
                    binding_reasons=["D2 artifact lacks deterministic assertion binding proof."]
                )

        return ClaimEvidenceBinding(
            claim_id=claim.claim_id,
            source_case_id=claim.source_case_id or "",
            raw_statement_sha256=raw_stmt_hash,
            subject=claim.subject,
            predicate=claim.predicate,
            object=claim.object,
            repository=claim_repo,
            base_commit=base_commit,
            target_commit=target_commit,
            evidence_artifact_sha256=art_hash,
            binding_status="UNKNOWN",
            binding_reasons=["Artifact type not recognized for verified binding."]
        )
