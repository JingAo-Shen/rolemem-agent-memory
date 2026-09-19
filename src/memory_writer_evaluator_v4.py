"""
src/memory_writer_evaluator_v4.py
Memory Writer Evaluator V4 for RoleMem.

Key Features:
1. Symbol Normalization: Handles fully qualified vs unqualified symbols
   (e.g., requests.adapters.HTTPAdapter vs HTTPAdapter, click.testing.isolated_filesystem vs isolated_filesystem).
2. Structural Attribution Consistency: Verifies artifact path/basename, commit hash matching,
   and symbol presence in diff hunks.
3. Semantic Entailment Judge: Verifies statement semantic direction (deprecation/removal/replacement)
   and diff-level entailment against ground truth.
4. Comprehensive Metrics:
   - Required Recall = matched REQUIRED / total REQUIRED
   - Valid Prediction Precision = (matched REQUIRED + matched OPTIONAL_VALID) / all generated claims
   - F1 Score
   - Optional Valid Discovery Rate = matched OPTIONAL_VALID / total OPTIONAL_VALID
   - Supported Attribution Accuracy = count(SUPPORTED) / total claims
   - Unsupported Claim Rate = count(UNSUPPORTED + WRONG_*) / total claims
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


def normalize_symbol(sym: Optional[str]) -> str:
    """Normalizes a symbol name by stripping whitespace, call syntax, and resolving qualifiers."""
    if not sym:
        return ""
    clean = sym.strip().rstrip("()")
    clean = re.sub(r"^[\"']|[\"']$", "", clean)
    return clean


def get_short_symbol(sym: Optional[str]) -> str:
    """Extracts the unqualified identifier name (last token in dot-separated path)."""
    norm = normalize_symbol(sym)
    if not norm:
        return ""
    return norm.split(".")[-1]


def symbol_matches(sym1: Optional[str], sym2: Optional[str], statement: str = "") -> bool:
    """Determines if two symbols match, accounting for full vs unqualified forms and statement mentions."""
    s1_norm = normalize_symbol(sym1).lower()
    s2_norm = normalize_symbol(sym2).lower()
    s1_short = get_short_symbol(sym1).lower()
    s2_short = get_short_symbol(sym2).lower()

    if not s1_norm or not s2_norm:
        return False

    # Exact match
    if s1_norm == s2_norm or s1_short == s2_short:
        return True

    # Suffix match (qualified vs unqualified)
    if s1_norm.endswith("." + s2_short) or s2_norm.endswith("." + s1_short):
        return True

    # Check statement mention
    stmt_lower = statement.lower()
    if s1_short and s1_short in stmt_lower and s2_short and s2_short in stmt_lower:
        return True

    return False


def validate_claim_attribution_v4(
    claim: Dict[str, Any],
    gold_spec: Dict[str, Any],
    pr_diff: str = ""
) -> Tuple[str, Dict[str, Any]]:
    """
    Evaluates statement-level and structural attribution against target commit and diff.
    Returns:
      (status, details) where status is in:
      ["SUPPORTED", "PARTIAL", "UNSUPPORTED", "WRONG_ARTIFACT", "WRONG_COMMIT", "MISSING_COMMIT_ATTRIBUTION"]
    """
    art = claim.get("artifact_uri", "")
    target_commit = gold_spec.get("target_commit", "")
    claim_commit = claim.get("evidence_commit")
    stmt = claim.get("statement", "")
    stmt_lower = stmt.lower()
    claim_sym = claim.get("symbol", "")

    details = {
        "artifact_correct": False,
        "symbol_correct": False,
        "commit_correct": False,
        "direction_correct": False,
        "replacement_correct": False,
        "statement_entails_diff": False,
        "missing_commit": False
    }

    # 1. Structural Commit Check
    if not claim_commit or not str(claim_commit).strip():
        details["missing_commit"] = True
        return "MISSING_COMMIT_ATTRIBUTION", details

    claim_commit_str = str(claim_commit).strip()
    if target_commit and (claim_commit_str != target_commit and not target_commit.startswith(claim_commit_str)):
        return "WRONG_COMMIT", details
    details["commit_correct"] = True

    # 2. Structural Artifact Check
    gold_claims = gold_spec.get("gold_claims", [])
    gold_arts = [g.get("artifact_uri", "") for g in gold_claims]

    art_match = any(
        os.path.basename(art) == os.path.basename(ga) or art.endswith(ga) or ga.endswith(art)
        for ga in gold_arts if ga
    )
    if not art_match and pr_diff:
        art_base = os.path.basename(art)
        art_match = (art_base in pr_diff) or (art in pr_diff)

    if not art_match:
        return "WRONG_ARTIFACT", details
    details["artifact_correct"] = True

    # 3. Symbol Normalization & Matching Check
    gold_symbols = [g.get("symbol", "") for g in gold_claims]
    sym_in_gold = any(symbol_matches(claim_sym, gs, stmt) for gs in gold_symbols)

    short_claim_sym = get_short_symbol(claim_sym).lower()
    diff_lower = pr_diff.lower()
    sym_in_diff = (short_claim_sym in diff_lower) if (short_claim_sym and diff_lower) else sym_in_gold

    if not (sym_in_gold or sym_in_diff):
        return "UNSUPPORTED", details
    details["symbol_correct"] = True

    # 4. Semantic Direction Judge
    dep_patterns = [
        r"\bdeprecat", r"\bremov", r"\breplac", r"\brenam",
        r"\bfavor\b", r"\binstead\b", r"\bno longer\b",
        r"\bdisuse\b", r"\buse\s+.*\s+instead\b"
    ]
    direction_ok = any(re.search(pat, stmt_lower) for pat in dep_patterns)
    details["direction_correct"] = direction_ok

    # 5. Replacement Symbol Verification
    replacements = [
        g.get("replacement_symbol", "")
        for g in gold_claims
        if g.get("replacement_symbol")
    ]
    if replacements:
        rep_ok = any(
            get_short_symbol(r).lower() in stmt_lower
            for r in replacements if r
        )
    else:
        rep_ok = True
    details["replacement_correct"] = rep_ok

    # 6. Diff Semantic Entailment
    if pr_diff:
        entails_sym = (short_claim_sym in diff_lower) if short_claim_sym else True
        entails_rep = any(get_short_symbol(r).lower() in diff_lower for r in replacements if r) if replacements else True
        details["statement_entails_diff"] = entails_sym and entails_rep
    else:
        details["statement_entails_diff"] = True

    # Verdict synthesis
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


def match_claims_bipartite_v4(
    generated_claims: List[Dict[str, Any]],
    gold_claims: List[Dict[str, Any]],
    pr_diff: str = ""
) -> Dict[str, Any]:
    """
    Bipartite matching with normalized symbol comparison.
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
        g_sym = gc.get("symbol", "")
        g_art = os.path.basename(gc.get("artifact_uri", ""))
        g_keywords = [k.lower() for k in gc.get("core_fact_keywords", [])]

        for j, gen_c in enumerate(generated_claims):
            gen_sym = gen_c.get("symbol", "")
            gen_art = os.path.basename(gen_c.get("artifact_uri", ""))
            stmt = gen_c.get("statement", "")

            score = 0
            if symbol_matches(g_sym, gen_sym, stmt):
                score += 4
            if g_art and g_art == gen_art:
                score += 2
            for kw in g_keywords:
                if kw in stmt.lower():
                    score += 1

            if not symbol_matches(g_sym, gen_sym, stmt):
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


def evaluate_memory_writer_v4(
    generated_results_by_task: Dict[str, List[Dict[str, Any]]],
    gold_specs_dir: str = "/code/rolemem-agent-memory/data/gold_memory_claims_v2",
    repo_cache_root: str = "/code/repo_cache"
) -> Dict[str, Any]:
    """
    Evaluates Memory Writer across tasks under V4 standards.
    """
    task_evaluations = {}
    total_matched_required = 0
    total_required = 0
    total_matched_optional = 0
    total_optional = 0
    total_claims = 0

    attr_counts = {
        "SUPPORTED": 0,
        "PARTIAL": 0,
        "UNSUPPORTED": 0,
        "WRONG_ARTIFACT": 0,
        "WRONG_COMMIT": 0,
        "MISSING_COMMIT_ATTRIBUTION": 0
    }

    for task_id, claims in generated_results_by_task.items():
        spec_file = os.path.join(gold_specs_dir, f"{task_id}.json")
        if not os.path.exists(spec_file):
            continue

        with open(spec_file, "r", encoding="utf-8") as f:
            gold_spec = json.load(f)

        gold_claims = gold_spec.get("gold_claims", [])
        base_commit = gold_spec.get("base_commit", "")
        target_commit = gold_spec.get("target_commit", "")
        repo_name = gold_spec.get("repo_name", "")

        # Fetch real git diff for semantic entailment
        pr_diff = ""
        repo_dir_name = repo_name.split("/")[-1]
        repo_path = os.path.join(repo_cache_root, repo_dir_name)
        if os.path.exists(repo_path) and base_commit and target_commit:
            try:
                pr_diff = subprocess.check_output(
                    ["git", "-C", repo_path, "diff", f"{base_commit}..{target_commit}"],
                    env={**os.environ, "GIT_NO_LAZY_FETCH": "1", "GIT_TERMINAL_PROMPT": "0"},
                    stderr=subprocess.DEVNULL
                ).decode("utf-8", errors="ignore")
            except Exception:
                pr_diff = ""

        # 1. Bipartite Matching with symbol normalization
        match_res = match_claims_bipartite_v4(claims, gold_claims, pr_diff=pr_diff)

        # 2. Structural and Semantic Attribution
        attributions = []
        for c in claims:
            status, details = validate_claim_attribution_v4(c, gold_spec, pr_diff=pr_diff)
            attr_counts[status] = attr_counts.get(status, 0) + 1
            attributions.append({
                "claim_id": c.get("claim_id"),
                "symbol": c.get("symbol"),
                "normalized_symbol": normalize_symbol(c.get("symbol")),
                "status": status,
                "details": details
            })

        total_matched_required += match_res["matched_required"]
        total_required += match_res["total_required"]
        total_matched_optional += match_res["matched_optional"]
        total_optional += match_res["total_optional"]
        total_claims += len(claims)

        task_evaluations[task_id] = {
            "generated_claims_count": len(claims),
            "matching": match_res,
            "attributions": attributions
        }

    macro_rec = total_matched_required / total_required if total_required > 0 else 0.0
    macro_prec = (total_matched_required + total_matched_optional) / total_claims if total_claims > 0 else 0.0
    macro_f1 = (2 * macro_prec * macro_rec) / (macro_prec + macro_rec) if (macro_prec + macro_rec) > 0 else 0.0
    macro_opt = total_matched_optional / total_optional if total_optional > 0 else 0.0
    supp_acc = attr_counts["SUPPORTED"] / total_claims if total_claims > 0 else 0.0
    unsupp_rate = (attr_counts["UNSUPPORTED"] + attr_counts["WRONG_ARTIFACT"] + attr_counts["WRONG_COMMIT"] + attr_counts["MISSING_COMMIT_ATTRIBUTION"]) / total_claims if total_claims > 0 else 0.0

    return {
        "evaluator_version": "4.0.0",
        "required_recall": macro_rec,
        "valid_precision": macro_prec,
        "f1": macro_f1,
        "optional_valid_discovery_rate": macro_opt,
        "supported_attribution_accuracy": supp_acc,
        "unsupported_claim_rate": unsupp_rate,
        "total_claims_evaluated": total_claims,
        "total_matched_required": total_matched_required,
        "total_required": total_required,
        "total_matched_optional": total_matched_optional,
        "total_optional": total_optional,
        "attribution_counts": attr_counts,
        "task_evaluations": task_evaluations,
        "claims_per_task": total_claims / len(task_evaluations) if task_evaluations else 0.0
    }
