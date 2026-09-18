"""
src/memory_writer_evaluator_v2.py
Memory Writer Evaluator V2 with Bipartite One-to-One Matching & Statement-Level Attribution Validation.

Implements:
1. Bipartite one-to-one matching between generated claims and gold claims.
2. Recognition of gold claim status: REQUIRED, OPTIONAL_VALID, NOT_MEMORY_WORTHY.
3. Strict TP, FP, FN calculation:
   - TP = matched pairs
   - FP = unmatched generated claims
   - FN = unmatched REQUIRED gold claims
   - OPTIONAL_VALID claims: if matched, TP++; if unmatched, do NOT count as FN.
4. Statement-level attribution validation:
   - SUPPORTED, PARTIAL, UNSUPPORTED, WRONG_ARTIFACT, WRONG_COMMIT
   - Computes Supported Attribution Accuracy and Unsupported Claim Rate.
"""

import os
import sys
import json
import re
from typing import Dict, Any, List, Optional, Tuple, Set

try:
    from scipy.optimize import linear_sum_assignment
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False


def validate_claim_attribution(claim: Dict[str, Any], gold_spec: Dict[str, Any], pr_diff: str = "") -> Tuple[str, Dict[str, Any]]:
    """
    Validates attribution at statement level:
    - artifact correct
    - symbol correct
    - change direction correct
    - replacement correct
    - statement supported by diff/PR
    - commit correct
    Returns:
      (status, details) where status in:
      ["SUPPORTED", "PARTIAL", "UNSUPPORTED", "WRONG_ARTIFACT", "WRONG_COMMIT"]
    """
    art = claim.get("artifact_uri", "")
    target_commit = gold_spec.get("target_commit", "")
    claim_commit = claim.get("evidence_commit", target_commit)
    stmt = claim.get("statement", "").lower()
    symbol = claim.get("symbol", "").lower()

    details = {
        "artifact_correct": False,
        "symbol_correct": False,
        "commit_correct": False,
        "direction_correct": False,
        "replacement_correct": False,
    }

    # 1. Commit check
    if claim_commit and target_commit and (claim_commit != target_commit and not target_commit.startswith(claim_commit)):
        return "WRONG_COMMIT", details
    details["commit_correct"] = True

    # 2. Artifact check against gold claims
    gold_arts = [g.get("artifact_uri", "") for g in gold_spec.get("gold_claims", [])]
    gold_symbols = [g.get("symbol", "").lower() for g in gold_spec.get("gold_claims", [])]
    
    # Check if artifact matches
    art_match = any(os.path.basename(art) == os.path.basename(ga) for ga in gold_arts) or (art in pr_diff)
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

    # Check replacements
    replacements = [g.get("replacement_symbol", "").lower() for g in gold_spec.get("gold_claims", []) if g.get("replacement_symbol")]
    rep_ok = any(r in stmt for r in replacements if r)
    details["replacement_correct"] = rep_ok

    if details["artifact_correct"] and details["symbol_correct"] and details["direction_correct"] and details["replacement_correct"]:
        return "SUPPORTED", details
    elif details["artifact_correct"] and details["symbol_correct"] and details["direction_correct"]:
        return "SUPPORTED", details
    elif details["artifact_correct"] and details["symbol_correct"]:
        return "PARTIAL", details
    else:
        return "UNSUPPORTED", details


def match_claims_bipartite(
    generated_claims: List[Dict[str, Any]],
    gold_claims: List[Dict[str, Any]],
    pr_diff: str = ""
) -> Dict[str, Any]:
    """
    Bipartite one-to-one matching between generated claims and gold claims.
    """
    n_gen = len(generated_claims)
    n_gold = len(gold_claims)

    if n_gen == 0 and n_gold == 0:
        return {
            "matched_pairs": [],
            "unmatched_generated": [],
            "unmatched_required_gold": [],
            "tp": 0, "fp": 0, "fn": 0,
            "precision": 1.0, "recall": 1.0, "f1": 1.0
        }

    # Similarity matrix
    # cost matrix for minimization: -score
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

            # If symbol doesn't match and no keywords match, score is 0
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
            # If score > 0 (cost < 0)
            if cost_matrix[r][c] < 0:
                matched_pairs.append({
                    "gold_claim_id": gold_claims[r].get("claim_id"),
                    "generated_symbol": generated_claims[c].get("symbol"),
                    "gold_status": gold_claims[r].get("gold_claim_status", "REQUIRED")
                })
                matched_gold_indices.add(r)
                matched_gen_indices.add(c)
    else:
        # Greedy fallback
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

    # Calculate TP, FP, FN
    tp = len(matched_pairs)
    unmatched_gen = [generated_claims[c] for c in range(n_gen) if c not in matched_gen_indices]
    fp = len(unmatched_gen)

    unmatched_gold = [
        gold_claims[r] for r in range(n_gold)
        if r not in matched_gold_indices and gold_claims[r].get("gold_claim_status", "REQUIRED") == "REQUIRED"
    ]
    fn = len(unmatched_gold)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

    return {
        "matched_pairs": matched_pairs,
        "unmatched_generated": unmatched_gen,
        "unmatched_required_gold": unmatched_gold,
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": precision,
        "recall": recall,
        "f1": f1
    }


def evaluate_memory_writer_v2(
    generated_results_by_task: Dict[str, List[Dict[str, Any]]],
    gold_specs_dir: str = "/code/rolemem-agent-memory/data/gold_memory_claims_v2",
    repo_cache_root: str = "/code/repo_cache"
) -> Dict[str, Any]:
    """
    Evaluates memory writer outputs across tasks using one-to-one bipartite matching and attribution validation.
    """
    task_evaluations = {}
    total_tp = 0
    total_fp = 0
    total_fn = 0
    total_claims = 0
    attribution_counts = {
        "SUPPORTED": 0,
        "PARTIAL": 0,
        "UNSUPPORTED": 0,
        "WRONG_ARTIFACT": 0,
        "WRONG_COMMIT": 0
    }

    for tid, gen_claims in generated_results_by_task.items():
        gold_file = os.path.join(gold_specs_dir, f"{tid}.json")
        if not os.path.exists(gold_file):
            continue

        with open(gold_file, "r", encoding="utf-8") as f:
            gold_spec = json.load(f)

        gold_claims = gold_spec.get("gold_claims", [])

        # 1. Bipartite matching
        matching_res = match_claims_bipartite(gen_claims, gold_claims)
        total_tp += matching_res["tp"]
        total_fp += matching_res["fp"]
        total_fn += matching_res["fn"]
        total_claims += len(gen_claims)

        # 2. Statement-level attribution validation
        task_attr = []
        for c in gen_claims:
            st, details = validate_claim_attribution(c, gold_spec)
            attribution_counts[st] = attribution_counts.get(st, 0) + 1
            task_attr.append({"claim_id": c.get("claim_id"), "symbol": c.get("symbol"), "status": st, "details": details})

        task_evaluations[tid] = {
            "generated_claims_count": len(gen_claims),
            "matching": matching_res,
            "attributions": task_attr
        }

    overall_prec = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
    overall_rec = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0
    overall_f1 = (2 * overall_prec * overall_rec) / (overall_prec + overall_rec) if (overall_prec + overall_rec) > 0 else 0.0

    supported_claims = attribution_counts["SUPPORTED"]
    unsupported_claims = attribution_counts["UNSUPPORTED"] + attribution_counts["WRONG_ARTIFACT"] + attribution_counts["WRONG_COMMIT"]
    attr_acc = supported_claims / total_claims if total_claims > 0 else 0.0
    unsupported_rate = unsupported_claims / total_claims if total_claims > 0 else 0.0
    claims_per_task = total_claims / len(task_evaluations) if task_evaluations else 0.0

    return {
        "task_evaluations": task_evaluations,
        "total_tp": total_tp,
        "total_fp": total_fp,
        "total_fn": total_fn,
        "precision": overall_prec,
        "recall": overall_rec,
        "f1": overall_f1,
        "supported_attribution_accuracy": attr_acc,
        "unsupported_claim_rate": unsupported_rate,
        "claims_per_task": claims_per_task,
        "attribution_counts": attribution_counts,
        "total_claims_evaluated": total_claims
    }
