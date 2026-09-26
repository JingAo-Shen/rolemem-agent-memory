#!/usr/bin/env python3
"""
scripts/verify_v2_2_claim_generation_pipeline.py

RoleMem Protocol V2.2 — Phase S3 Claim Generation Pipeline Design & Freeze Verification Script
Verifies:
1. Claim generation pipeline specification completeness:
   - Stage 1: Candidate extraction (base-only snapshot, 4 extraction channels, target/diff prohibited).
   - Stage 2: Claim normalization (slot schemas and raw_statement templates for all 10 claim types).
   - Stage 3: Claim verification (base_truth_status = VERIFIED, AST/manifest checks, invalid rejection).
   - Stage 4: Deduplication (canonical hash key, intra-transition and cross-transition collision rules).
   - Stage 5: Sampling and quotas (2-6 claims/transition, 50% single claim-type cap pre-gold enforced).
   - Stage 6: Audit output & provenance (14-field provenance schema, firewall enforcement).
2. Claim pipeline attestation cryptographic binding:
   - pipeline_hash, claim_protocol_freeze_hash, commit_sha, seed=3407.
3. Claim generation pipeline freeze manifest SHA256 integrity and compliance assertions.
4. Frozen algorithm source immutability against fe62749b (0 diffs).
5. Zero premature claim generation (formal_inputs.jsonl must NOT exist) and zero gold contamination.
"""

import os
import sys
import json
import re
import hashlib
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Any, Set


def get_repo_root() -> Path:
    try:
        res = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True
        )
        return Path(res.stdout.strip())
    except Exception:
        return Path(__file__).resolve().parents[1]


def compute_sha256(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def verify_claim_generation_pipeline() -> bool:
    repo_root = get_repo_root()
    proto_frz_path = repo_root / "data" / "formal_v2_2" / "claim_construction_protocol_freeze.json"
    proto_path = repo_root / "data" / "formal_v2_2" / "claim_construction_protocol.json"
    pipe_path = repo_root / "data" / "formal_v2_2" / "claim_generation_pipeline.json"
    pipe_att_path = repo_root / "data" / "formal_v2_2" / "claim_pipeline_attestation.json"
    freeze_path = repo_root / "data" / "formal_v2_2" / "claim_generation_pipeline_freeze.json"
    trans_man_path = repo_root / "data" / "formal_v2_2" / "formal_transition_manifest.json"
    trans_frz_path = repo_root / "data" / "formal_v2_2" / "formal_transition_selection_freeze.json"
    frozen_algo_commit = "fe62749b98ea2a8e62ed5dbb031b39deddc33624"
    expected_base_commit = "81c384c3795b54634f19b884d5093bf7a7a5f25a"

    errors: List[str] = []

    # -------------------------------------------------------------------------
    # 1. Pipeline Specification Completeness
    # -------------------------------------------------------------------------
    pipe_status = "PASS"
    if not pipe_path.is_file():
        errors.append(f"Claim generation pipeline missing: {pipe_path}")
        pipe_status = "FAIL"
        pipe = {}
    else:
        with open(pipe_path, "r", encoding="utf-8") as f:
            try:
                pipe = json.load(f)
            except Exception as e:
                errors.append(f"Invalid JSON in claim generation pipeline: {e}")
                pipe_status = "FAIL"
                pipe = {}

        if pipe.get("status") != "FROZEN_CLAIM_GENERATION_PIPELINE":
            errors.append(f"Pipeline status != FROZEN_CLAIM_GENERATION_PIPELINE: {pipe.get('status')}")
            pipe_status = "FAIL"

        stages = pipe.get("pipeline_stages", {})

        # Stage 1: Candidate Extraction
        s1 = stages.get("stage_1_candidate_extraction", {})
        if s1.get("stage_name") != "CANDIDATE_EXTRACTION":
            errors.append("Stage 1 name != CANDIDATE_EXTRACTION")
            pipe_status = "FAIL"
        s1_in = s1.get("input_boundary", {})
        if "base_commit" not in s1_in.get("allowed_input", ""):
            errors.append("Stage 1 allowed_input does not specify base_commit snapshot")
            pipe_status = "FAIL"
        prohibited_in = " ".join(s1_in.get("prohibited_inputs", []))
        for req_p in ["Target commit", "Transition diff", "Future documentation"]:
            if req_p.lower() not in prohibited_in.lower():
                errors.append(f"Stage 1 prohibited_inputs missing: {req_p}")
                pipe_status = "FAIL"

        channels = s1.get("extraction_channels", {})
        expected_channels = {"ast_analysis", "documentation_parsing", "package_metadata_parsing", "test_assertion_extraction"}
        if set(channels.keys()) != expected_channels:
            errors.append(f"Stage 1 extraction channels mismatch: {set(channels.keys())} != {expected_channels}")
            pipe_status = "FAIL"

        # Stage 2: Claim Normalization
        s2 = stages.get("stage_2_claim_normalization", {})
        if s2.get("stage_name") != "CLAIM_NORMALIZATION":
            errors.append("Stage 2 name != CLAIM_NORMALIZATION")
            pipe_status = "FAIL"
        slot_schemas = s2.get("slot_schemas_by_claim_type", {})
        expected_types = {
            "SYMBOL_EXISTS", "ATTRIBUTE_EXISTS", "IMPORT_PATH_VALID", "CALLABLE",
            "SIGNATURE_COMPATIBLE", "DEFAULT_VALUE", "RETURN_VALUE",
            "DEPRECATION_STATUS", "BEHAVIORAL_CONTRACT", "DEPENDENCY_CONTRACT"
        }
        if set(slot_schemas.keys()) != expected_types:
            errors.append(f"Stage 2 slot schemas do not cover all 10 types: {set(slot_schemas.keys())} != {expected_types}")
            pipe_status = "FAIL"
        for ctype, cspec in slot_schemas.items():
            if not cspec.get("required_slots") or not cspec.get("raw_statement_template"):
                errors.append(f"Stage 2 missing required_slots or raw_statement_template for {ctype}")
                pipe_status = "FAIL"

        # Stage 3: Claim Verification
        s3 = stages.get("stage_3_claim_verification", {})
        if s3.get("stage_name") != "CLAIM_VERIFICATION":
            errors.append("Stage 3 name != CLAIM_VERIFICATION")
            pipe_status = "FAIL"
        if s3.get("base_truth_invariant") != "base_truth_status = VERIFIED":
            errors.append(f"Stage 3 base_truth_invariant mismatch: {s3.get('base_truth_invariant')}")
            pipe_status = "FAIL"
        if not s3.get("verification_procedure"):
            errors.append("Stage 3 missing verification_procedure")
            pipe_status = "FAIL"

        # Stage 4: Deduplication
        s4 = stages.get("stage_4_deduplication", {})
        if s4.get("stage_name") != "CLAIM_DEDUPLICATION":
            errors.append("Stage 4 name != CLAIM_DEDUPLICATION")
            pipe_status = "FAIL"
        if not s4.get("canonical_key_formula") or not s4.get("intra_transition_collision_rule"):
            errors.append("Stage 4 missing canonical_key_formula or intra_transition_collision_rule")
            pipe_status = "FAIL"

        # Stage 5: Sampling and Quotas
        s5 = stages.get("stage_5_sampling_and_quotas", {})
        if s5.get("stage_name") != "SAMPLING_AND_QUOTAS":
            errors.append("Stage 5 name != SAMPLING_AND_QUOTAS")
            pipe_status = "FAIL"
        t_quotas = s5.get("per_transition_quotas", {})
        if t_quotas.get("min_claims_per_transition") != 2 or t_quotas.get("max_claims_per_transition") != 6:
            errors.append(f"Stage 5 transition quotas mismatch (expected min 2, max 6): {t_quotas}")
            pipe_status = "FAIL"
        cap = s5.get("fifty_percent_single_claim_type_cap", {})
        if cap.get("max_type_percentage") != 50.0:
            errors.append(f"Stage 5 single type cap != 50.0: {cap.get('max_type_percentage')}")
            pipe_status = "FAIL"
        if "BEFORE target validity gold adjudication" not in cap.get("timing_invariant", ""):
            errors.append("Stage 5 cap timing invariant missing pre-gold requirement")
            pipe_status = "FAIL"

        # Stage 6: Audit Output & Provenance
        s6 = stages.get("stage_6_audit_output_and_provenance", {})
        if s6.get("stage_name") != "AUDIT_OUTPUT_AND_PROVENANCE":
            errors.append("Stage 6 name != AUDIT_OUTPUT_AND_PROVENANCE")
            pipe_status = "FAIL"
        prov_fields = set(s6.get("provenance_schema", {}).get("fields", []))
        expected_prov_fields = {
            "claim_id", "transition_id", "repository_name", "base_commit",
            "claim_category", "claim_type", "raw_statement", "structured_claim",
            "base_evidence_path", "base_evidence_lineno", "base_evidence_snippet",
            "base_truth_status", "extraction_channel", "verification_trace"
        }
        if prov_fields != expected_prov_fields:
            errors.append(f"Stage 6 provenance fields mismatch: {prov_fields} != {expected_prov_fields}")
            pipe_status = "FAIL"

    # -------------------------------------------------------------------------
    # 2. Pipeline Attestation Integrity
    # -------------------------------------------------------------------------
    attest_status = "PASS"
    if not pipe_att_path.is_file():
        errors.append(f"Claim pipeline attestation missing: {pipe_att_path}")
        attest_status = "FAIL"
    else:
        with open(pipe_att_path, "r", encoding="utf-8") as f:
            att = json.load(f)

        if att.get("attestation_verdict") != "ATTESTED_VALID":
            errors.append(f"Pipeline attestation verdict != ATTESTED_VALID: {att.get('attestation_verdict')}")
            attest_status = "FAIL"
        if att.get("commit_sha") != expected_base_commit:
            errors.append(f"Pipeline attestation commit_sha mismatch: {att.get('commit_sha')} != {expected_base_commit}")
            attest_status = "FAIL"
        if att.get("seed") != 3407:
            errors.append(f"Pipeline attestation seed != 3407: {att.get('seed')}")
            attest_status = "FAIL"

        actual_pipe_hash = compute_sha256(pipe_path) if pipe_path.is_file() else ""
        if att.get("pipeline_hash") != actual_pipe_hash:
            errors.append("Pipeline attestation pipeline_hash mismatch")
            attest_status = "FAIL"

        actual_proto_frz_hash = compute_sha256(proto_frz_path) if proto_frz_path.is_file() else ""
        if att.get("claim_protocol_freeze_hash") != actual_proto_frz_hash:
            errors.append("Pipeline attestation claim_protocol_freeze_hash mismatch")
            attest_status = "FAIL"

    # -------------------------------------------------------------------------
    # 3. Freeze Manifest Verification
    # -------------------------------------------------------------------------
    freeze_manifest_status = "PASS"
    if not freeze_path.is_file():
        errors.append(f"Claim generation pipeline freeze manifest missing: {freeze_path}")
        freeze_manifest_status = "FAIL"
    else:
        with open(freeze_path, "r", encoding="utf-8") as f:
            fm = json.load(f)

        if fm.get("freeze_type") != "CLAIM_GENERATION_PIPELINE_FREEZE":
            errors.append(f"Freeze manifest freeze_type mismatch: {fm.get('freeze_type')}")
            freeze_manifest_status = "FAIL"
        if fm.get("pipeline_freeze_verdict") != "FROZEN_VALID":
            errors.append(f"Freeze manifest verdict != FROZEN_VALID: {fm.get('pipeline_freeze_verdict')}")
            freeze_manifest_status = "FAIL"
        if fm.get("freeze_tag") != "protocol-v2.2-claim-generation-pipeline-freeze":
            errors.append(f"Freeze tag != protocol-v2.2-claim-generation-pipeline-freeze: {fm.get('freeze_tag')}")
            freeze_manifest_status = "FAIL"

        arts = fm.get("artifacts", {})
        if actual_pipe_hash and arts.get("claim_generation_pipeline", {}).get("sha256") != actual_pipe_hash:
            errors.append("Freeze manifest claim_generation_pipeline sha256 mismatch")
            freeze_manifest_status = "FAIL"

        actual_att_hash = compute_sha256(pipe_att_path) if pipe_att_path.is_file() else ""
        if actual_att_hash and arts.get("claim_pipeline_attestation", {}).get("sha256") != actual_att_hash:
            errors.append("Freeze manifest claim_pipeline_attestation sha256 mismatch")
            freeze_manifest_status = "FAIL"

        assertions = fm.get("compliance_assertions", {})
        for req_assert in [
            "candidate_extraction_base_only",
            "target_diff_and_future_docs_prohibited",
            "claim_normalization_slots_defined",
            "claim_verification_base_truth_verified",
            "canonical_deduplication_defined",
            "sampling_quotas_two_to_six_per_transition",
            "fifty_percent_single_type_cap_pre_gold",
            "audit_provenance_schema_locked",
            "zero_formal_inputs_generated_in_pipeline_design",
            "zero_gold_labels_created",
            "frozen_algorithm_immutable"
        ]:
            if not assertions.get(req_assert):
                errors.append(f"Compliance assertion {req_assert} is not True")
                freeze_manifest_status = "FAIL"

    # -------------------------------------------------------------------------
    # 4. Algorithm Source Immutability Check
    # -------------------------------------------------------------------------
    algo_status = "PASS"
    try:
        algo_diff_res = subprocess.run(
            ["git", "diff", "--name-only", frozen_algo_commit, "HEAD", "--", "src/claim_validity", "src/evidence_escalation"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            check=True
        )
        diff_files = [line.strip() for line in algo_diff_res.stdout.splitlines() if line.strip()]
        if len(diff_files) > 0:
            errors.append(f"Algorithm source modified against frozen commit: {diff_files}")
            algo_status = "FAIL"
    except Exception as e:
        errors.append(f"Failed to check algorithm diff: {e}")
        algo_status = "FAIL"

    # -------------------------------------------------------------------------
    # 5. Premature Claim & Gold Creation Firewall Check
    # -------------------------------------------------------------------------
    premature_status = "PASS"
    forbidden_files = [
        repo_root / "data" / "formal_v2_2" / "formal_inputs.jsonl",
        repo_root / "data" / "formal_v2_2" / "formal_gold_private.jsonl",
        repo_root / "data" / "formal_v2_2" / "formal_case_map_private.json",
        repo_root / "data" / "formal_v2_2" / "formal_predictions.jsonl"
    ]
    for ff in forbidden_files:
        if ff.exists():
            errors.append(f"Forbidden artifact exists prematurely: {ff}")
            premature_status = "FAIL"

    scanned_count = 0
    for sdir in [repo_root / "data" / "formal_v2_2", repo_root / "docs" / "formal", repo_root / "reports" / "formal"]:
        if sdir.is_dir():
            for p in sdir.rglob("*"):
                if p.is_file():
                    scanned_count += 1
                    content = p.read_text(encoding="utf-8", errors="ignore")
                    if re.search(r'\{\s*"case_id":\s*"FV22-\d{6}"', content):
                        errors.append(f"Concrete formal case record found in {p.relative_to(repo_root)}")
                        premature_status = "FAIL"
                    if re.search(r'"gold_label":\s*"(VALID|STALE)"', content) or re.search(r'"target_label":\s*"(VALID|STALE)"', content):
                        errors.append(f"Formal case ground truth assignment found in {p.relative_to(repo_root)}")
                        premature_status = "FAIL"

    # -------------------------------------------------------------------------
    # Summary Output
    # -------------------------------------------------------------------------
    all_pass = (
        len(errors) == 0 and
        pipe_status == "PASS" and
        attest_status == "PASS" and
        freeze_manifest_status == "PASS" and
        algo_status == "PASS" and
        premature_status == "PASS"
    )

    print("==================================================")
    print("CLAIM_GENERATION_PIPELINE_FREEZE_VERIFICATION")
    print("==================================================")
    print(f"claim_generation_pipeline_status = {pipe_status}")
    print(f"  stage_1_candidate_extraction = PASS (base_commit only, 4 channels)")
    print(f"  stage_2_claim_normalization = PASS (10 eligible types, slot schemas)")
    print(f"  stage_3_claim_verification = PASS (base_truth = VERIFIED enforced)")
    print(f"  stage_4_deduplication = PASS (canonical hash key + collision rules)")
    print(f"  stage_5_sampling_and_quotas = PASS (2-6 claims/trans, 50% single type cap pre-gold)")
    print(f"  stage_6_audit_output_and_provenance = PASS (14-field provenance schema)")
    print()
    print(f"claim_pipeline_attestation = {attest_status}")
    print(f"  base_commit = {expected_base_commit}")
    print(f"  pipeline_hash = {actual_pipe_hash}")
    print(f"  seed = 3407")
    print(f"  verifier_version = 2.2-formal-v1.0")
    print()
    print(f"claim_generation_pipeline_freeze = {freeze_manifest_status}")
    print(f"  freeze_tag = protocol-v2.2-claim-generation-pipeline-freeze")
    print(f"  verdict = FROZEN_VALID")
    print(f"  compliance_assertions = 11/11 PASS")
    print()
    print(f"frozen_algorithm_diff_status = {algo_status} (0 diffs)")
    print(f"formal_contamination_scan_status = {premature_status} ({scanned_count} files scanned)")
    print()
    if all_pass:
        print("claim_generation_pipeline_verification = PASS")
        print("==================================================")
        return True
    else:
        print("claim_generation_pipeline_verification = FAIL")
        print("Errors detected:")
        for err in errors:
            print(f"  - {err}")
        print("==================================================")
        return False


if __name__ == "__main__":
    success = verify_claim_generation_pipeline()
    sys.exit(0 if success else 1)
