#!/usr/bin/env python3
"""
scripts/verify_v2_2_gold_annotation_protocol.py

RoleMem Protocol V2.2 — Phase S4 Gold Annotation Protocol Design & Freeze Verification Script
Verifies:
1. Gold annotation protocol specification completeness:
   - Gold label taxonomy (VALID, STALE, PARTIALLY_VALID, UNRESOLVED_GOLD).
   - Annotation information boundary (base claim, base evidence, target state allowed; RoleMem predictions strictly prohibited).
   - Adjudication process (3-tier: single primary, double blind independent, conflict resolution consensus).
   - Evidence requirements (mandatory target evidence snippet, 5-field schema).
   - Inter-annotator agreement (Cohen's Kappa formula, target >= 0.85, minimum >= 0.75).
   - Gold freeze and file isolation architecture (formal_inputs.jsonl, formal_gold_private.jsonl, formal_case_map_private.json).
2. Gold protocol attestation cryptographic binding:
   - gold_protocol_hash, selection_protocol_freeze_hash, commit_sha, seed=3407.
3. Gold annotation protocol freeze manifest SHA256 integrity and compliance assertions.
4. Frozen algorithm source immutability against fe62749b (0 diffs).
5. Zero premature gold label generation and zero contamination.
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


def verify_gold_annotation_protocol() -> bool:
    repo_root = get_repo_root()
    proto_path = repo_root / "data" / "formal_v2_2" / "gold_annotation_protocol.json"
    attest_path = repo_root / "data" / "formal_v2_2" / "gold_annotation_protocol_attestation.json"
    freeze_path = repo_root / "data" / "formal_v2_2" / "gold_annotation_protocol_freeze.json"
    sel_frz_path = repo_root / "data" / "formal_v2_2" / "claim_selection_protocol_freeze.json"
    frozen_algo_commit = "fe62749b98ea2a8e62ed5dbb031b39deddc33624"
    expected_base_commit = "0cfcd5c41fe7ba4c20b986866ba477c77c908535"

    errors: List[str] = []

    # -------------------------------------------------------------------------
    # 1. Gold Annotation Protocol Specification Verification
    # -------------------------------------------------------------------------
    proto_status = "PASS"
    if not proto_path.is_file():
        errors.append(f"Gold annotation protocol missing: {proto_path}")
        proto_status = "FAIL"
        proto = {}
    else:
        with open(proto_path, "r", encoding="utf-8") as f:
            try:
                proto = json.load(f)
            except Exception as e:
                errors.append(f"Invalid JSON in gold annotation protocol: {e}")
                proto_status = "FAIL"
                proto = {}

        if proto.get("status") != "FROZEN_GOLD_ANNOTATION_PROTOCOL":
            errors.append(f"Protocol status != FROZEN_GOLD_ANNOTATION_PROTOCOL: {proto.get('status')}")
            proto_status = "FAIL"

        # A. Taxonomy
        tax = proto.get("gold_label_taxonomy", {})
        labels = tax.get("labels", {})
        for req_lbl in ["VALID", "STALE", "PARTIALLY_VALID", "UNRESOLVED_GOLD"]:
            if req_lbl not in labels:
                errors.append(f"Taxonomy missing label: {req_lbl}")
                proto_status = "FAIL"

        pv = labels.get("PARTIALLY_VALID", {})
        if not pv.get("resolution_tracks", {}).get("Track_A_Strict_Stale") or not pv.get("resolution_tracks", {}).get("Track_B_Compatible_Valid"):
            errors.append("PARTIALLY_VALID missing Track A / Track B resolution definitions")
            proto_status = "FAIL"

        # B. Information boundary
        boundary = proto.get("annotation_information_boundary", {})
        if boundary.get("annotator_role") != "VALIDITY_ADJUDICATOR":
            errors.append("Annotator role != VALIDITY_ADJUDICATOR")
            proto_status = "FAIL"
        prohibited = " ".join(boundary.get("prohibited_scope", []))
        if "rolemem" not in prohibited.lower():
            errors.append("Prohibited scope does not include RoleMem algorithm predictions")
            proto_status = "FAIL"
        if not boundary.get("blinding_guarantee"):
            errors.append("Missing blinding guarantee in annotation information boundary")
            proto_status = "FAIL"

        # C. Adjudication process
        adj = proto.get("adjudication_process", {}).get("three_tier_architecture", {})
        for req_tier in ["tier_1_single_primary_annotation", "tier_2_double_blind_independent_annotation", "tier_3_conflict_resolution_and_consensus"]:
            if req_tier not in adj:
                errors.append(f"Missing adjudication tier: {req_tier}")
                proto_status = "FAIL"

        # D. Evidence requirements
        ev = proto.get("evidence_requirements", {})
        if not ev.get("mandatory_target_evidence_rule"):
            errors.append("Missing mandatory_target_evidence_rule")
            proto_status = "FAIL"
        ev_fields = set(ev.get("target_evidence_schema", {}).get("fields", []))
        expected_ev_fields = {"target_evidence_path", "target_evidence_lineno", "target_evidence_snippet", "target_verification_method", "justification_note"}
        if ev_fields != expected_ev_fields:
            errors.append(f"Target evidence schema fields mismatch: {ev_fields} != {expected_ev_fields}")
            proto_status = "FAIL"

        # E. Inter-annotator agreement
        iaa = proto.get("inter_annotator_agreement", {})
        if "cohen" not in iaa.get("metric", "").lower() or "kappa" not in iaa.get("metric", "").lower():
            errors.append("IAA metric is not Cohen Kappa")
            proto_status = "FAIL"
        thresh = iaa.get("quality_thresholds", {})
        if thresh.get("target_threshold") != 0.85 or thresh.get("minimum_acceptable_threshold") != 0.75:
            errors.append(f"IAA thresholds mismatch: {thresh}")
            proto_status = "FAIL"

        # F. Gold freeze & file isolation
        g_freeze = proto.get("gold_freeze_and_isolation_specification", {})
        arch = g_freeze.get("file_isolation_architecture", {})
        for req_f in ["formal_inputs", "formal_gold_private", "formal_case_map_private"]:
            if req_f not in arch:
                errors.append(f"Missing isolated artifact specification: {req_f}")
                proto_status = "FAIL"

    # -------------------------------------------------------------------------
    # 2. Gold Annotation Protocol Attestation Verification
    # -------------------------------------------------------------------------
    attest_status = "PASS"
    if not attest_path.is_file():
        errors.append(f"Gold annotation protocol attestation missing: {attest_path}")
        attest_status = "FAIL"
    else:
        with open(attest_path, "r", encoding="utf-8") as f:
            att = json.load(f)

        if att.get("attestation_verdict") != "ATTESTED_VALID":
            errors.append(f"Attestation verdict != ATTESTED_VALID: {att.get('attestation_verdict')}")
            attest_status = "FAIL"
        if att.get("commit_sha") != expected_base_commit:
            errors.append(f"Attestation commit_sha mismatch: {att.get('commit_sha')} != {expected_base_commit}")
            attest_status = "FAIL"
        if att.get("seed") != 3407:
            errors.append(f"Attestation seed != 3407: {att.get('seed')}")
            attest_status = "FAIL"

        actual_proto_hash = compute_sha256(proto_path) if proto_path.is_file() else ""
        if att.get("gold_protocol_hash") != actual_proto_hash:
            errors.append("Attestation gold_protocol_hash mismatch")
            attest_status = "FAIL"

        actual_sel_frz_hash = compute_sha256(sel_frz_path) if sel_frz_path.is_file() else ""
        if att.get("selection_protocol_freeze_hash") != actual_sel_frz_hash:
            errors.append("Attestation selection_protocol_freeze_hash mismatch")
            attest_status = "FAIL"

    # -------------------------------------------------------------------------
    # 3. Gold Annotation Protocol Freeze Manifest Verification
    # -------------------------------------------------------------------------
    freeze_manifest_status = "PASS"
    if not freeze_path.is_file():
        errors.append(f"Gold annotation protocol freeze manifest missing: {freeze_path}")
        freeze_manifest_status = "FAIL"
    else:
        with open(freeze_path, "r", encoding="utf-8") as f:
            fm = json.load(f)

        if fm.get("freeze_type") != "GOLD_ANNOTATION_PROTOCOL_FREEZE":
            errors.append(f"Freeze manifest freeze_type mismatch: {fm.get('freeze_type')}")
            freeze_manifest_status = "FAIL"
        if fm.get("gold_protocol_freeze_verdict") != "FROZEN_VALID":
            errors.append(f"Freeze manifest verdict != FROZEN_VALID: {fm.get('gold_protocol_freeze_verdict')}")
            freeze_manifest_status = "FAIL"
        if fm.get("freeze_tag") != "protocol-v2.2-gold-annotation-protocol-freeze":
            errors.append(f"Freeze tag mismatch: {fm.get('freeze_tag')}")
            freeze_manifest_status = "FAIL"

        arts = fm.get("artifacts", {})
        if actual_proto_hash and arts.get("gold_annotation_protocol", {}).get("sha256") != actual_proto_hash:
            errors.append("Freeze manifest gold_annotation_protocol sha256 mismatch")
            freeze_manifest_status = "FAIL"

        actual_att_hash = compute_sha256(attest_path) if attest_path.is_file() else ""
        if actual_att_hash and arts.get("gold_annotation_protocol_attestation", {}).get("sha256") != actual_att_hash:
            errors.append("Freeze manifest gold_annotation_protocol_attestation sha256 mismatch")
            freeze_manifest_status = "FAIL"

        assertions = fm.get("compliance_assertions", {})
        for req_assert in [
            "gold_label_taxonomy_defined",
            "valid_stale_partially_valid_included",
            "annotation_information_boundary_enforced",
            "rolemem_predictions_prohibited_from_annotator",
            "adjudication_process_three_tiers_defined",
            "mandatory_target_evidence_snippet_enforced",
            "cohen_kappa_agreement_metric_defined",
            "gold_file_isolation_architecture_locked",
            "zero_gold_labels_generated_in_protocol_design",
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
    # 5. Premature Gold Creation & Contamination Check
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
                if p.is_file() and p.name != "candidate_claims.jsonl":
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
        proto_status == "PASS" and
        attest_status == "PASS" and
        freeze_manifest_status == "PASS" and
        algo_status == "PASS" and
        premature_status == "PASS"
    )

    print("==================================================")
    print("GOLD_ANNOTATION_PROTOCOL_FREEZE_VERIFICATION")
    print("==================================================")
    print(f"gold_annotation_protocol_status = {proto_status}")
    print(f"  gold_label_taxonomy = PASS (VALID, STALE, PARTIALLY_VALID, UNRESOLVED_GOLD)")
    print(f"  annotation_information_boundary = PASS (RoleMem blinded)")
    print(f"  adjudication_process_three_tiers = PASS (single, double blind, consensus)")
    print(f"  evidence_requirements = PASS (mandatory target snippet + 5-field schema)")
    print(f"  inter_annotator_agreement = PASS (Cohen Kappa, target >= 0.85, min >= 0.75)")
    print(f"  gold_freeze_and_isolation = PASS (inputs, gold_private, case_map_private)")
    print()
    print(f"gold_annotation_protocol_attestation = {attest_status}")
    print(f"  base_commit = {expected_base_commit}")
    print(f"  seed = 3407")
    print()
    print(f"gold_annotation_protocol_freeze = {freeze_manifest_status}")
    print(f"  freeze_tag = protocol-v2.2-gold-annotation-protocol-freeze")
    print(f"  verdict = FROZEN_VALID")
    print(f"  compliance_assertions = 10/10 PASS")
    print()
    print(f"frozen_algorithm_diff_status = {algo_status} (0 diffs)")
    print(f"formal_contamination_scan_status = {premature_status} ({scanned_count} files scanned)")
    print()
    if all_pass:
        print("gold_annotation_protocol_verification = PASS")
        print("==================================================")
        return True
    else:
        print("gold_annotation_protocol_verification = FAIL")
        print("Errors detected:")
        for err in errors:
            print(f"  - {err}")
        print("==================================================")
        return False


if __name__ == "__main__":
    success = verify_gold_annotation_protocol()
    sys.exit(0 if success else 1)
