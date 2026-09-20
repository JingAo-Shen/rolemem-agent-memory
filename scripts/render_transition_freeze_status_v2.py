#!/usr/bin/env python3
"""
scripts/render_transition_freeze_status_v2.py
Formal Fail-Closed Freeze Status Evaluation and Evidence Manifest Generator V2.

Requirements:
- Strictly fail-closed: Any missing file or failed check results in TRANSITION_FREEZE_BLOCKED.
- Zero fallback to True.
- Generates data/freeze_evidence_manifest/<tid>.json with cryptographic sha256 digests for all 9 evidence components.
- Outputs data/transition_freeze_status_v2.jsonl.
"""

import os
import sys
import json
import glob
import hashlib
from typing import Dict, Any, Optional

DATA_DIR = "/code/rolemem-agent-memory/data"
SPECS_DIR = os.path.join(DATA_DIR, "specs")
TREE_DIR = os.path.join(DATA_DIR, "tree_manifests")
VERIFIER_DIR = os.path.join(DATA_DIR, "verifier_verdicts")
HIDDEN_DIR = os.path.join(DATA_DIR, "hidden_test_evidence")
MUTATION_DIR = os.path.join(DATA_DIR, "test_strength")
CONTROLS_DIR = os.path.join(DATA_DIR, "fixture_controls")
CAUSAL_DIR = os.path.join(DATA_DIR, "causal_counterfactual")
GT_DIR = os.path.join(DATA_DIR, "ground_truth_audit_v3")
SEMANTIC_V4_DIR = os.path.join(DATA_DIR, "transition_semantic_audit_v4")

MANIFEST_OUT_DIR = os.path.join(DATA_DIR, "freeze_evidence_manifest")
STATUS_OUT_PATH = os.path.join(DATA_DIR, "transition_freeze_status_v2.jsonl")

os.makedirs(MANIFEST_OUT_DIR, exist_ok=True)


def compute_file_sha256(path: str) -> Optional[str]:
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def render_transition_freeze_v2():
    spec_files = sorted(glob.glob(f"{SPECS_DIR}/trans_track_a_*.json"))
    manifest_records = []
    ready_count = 0
    blocked_count = 0

    for spec_p in spec_files:
        with open(spec_p, "r", encoding="utf-8") as f:
            spec = json.load(f)
        tid = spec["transition_id"]

        # Paths
        tree_p = os.path.join(TREE_DIR, f"{tid}.json")
        verif_p = os.path.join(VERIFIER_DIR, f"{tid}.json")
        hidden_p = os.path.join(HIDDEN_DIR, f"{tid}.json")
        mut_p = os.path.join(MUTATION_DIR, f"{tid}.json")
        ctrl_p = os.path.join(CONTROLS_DIR, f"{tid}.json")
        causal_p = os.path.join(CAUSAL_DIR, f"{tid}.json")
        gt_p = os.path.join(GT_DIR, f"{tid}.json")
        sem_p = os.path.join(SEMANTIC_V4_DIR, f"{tid}.json")

        # Hashes (Fail-Closed: None if missing)
        hashes = {
            "spec_sha256": compute_file_sha256(spec_p),
            "tree_manifest_sha256": compute_file_sha256(tree_p),
            "verifier_sha256": compute_file_sha256(verif_p),
            "hidden_test_evidence_sha256": compute_file_sha256(hidden_p),
            "mutation_evidence_sha256": compute_file_sha256(mut_p),
            "controls_evidence_sha256": compute_file_sha256(ctrl_p),
            "causal_evidence_sha256": compute_file_sha256(causal_p),
            "ground_truth_sha256": compute_file_sha256(gt_p),
            "semantic_v4_sha256": compute_file_sha256(sem_p),
        }

        # Detailed Verification Checks (Zero fallback)
        checks = {}

        # 1. Spec
        checks["spec_valid"] = bool(hashes["spec_sha256"] is not None)

        # 2. Tree purity
        if hashes["tree_manifest_sha256"] is not None:
            with open(tree_p) as f:
                td = json.load(f)
            checks["tree_pure"] = bool(td.get("tree_purity_status") == "TREE_PURITY_PASS" or td.get("purity_status") == "PURE")
        else:
            checks["tree_pure"] = False

        # 3. Verifier
        if hashes["verifier_sha256"] is not None:
            with open(verif_p) as f:
                vd = json.load(f)
            checks["verifier_accept"] = bool(vd.get("overall_status") == "ACCEPT" or vd.get("verdict") == "ACCEPT")
        else:
            checks["verifier_accept"] = False

        # 4. Hidden test
        if hashes["hidden_test_evidence_sha256"] is not None:
            with open(hidden_p) as f:
                hd = json.load(f)
            checks["hidden_test_pass"] = bool(hd.get("verification_status") == "PASS" or hd.get("status") == "PASS")
        else:
            checks["hidden_test_pass"] = False

        # 5. Mutation evidence
        if hashes["mutation_evidence_sha256"] is not None:
            with open(mut_p) as f:
                md = json.load(f)
            checks["mutants_killed"] = bool((md.get("audit_status") == "PASS" or md.get("status") == "PASS") and md.get("mutation_kill_rate", 0) >= 1.0)
        else:
            checks["mutants_killed"] = False

        # 6. Controls
        if hashes["controls_evidence_sha256"] is not None:
            with open(ctrl_p) as f:
                cd = json.load(f)
            checks["controls_pass"] = bool(cd.get("status") == "PASS" and cd.get("valid_control_status") == "PASS")
        else:
            checks["controls_pass"] = False

        # 7. Causal counterfactual
        if hashes["causal_evidence_sha256"] is not None:
            with open(causal_p) as f:
                cad = json.load(f)
            checks["causal_pass"] = bool(cad.get("causality_status") == "CAUSAL_PASS" or cad.get("is_causal") is True)
        else:
            checks["causal_pass"] = False

        # 8. Ground truth
        if hashes["ground_truth_sha256"] is not None:
            with open(gt_p) as f:
                gd = json.load(f)
            checks["ground_truth_pass"] = bool(gd.get("overall_status") == "PASS" or gd.get("status") == "PASS")
        else:
            checks["ground_truth_pass"] = False

        # 9. Semantic V4
        if hashes["semantic_v4_sha256"] is not None:
            with open(sem_p) as f:
                sd = json.load(f)
            checks["semantic_v4_pass"] = bool(sd.get("semantic_pass") is True)
            checks["semantic_v4_verdict"] = sd.get("verdict", "REJECT")
        else:
            checks["semantic_v4_pass"] = False
            checks["semantic_v4_verdict"] = "EVIDENCE_MISSING"

        all_checks_passed = all([
            checks["spec_valid"],
            checks["tree_pure"],
            checks["verifier_accept"],
            checks["hidden_test_pass"],
            checks["mutants_killed"],
            checks["controls_pass"],
            checks["causal_pass"],
            checks["ground_truth_pass"],
            checks["semantic_v4_pass"]
        ])

        freeze_status = "TRANSITION_SEED_FREEZE_READY" if all_checks_passed else "TRANSITION_FREEZE_BLOCKED"
        if all_checks_passed:
            ready_count += 1
        else:
            blocked_count += 1

        manifest_entry = {
            "transition_id": tid,
            "freeze_status": freeze_status,
            "evidence_hashes": hashes,
            "checks": checks
        }

        # Write individual manifest
        with open(os.path.join(MANIFEST_OUT_DIR, f"{tid}.json"), "w", encoding="utf-8") as f:
            json.dump(manifest_entry, f, indent=2)

        manifest_records.append({
            "transition_id": tid,
            "repo_name": spec.get("repo_name"),
            "freeze_status": freeze_status,
            "checks_summary": {k: v for k, v in checks.items() if k != "semantic_v4_verdict"},
            "semantic_v4_verdict": checks["semantic_v4_verdict"]
        })

    with open(STATUS_OUT_PATH, "w", encoding="utf-8") as f:
        for r in manifest_records:
            f.write(json.dumps(r) + "\n")

    print(f"=== Freeze Status Evaluation V2 ({len(spec_files)} transitions) ===")
    print(f"  TRANSITION_SEED_FREEZE_READY: {ready_count}/{len(spec_files)} ({ready_count/len(spec_files)*100:.1f}%)")
    print(f"  TRANSITION_FREEZE_BLOCKED:   {blocked_count}/{len(spec_files)} ({blocked_count/len(spec_files)*100:.1f}%)")


if __name__ == "__main__":
    render_transition_freeze_v2()
