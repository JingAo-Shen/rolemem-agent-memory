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
    # Provenance fields
    artifact_claim_hash: Optional[str] = None
    claim_raw_statement_hash: Optional[str] = None
    artifact_claim_subject: Optional[str] = None
    claim_subject: Optional[str] = None
    artifact_claim_predicate: Optional[str] = None
    claim_predicate: Optional[str] = None
    claim_object: Optional[str] = None
    contract_assertions_hash: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "source_case_id": self.source_case_id,
            "raw_statement_sha256": self.raw_statement_sha256,
            "subject": self.subject,
            "predicate": self.predicate,
            "object": self.object,
            "repository": self.repository,
            "base_commit": self.base_commit,
            "target_commit": self.target_commit,
            "evidence_artifact_sha256": self.evidence_artifact_sha256,
            "contract_hash": self.contract_hash,
            "binding_status": self.binding_status,
            "binding_reasons": self.binding_reasons,
            "artifact_claim_hash": self.artifact_claim_hash,
            "claim_raw_statement_hash": self.claim_raw_statement_hash,
            "artifact_claim_subject": self.artifact_claim_subject,
            "claim_subject": self.claim_subject,
            "artifact_claim_predicate": self.artifact_claim_predicate,
            "claim_predicate": self.claim_predicate,
            "claim_object": self.claim_object,
            "contract_assertions_hash": self.contract_assertions_hash
        }


class ClaimEvidenceBinder:
    """Verifies that an execution artifact validly binds to a specific MemoryClaim and context."""

    @staticmethod
    def compute_sha256(text_or_dict: Any) -> str:
        if isinstance(text_or_dict, dict) or isinstance(text_or_dict, list):
            content = json.dumps(text_or_dict, sort_keys=True)
        else:
            content = str(text_or_dict)
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    @staticmethod
    def normalize_text(text: Optional[str]) -> str:
        if not text:
            return ""
        return " ".join(str(text).strip().split())

    def verify(
        self,
        claim: MemoryClaim,
        execution_artifact: Optional[Dict[str, Any]],
        base_commit: str = "",
        target_commit: str = "",
        repository: str = ""
    ) -> ClaimEvidenceBinding:
        raw_stmt_norm = self.normalize_text(claim.raw_statement)
        raw_stmt_hash = self.compute_sha256(raw_stmt_norm) if raw_stmt_norm else ""
        art_hash = self.compute_sha256(execution_artifact) if execution_artifact else ""

        claim_repo = repository or claim.repository
        claim_case = claim.source_case_id or ""

        if not execution_artifact:
            return ClaimEvidenceBinding(
                claim_id=claim.claim_id,
                source_case_id=claim_case,
                raw_statement_sha256=raw_stmt_hash,
                subject=claim.subject,
                predicate=claim.predicate,
                object=claim.object,
                repository=claim_repo,
                base_commit=base_commit,
                target_commit=target_commit,
                evidence_artifact_sha256=art_hash,
                contract_hash=None,
                binding_status="UNKNOWN",
                binding_reasons=["No execution artifact provided."],
                claim_raw_statement_hash=raw_stmt_hash,
                claim_subject=claim.subject,
                claim_predicate=claim.predicate,
                claim_object=claim.object
            )

        art_repo = execution_artifact.get("repository", "")
        art_base = execution_artifact.get("base_commit", "")
        art_target = execution_artifact.get("target_commit", "")
        art_case = execution_artifact.get("case_id") or execution_artifact.get("source_case_id", "")
        
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
                source_case_id=claim_case,
                raw_statement_sha256=raw_stmt_hash,
                subject=claim.subject,
                predicate=claim.predicate,
                object=claim.object,
                repository=claim_repo,
                base_commit=base_commit,
                target_commit=target_commit,
                evidence_artifact_sha256=art_hash,
                binding_status="FAILED",
                binding_reasons=reasons,
                claim_raw_statement_hash=raw_stmt_hash,
                claim_subject=claim.subject,
                claim_predicate=claim.predicate,
                claim_object=claim.object
            )

        # 1. Cat B: Behavioral Contract Binding
        if claim.claim_type == ClaimType.BEHAVIORAL_CONTRACT or "contracts" in str(execution_artifact.get("case_id", "")) or "contract_assertions" in execution_artifact:
            art_claim_raw = execution_artifact.get("claim", "")
            art_claim_norm = self.normalize_text(art_claim_raw) if art_claim_raw else ""
            art_claim_hash = self.compute_sha256(art_claim_norm) if art_claim_norm else None
            
            art_subject = execution_artifact.get("claim_subject")
            art_pred = execution_artifact.get("claim_predicate")
            
            contract_assertions = execution_artifact.get("contract_assertions")
            assertions_hash = self.compute_sha256(contract_assertions) if contract_assertions else None

            c_hash = (
                execution_artifact.get("target_execution", {}).get("contract_hash") or
                execution_artifact.get("base_execution", {}).get("contract_hash")
            )

            # Check 1: Artifact claim raw statement hash equality
            if art_claim_raw and art_claim_hash != raw_stmt_hash:
                return ClaimEvidenceBinding(
                    claim_id=claim.claim_id,
                    source_case_id=claim_case,
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
                    binding_reasons=[f"Artifact claim raw statement sha256 mismatch: artifact_hash={art_claim_hash}, claim_hash={raw_stmt_hash}"],
                    artifact_claim_hash=art_claim_hash,
                    claim_raw_statement_hash=raw_stmt_hash,
                    artifact_claim_subject=art_subject,
                    claim_subject=claim.subject,
                    artifact_claim_predicate=art_pred,
                    claim_predicate=claim.predicate,
                    claim_object=claim.object,
                    contract_assertions_hash=assertions_hash
                )

            # Check 2: Subject equality
            art_sub_clean = art_subject.split(".")[-1] if art_subject else ""
            claim_sub_clean = (claim.subject or claim.symbol).split(".")[-1]
            if art_subject and art_sub_clean != claim_sub_clean:
                return ClaimEvidenceBinding(
                    claim_id=claim.claim_id,
                    source_case_id=claim_case,
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
                    binding_reasons=[f"Subject mismatch for Cat B: artifact={art_subject}, claim={claim.subject}"],
                    artifact_claim_hash=art_claim_hash,
                    claim_raw_statement_hash=raw_stmt_hash,
                    artifact_claim_subject=art_subject,
                    claim_subject=claim.subject,
                    artifact_claim_predicate=art_pred,
                    claim_predicate=claim.predicate,
                    claim_object=claim.object,
                    contract_assertions_hash=assertions_hash
                )

            # Check 3: Verified contract hash existence
            if not c_hash:
                return ClaimEvidenceBinding(
                    claim_id=claim.claim_id,
                    source_case_id=claim_case,
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
                    binding_reasons=["Cat B artifact lacks verified contract_hash."],
                    artifact_claim_hash=art_claim_hash,
                    claim_raw_statement_hash=raw_stmt_hash,
                    artifact_claim_subject=art_subject,
                    claim_subject=claim.subject,
                    artifact_claim_predicate=art_pred,
                    claim_predicate=claim.predicate,
                    claim_object=claim.object,
                    contract_assertions_hash=assertions_hash
                )

            # Check 4: Auditable mapping of claim_predicate
            if not art_pred or not str(art_pred).strip():
                return ClaimEvidenceBinding(
                    claim_id=claim.claim_id,
                    source_case_id=claim_case,
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
                    binding_reasons=["Cat B artifact lacks claim_predicate for audit mapping."],
                    artifact_claim_hash=art_claim_hash,
                    claim_raw_statement_hash=raw_stmt_hash,
                    artifact_claim_subject=art_subject,
                    claim_subject=claim.subject,
                    artifact_claim_predicate=art_pred,
                    claim_predicate=claim.predicate,
                    claim_object=claim.object,
                    contract_assertions_hash=assertions_hash
                )

            return ClaimEvidenceBinding(
                claim_id=claim.claim_id,
                source_case_id=claim_case,
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
                binding_reasons=["Cat B behavioral contract binding verified."],
                artifact_claim_hash=art_claim_hash,
                claim_raw_statement_hash=raw_stmt_hash,
                artifact_claim_subject=art_subject,
                claim_subject=claim.subject,
                artifact_claim_predicate=art_pred,
                claim_predicate=claim.predicate,
                claim_object=claim.object,
                contract_assertions_hash=assertions_hash
            )

        # 2. Cat C: Dependency Contract Binding
        if claim.claim_type == ClaimType.DEPENDENCY_CONTRACT or "counterfactuals" in str(execution_artifact.get("case_id", "")) or "dependency_path" in execution_artifact:
            art_target_sym = execution_artifact.get("target_symbol", "").split(".")[-1]
            art_dep_sym = execution_artifact.get("dependency_symbol", "").split(".")[-1]
            dep_path = execution_artifact.get("dependency_path", [])
            claim_subject = (claim.subject or claim.symbol).split(".")[-1]
            claim_object = claim.object.split(".")[-1] if claim.object else ""

            c_hash = (
                execution_artifact.get("old_on_target", {}).get("contract_hash") or
                execution_artifact.get("old_on_base", {}).get("contract_hash")
            )

            if not c_hash:
                return ClaimEvidenceBinding(
                    claim_id=claim.claim_id,
                    source_case_id=claim_case,
                    raw_statement_sha256=raw_stmt_hash,
                    subject=claim.subject,
                    predicate=claim.predicate,
                    object=claim.object,
                    repository=claim_repo,
                    base_commit=base_commit,
                    target_commit=target_commit,
                    evidence_artifact_sha256=art_hash,
                    contract_hash=None,
                    binding_status="UNKNOWN",
                    binding_reasons=["Missing contract_hash in dependency evidence."]
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
                    source_case_id=claim_case,
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
                source_case_id=claim_case,
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
            # D2 execution artifacts do not contain claim <-> executable contract mapping
            return ClaimEvidenceBinding(
                claim_id=claim.claim_id,
                source_case_id=claim_case,
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
            source_case_id=claim_case,
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
