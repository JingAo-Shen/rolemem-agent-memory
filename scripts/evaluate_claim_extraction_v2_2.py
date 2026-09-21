#!/usr/bin/env python3
"""
scripts/evaluate_claim_extraction_v2_2.py

Protocol V2.2 Extraction Evaluation Pipeline:
- Strictly evaluates natural-language / semi-structured statement extraction independently of validity verification.
- Phase 1: Takes blind statements without structured metadata -> outputs predictions_claim_extraction.jsonl.
- Phase 2: Scores extracted structured fields (claim_type, subject, predicate, object) against dev_claim_gold_v2.jsonl.
- Evaluates Developer-Seen Paraphrase Dev Set (165 records) and outputs paraphrase_extraction_results.json.
"""

import os
import sys
import json
from typing import Dict, Any, List, Optional

sys.path.insert(0, "/code/rolemem-agent-memory")
from src.claim_validity.claim_extractor import DeterministicClaimExtractor

DATA_DIR = "/code/rolemem-agent-memory/data/claim_validity_v2_2"
INPUTS_PATH = os.path.join(DATA_DIR, "dev_claim_inputs_v2.jsonl")
GOLD_PATH = os.path.join(DATA_DIR, "dev_claim_gold_v2.jsonl")
PARAPHRASE_PATH = os.path.join(DATA_DIR, "paraphrase_dev.jsonl")

PRED_EXTRACTION_PATH = os.path.join(DATA_DIR, "predictions_claim_extraction.jsonl")
DEV_RESULTS_PATH = os.path.join(DATA_DIR, "dev_extraction_results.json")
PARAPHRASE_RESULTS_PATH = os.path.join(DATA_DIR, "paraphrase_extraction_results.json")


def run_phase_1_dev_extraction() -> str:
    """
    Phase 1: Extracts structured claims from blind inputs.
    Input contains ONLY raw_statement, repository, file_path, and claim_id.
    """
    print("--- Running Extraction Phase 1: Dev Statements ---")
    with open(INPUTS_PATH, "r", encoding="utf-8") as f:
        inputs = [json.loads(line) for line in f if line.strip()]

    extractor = DeterministicClaimExtractor()
    extracted_records = []

    for item in inputs:
        cid = item["claim_id"]
        st = item["raw_statement"]
        repo = item["repository"]
        fp = item["file_path"]

        # Strictly blind extraction: pass no symbols or gold metadata
        claim = extractor.extract(
            raw_statement=st,
            claim_id=cid,
            repository=repo,
            file_path=fp,
            source_case_id=item.get("source_case_id")
        )

        extracted_records.append({
            "claim_id": cid,
            "source_case_id": item.get("source_case_id", ""),
            "raw_statement": st,
            "extracted_claim_type": claim.claim_type.value,
            "extracted_subject": claim.subject,
            "extracted_predicate": claim.predicate,
            "extracted_object": claim.object,
            "extracted_qualifiers": claim.qualifiers,
            "claim_parse_status": claim.claim_parse_status
        })

    with open(PRED_EXTRACTION_PATH, "w", encoding="utf-8") as f:
        for r in extracted_records:
            f.write(json.dumps(r) + "\n")

    print(f"Extraction predictions saved to {PRED_EXTRACTION_PATH}")
    return PRED_EXTRACTION_PATH


def score_extraction(predictions: List[Dict[str, Any]], gold_records: List[Dict[str, Any]]) -> Dict[str, Any]:
    pred_map = {p["claim_id"]: p for p in predictions}
    gold_map = {g["claim_id"]: g for g in gold_records}

    assert set(pred_map.keys()) == set(gold_map.keys()), "Mismatch between extraction prediction IDs and gold IDs!"
    assert len(pred_map) == len(predictions), "Duplicate prediction IDs detected!"

    total = len(gold_map)
    type_matches = 0
    subject_matches = 0
    predicate_matches = 0
    object_matches = 0
    full_exact_matches = 0
    parsed_count = 0
    unresolved_count = 0

    per_type_stats = {}

    for cid, gold in gold_map.items():
        pred = pred_map[cid]
        gold_type = gold["claim_type"]
        gold_sub = gold.get("subject", "").strip().strip("`'\"")
        gold_pred = gold.get("predicate", "").strip()
        gold_obj = gold.get("object", "").strip().strip("`'\"")

        pred_type = pred["extracted_claim_type"]
        pred_sub = pred.get("extracted_subject", "").strip().strip("`'\"")
        pred_pred = pred.get("extracted_predicate", "").strip()
        pred_obj = pred.get("extracted_object", "").strip().strip("`'\"")

        is_parsed = pred["claim_parse_status"] == "PARSED"
        if is_parsed:
            parsed_count += 1
        else:
            unresolved_count += 1

        t_match = (pred_type == gold_type)
        s_match = (pred_sub == gold_sub)
        p_match = (pred_pred == gold_pred)
        o_match = (pred_obj == gold_obj)
        full_match = t_match and s_match and p_match and o_match

        if t_match: type_matches += 1
        if s_match: subject_matches += 1
        if p_match: predicate_matches += 1
        if o_match: object_matches += 1
        if full_match: full_exact_matches += 1

        if gold_type not in per_type_stats:
            per_type_stats[gold_type] = {
                "total": 0, "type_match": 0, "subject_match": 0,
                "predicate_match": 0, "object_match": 0, "full_match": 0,
                "unresolved": 0
            }
        st_data = per_type_stats[gold_type]
        st_data["total"] += 1
        if t_match: st_data["type_match"] += 1
        if s_match: st_data["subject_match"] += 1
        if p_match: st_data["predicate_match"] += 1
        if o_match: st_data["object_match"] += 1
        if full_match: st_data["full_match"] += 1
        if not is_parsed: st_data["unresolved"] += 1

    per_type_metrics = {}
    for gt, data in sorted(per_type_stats.items()):
        cnt = data["total"]
        per_type_metrics[gt] = {
            "count": cnt,
            "type_accuracy": data["type_match"] / cnt if cnt > 0 else 0.0,
            "subject_match_rate": data["subject_match"] / cnt if cnt > 0 else 0.0,
            "predicate_match_rate": data["predicate_match"] / cnt if cnt > 0 else 0.0,
            "object_match_rate": data["object_match"] / cnt if cnt > 0 else 0.0,
            "full_exact_match_rate": data["full_match"] / cnt if cnt > 0 else 0.0,
            "unresolved_rate": data["unresolved"] / cnt if cnt > 0 else 0.0
        }

    return {
        "total_claims": total,
        "parse_coverage": parsed_count / total if total > 0 else 0.0,
        "unresolved_rate": unresolved_count / total if total > 0 else 0.0,
        "claim_type_accuracy": type_matches / total if total > 0 else 0.0,
        "subject_exact_match_rate": subject_matches / total if total > 0 else 0.0,
        "predicate_exact_match_rate": predicate_matches / total if total > 0 else 0.0,
        "object_exact_match_rate": object_matches / total if total > 0 else 0.0,
        "full_structured_claim_exact_match_rate": full_exact_matches / total if total > 0 else 0.0,
        "per_claim_type_metrics": per_type_metrics
    }


def run_phase_2_dev_evaluation():
    print("--- Running Extraction Phase 2: Dev Evaluation ---")
    with open(PRED_EXTRACTION_PATH, "r", encoding="utf-8") as f:
        preds = [json.loads(line) for line in f if line.strip()]

    with open(GOLD_PATH, "r", encoding="utf-8") as f:
        gold = [json.loads(line) for line in f if line.strip()]

    metrics = score_extraction(preds, gold)
    metrics["benchmark_designation"] = "DEVELOPMENT_EXTRACTION_SELF_CONSISTENCY"
    metrics["extractor_version"] = "2.2-v0.2"
    metrics["independent_gold"] = False
    metrics["scientific_generalization_claim"] = False
    metrics["note"] = "Structured claim representation was generated within the same extractor development cycle and does not constitute independent extraction ground truth."

    with open(DEV_RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    print(f"Dev extraction metrics saved to {DEV_RESULTS_PATH}:")
    print(f"  Claim Type Acc:        {metrics['claim_type_accuracy']*100:.1f}%")
    print(f"  Subject Exact Match:   {metrics['subject_exact_match_rate']*100:.1f}%")
    print(f"  Predicate Exact Match: {metrics['predicate_exact_match_rate']*100:.1f}%")
    print(f"  Object Exact Match:    {metrics['object_exact_match_rate']*100:.1f}%")
    print(f"  Full Structured Match: {metrics['full_structured_claim_exact_match_rate']*100:.1f}%")
    print(f"  Parse Coverage:        {metrics['parse_coverage']*100:.1f}%")
    print(f"  Unresolved Rate:       {metrics['unresolved_rate']*100:.1f}%")


def evaluate_paraphrase_dev():
    print("--- Running Paraphrase Dev Extraction Evaluation (DEVELOPER_SEEN_PARAPHRASE_DEV) ---")
    if not os.path.exists(PARAPHRASE_PATH):
        print(f"Paraphrase file {PARAPHRASE_PATH} not found.")
        return

    with open(PARAPHRASE_PATH, "r", encoding="utf-8") as f:
        paraphrases = [json.loads(line) for line in f if line.strip()]

    extractor = DeterministicClaimExtractor()
    preds = []
    gold = []

    for p in paraphrases:
        pid = p["paraphrase_id"]
        st = p["paraphrased_statement"]
        repo = p.get("repository", "")
        fp = p.get("file_path", "")

        claim = extractor.extract(
            raw_statement=st,
            claim_id=pid,
            repository=repo,
            file_path=fp,
            source_case_id=p.get("source_case_id")
        )

        preds.append({
            "claim_id": pid,
            "extracted_claim_type": claim.claim_type.value,
            "extracted_subject": claim.subject,
            "extracted_predicate": claim.predicate,
            "extracted_object": claim.object,
            "claim_parse_status": claim.claim_parse_status
        })

        gold.append({
            "claim_id": pid,
            "claim_type": p["claim_type"],
            "subject": p["subject"],
            "predicate": p["predicate"],
            "object": p["object"]
        })

    para_metrics = score_extraction(preds, gold)
    para_metrics["benchmark_designation"] = "DEVELOPER_SEEN_PARAPHRASE_DEV"
    para_metrics["note"] = "Paraphrases developed in same iteration as parser. Not for scientific generalization claim."
    para_metrics["extractor_version"] = "2.2-v0.2"

    with open(PARAPHRASE_RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump(para_metrics, f, indent=2)

    print(f"Paraphrase extraction metrics saved to {PARAPHRASE_RESULTS_PATH}:")
    print(f"  Total Paraphrases:     {para_metrics['total_claims']}")
    print(f"  Claim Type Acc:        {para_metrics['claim_type_accuracy']*100:.1f}%")
    print(f"  Subject Exact Match:   {para_metrics['subject_exact_match_rate']*100:.1f}%")
    print(f"  Predicate Exact Match: {para_metrics['predicate_exact_match_rate']*100:.1f}%")
    print(f"  Object Exact Match:    {para_metrics['object_exact_match_rate']*100:.1f}%")
    print(f"  Full Structured Match: {para_metrics['full_structured_claim_exact_match_rate']*100:.1f}%")
    print(f"  Parse Coverage:        {para_metrics['parse_coverage']*100:.1f}%")
    print(f"  Unresolved Rate:       {para_metrics['unresolved_rate']*100:.1f}%")


if __name__ == "__main__":
    run_phase_1_dev_extraction()
    run_phase_2_dev_evaluation()
    evaluate_paraphrase_dev()
