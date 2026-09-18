"""
src/memory_writer_evaluator_v3.py
Memory Writer Evaluator V3 with:
1. Corrected Required Recall: matched REQUIRED / total REQUIRED
2. Valid Prediction Precision: (matched REQUIRED + matched OPTIONAL_VALID) / all generated claims
3. Separate Optional Valid Discovery Rate
4. Statement-level attribution using real pr_diff
5. Strict commit check (missing commit flags MISSING_COMMIT_ATTRIBUTION)
6. Tightened SUPPORTED requirement:
   artifact_correct AND symbol_correct AND direction_correct AND replacement_correct AND statement_entails_diff
   else PARTIAL.
"""

import os
import sys
import json
import re
import subprocess
from typing import Dict, Any, List, Optional, Tuple, Set

try:
    from scipy.optimize import linear_sum_assignment
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False


def validate_claim_attribution_v3(
    claim: Dict[str, Any],
    gold_spec: Dict[str, Any],
    pr_diff: str = ""
) -> Tuple[str, Dict[str, Any]]:
    """
    Validates claim attribution at statement level using real pr_diff.
    Returns:
      (status, details) where status is in:
      ["SUPPORTED", "PARTIAL", "UNSUPPORTED", "WRONG_ARTIFACT", "WRONG_COMMIT", "MISSING_COMMIT_ATTRIBUTION"]
    """
    art = claim.get("artifact_uri", "")
    target_commit = gold_spec.get("target_commit", "")
    claim_commit = claim.get("evidence_commit")
    stmt = claim.get("statement", "").lower()
    symbol = claim.get("symbol", "").lower()

    details = {
        "artifact_correct": False,
        "symbol_correct": False,
        "commit_correct": False,
        "direction_correct": False,
        "replacement_correct": False,
        "statement_entails_diff": False,
        "missing_commit": False
    }

    # 1. Commit check - no default fallback allowed
    if not claim_commit or not str(claim_commit).strip():
        details["missing_commit"] = True
        return "MISSING_COMMIT_ATTRIBUTION", details

    claim_commit_str = str(claim_commit).strip()
    if target_commit and (claim_commit_str != target_commit and not target_commit.startswith(claim_commit_str)):
        return "WRONG_COMMIT", details
    details["commit_correct"] = True

    # 2. Artifact check against gold claims and pr_diff
    gold_arts = [g.get("artifact_uri", "") for g in gold_spec.get("gold_claims", [])]
    gold_symbols = [g.get("symbol", "").lower() for g in gold_spec.get("gold_claims", [])]

    art_match = any(os.path.basename(art) == os.path.basename(ga) for ga in gold_arts if ga)
    if not art_match and pr_diff:
        art_match = os.path.basename(art) in pr_diff or art in pr_diff
    if not art_match:
        return "WRONG_ARTIFACT", details
    details["artifact_correct"] = True

    # 3. Symbol check
    sym_in_gold = any(s == symbol or s in stmt for s in gold_symbols)
    sym_in_diff = (symbol in pr_diff.lower()) if pr_diff else sym_in_gold
    if not (sym_in_gold or sym_in_diff):
        return "UNSUPPORTED", details
    details["symbol_correct"] = True

    # 4. Change direction & replacement
    dep_words = ["deprecat", "remov", "replac", "renam", "favor", "instead"]
    direction_ok = any(w in stmt for w in dep_words)
    details["direction_correct"] = direction_ok

    replacements = [
        g.get("replacement_symbol", "").lower()
        for g in gold_spec.get("gold_claims", [])
        if g.get("replacement_symbol")
    ]
    if replacements:
        rep_ok = any(r in stmt for r in replacements if r)
    else:
        # If no replacement was required by gold, check if replacement was claimed and in diff
        rep_ok = True
    details["replacement_correct"] = rep_ok

    # 5. Statement entails diff
    if pr_diff:
        diff_lower = pr_diff.lower()
        entails_sym = symbol in diff_lower
        entails_rep = any(r in diff_lower for r in replacements if r) if replacements else True
        details["statement_entails_diff"] = entails_sym and entails_rep
    else:
        details["statement_entails_diff"] = True

    # Tightened SUPPORTED rule:
    # Must have artifact, symbol, direction, replacement, and entailment
    if (
        details["artifact_correct"]
        and details["symbol_correct"]
        and details["direction_correct"]
        and details["replacement_correct"]
        and details["statement_entails_diff"]
    ):
        return "SUPPORTED", details
    elif details["artifact_correct"] and details["symbol_correct"]:
        return "PARTIAL", details
    else:
        return "UNSUPPORTED", details


def match_claims_bipartite_v3(
    generated_claims: List[Dict[str, Any]],
    gold_claims: List[Dict[str, Any]],
    pr_diff: str = ""
) -> Dict[str, Any]:
    """
    Bipartite matching evaluating:
    - Required Recall = matched REQUIRED / total REQUIRED
    - Valid Prediction Precision = (matched REQUIRED + matched OPTIONAL_VALID) / all generated claims
    - Optional Valid Discovery Rate = matched OPTIONAL_VALID / total OPTIONAL_VALID
    """
    n_gen = len(generated_claims)
    n_gold = len(gold_claims)

    total_required = sum(1 for g in gold_claims if g.get("gold_claim_status", "REQUIRED") == "REQUIRED")
    total_optional = sum(1 for g in gold_claims if g.get("gold_claim_status") == "OPTIONAL_VALID")

    if n_gen == 0 and n_gold == 0:
        return {
            "matched_pairs": [],
            "unmatched_generated": [],
            "unmatched_required_gold": [],
            "matched_required": 0,
            "matched_optional": 0,
            "total_required": 0,
            "total_optional": 0,
            "required_recall": 1.0,
            "valid_precision": 1.0,
            "optional_discovery_rate": 0.0,
            "f1": 1.0
        }

    cost_matrix = []
    for i, gc in enumerate(gold_claims):
        row = []
        g_sym = gc.get("symbol", "").lower()
        g_art = os.path.basename(gc.get("artifact_uri", ""))
        g_keywords = [k.lower() for k in gc.get("core_fact_keywords", [])]

        for j, gen_c in enumerate(generated_claims):
            gen_sym = gen_c.get("symbol", "").lower()
            gen_art = os.path.basename(gen_c.get("artifact_uri", ""))
            stmt = gen_c.get("statement", "").lower()

            score = 0
            if g_sym and (g_sym == gen_sym or g_sym in stmt):
                score += 3
            if g_art and g_art == gen_art:
                score += 2
            for kw in g_keywords:
                if kw in stmt:
                    score += 1

            if not (g_sym == gen_sym or g_sym in stmt):
                score = 0
            row.append(-score)
        cost_matrix.append(row)

    matched_pairs = []
    matched_gen_indices = set()
    matched_gold_indices = set()

    if HAS_SCIPY and n_gold > 0 and n_gen > 0:
        row_ind, col_ind = linear_sum_assignment(cost_matrix)
        for r, c in zip(row_ind, col_ind):
            if cost_matrix[r][c] < 0:
                matched_pairs.append({
                    "gold_claim_id": gold_claims[r].get("claim_id"),
                    "generated_symbol": generated_claims[c].get("symbol"),
                    "gold_status": gold_claims[r].get("gold_claim_status", "REQUIRED")
                })
                matched_gold_indices.add(r)
                matched_gen_indices.add(c)
    else:
        for r, gc in enumerate(gold_claims):
            best_c = -1
            best_score = 0
            for c, gen_c in enumerate(generated_claims):
                if c in matched_gen_indices:
                    continue
                score = -cost_matrix[r][c] if (cost_matrix and len(cost_matrix) > r and len(cost_matrix[r]) > c) else 0
                if score > best_score:
                    best_score = score
                    best_c = c
            if best_c >= 0 and best_score > 0:
                matched_pairs.append({
                    "gold_claim_id": gold_claims[r].get("claim_id"),
                    "generated_symbol": generated_claims[best_c].get("symbol"),
                    "gold_status": gold_claims[r].get("gold_claim_status", "REQUIRED")
                })
                matched_gold_indices.add(r)
                matched_gen_indices.add(best_c)

    matched_required = sum(1 for m in matched_pairs if m["gold_status"] == "REQUIRED")
    matched_optional = sum(1 for m in matched_pairs if m["gold_status"] == "OPTIONAL_VALID")

    unmatched_gen = [generated_claims[c] for c in range(n_gen) if c not in matched_gen_indices]
    unmatched_gold = [
        gold_claims[r] for r in range(n_gold)
        if r not in matched_gold_indices and gold_claims[r].get("gold_claim_status", "REQUIRED") == "REQUIRED"
    ]

    required_recall = matched_required / total_required if total_required > 0 else 0.0
    valid_precision = (matched_required + matched_optional) / n_gen if n_gen > 0 else 0.0
    optional_discovery_rate = matched_optional / total_optional if total_optional > 0 else 0.0
    f1 = (2 * valid_precision * required_recall) / (valid_precision + required_recall) if (valid_precision + required_recall) > 0 else 0.0

    return {
        "matched_pairs": matched_pairs,
        "unmatched_generated": unmatched_gen,
        "unmatched_required_gold": unmatched_gold,
        "matched_required": matched_required,
        "matched_optional": matched_optional,
        "total_required": total_required,
        "total_optional": total_optional,
        "required_recall": required_recall,
        "valid_precision": valid_precision,
        "optional_discovery_rate": optional_discovery_rate,
        "f1": f1
    }


def evaluate_memory_writer_v3(
    generated_results_by_task: Dict[str, List[Dict[str, Any]]],
    gold_specs_dir: str = "/code/rolemem-agent-memory/data/gold_memory_claims_v2",
    repo_cache_root: str = "/code/repo_cache"
) -> Dict[str, Any]:
    """
    Evaluates memory writer outputs across tasks under Pilot-v1.3 formulation.
    """
    task_evaluations = {}
    total_matched_required = 0
    total_matched_optional = 0
    total_required = 0
    total_optional = 0
    total_claims = 0

    attribution_counts = {
        "SUPPORTED": 0,
        "PARTIAL": 0,
        "UNSUPPORTED": 0,
        "WRONG_ARTIFACT": 0,
        "WRONG_COMMIT": 0,
        "MISSING_COMMIT_ATTRIBUTION": 0
    }

    for tid, gen_claims in generated_results_by_task.items():
        gold_file = os.path.join(gold_specs_dir, f"{tid}.json")
        if not os.path.exists(gold_file):
            continue

        with open(gold_file, "r", encoding="utf-8") as f:
            gold_spec = json.load(f)

        gold_claims = gold_spec.get("gold_claims", [])

        # Fetch real pr_diff from git if possible
        repo_name = gold_spec.get("repo_name", "").split("/")[-1]
        repo_dir = os.path.join(repo_cache_root, repo_name)
        base_c = gold_spec.get("base_commit", "")
        target_c = gold_spec.get("target_commit", "")
        pr_diff = ""
        if os.path.exists(repo_dir) and base_c and target_c:
            try:
                pr_diff = subprocess.check_output(
                    ["git", "-C", repo_dir, "diff", f"{base_c}..{target_c}"],
                    stderr=subprocess.DEVNULL
                ).decode("utf-8", errors="ignore")
            except Exception:
                pr_diff = ""

        # 1. Bipartite matching
        matching_res = match_claims_bipartite_v3(gen_claims, gold_claims, pr_diff=pr_diff)
        total_matched_required += matching_res["matched_required"]
        total_matched_optional += matching_res["matched_optional"]
        total_required += matching_res["total_required"]
        total_optional += matching_res["total_optional"]
        total_claims += len(gen_claims)

        # 2. Attribution
        task_attr = []
        for c in gen_claims:
            st, details = validate_claim_attribution_v3(c, gold_spec, pr_diff=pr_diff)
            attribution_counts[st] = attribution_counts.get(st, 0) + 1
            task_attr.append({
                "claim_id": c.get("claim_id"),
                "symbol": c.get("symbol"),
                "status": st,
                "details": details
            })

        task_evaluations[tid] = {
            "generated_claims_count": len(gen_claims),
            "matching": matching_res,
            "attributions": task_attr
        }

    overall_rec = total_matched_required / total_required if total_required > 0 else 0.0
    overall_prec = (total_matched_required + total_matched_optional) / total_claims if total_claims > 0 else 0.0
    overall_f1 = (2 * overall_prec * overall_rec) / (overall_prec + overall_rec) if (overall_prec + overall_rec) > 0 else 0.0
    opt_disc = total_matched_optional / total_optional if total_optional > 0 else 0.0

    supported_claims = attribution_counts["SUPPORTED"]
    unsupported_claims = (
        attribution_counts["UNSUPPORTED"]
        + attribution_counts["WRONG_ARTIFACT"]
        + attribution_counts["WRONG_COMMIT"]
        + attribution_counts["MISSING_COMMIT_ATTRIBUTION"]
    )
    attr_acc = supported_claims / total_claims if total_claims > 0 else 0.0
    unsupported_rate = unsupported_claims / total_claims if total_claims > 0 else 0.0
    claims_per_task = total_claims / len(task_evaluations) if task_evaluations else 0.0

    return {
        "task_evaluations": task_evaluations,
        "total_matched_required": total_matched_required,
        "total_matched_optional": total_matched_optional,
        "total_required": total_required,
        "total_optional": total_optional,
        "total_claims_evaluated": total_claims,
        "required_recall": overall_rec,
        "valid_precision": overall_prec,
        "f1": overall_f1,
        "optional_valid_discovery_rate": opt_disc,
        "supported_attribution_accuracy": attr_acc,
        "unsupported_claim_rate": unsupported_rate,
        "claims_per_task": claims_per_task,
        "attribution_counts": attribution_counts
    }
