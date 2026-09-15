import os
import json
import time
from typing import Dict, Any, List
from src.memory import RoleMemoryStore
from src.sandbox import TaskSandbox

def setup_task_memory(store: RoleMemoryStore, task_spec: Dict[str, Any]):
    tid = task_spec["id"]
    cat = task_spec["category"]

    # Add general background distractors
    for i in range(3):
        store.write_record({
            "id": f"{tid}_distractor_{i}",
            "task_scope": tid,
            "type": "note",
            "statement": f"General developer note {i}: standard project logging and linting guidelines apply to {tid}.",
            "evidence_ids": [f"dist_{i}"],
            "valid_from": 1,
            "valid_to": 999999,
            "role_tags": ["coder"],
            "artifact_hash": "hash_v1"
        }, as_of=1)

    if cat == "explicit_update":
        store.write_record({
            "id": f"{tid}_m1",
            "task_scope": tid,
            "type": "requirement",
            "statement": "Legacy configuration policy: Set DEFAULT_TTL = 60 in cache_config.py.",
            "evidence_ids": ["ev_1"],
            "valid_from": 1,
            "valid_to": 3,
            "role_tags": ["coder", "all"],
            "artifact_hash": "hash_v1"
        }, as_of=1)
        store.write_record({
            "id": f"{tid}_m2",
            "task_scope": tid,
            "type": "requirement",
            "statement": "UPDATE: Discard fixed 60s TTL; change cache strategy to dynamic adaptive LRU with max_keys=10000.",
            "evidence_ids": ["ev_2"],
            "valid_from": 3,
            "valid_to": 999999,
            "supersedes": f"{tid}_m1",
            "role_tags": ["coder", "reviewer", "all"],
            "artifact_hash": "hash_v2"
        }, as_of=3)

    elif cat == "stale_evidence":
        store.write_record({
            "id": f"{tid}_m1",
            "task_scope": tid,
            "type": "fact",
            "statement": "Observed auth.py defines SALT = 'legacy_salt_value'.",
            "evidence_ids": ["ev_1"],
            "valid_from": 1,
            "valid_to": 999999,
            "role_tags": ["coder"],
            "artifact_hash": "commit_v1"  # Old hash
        }, as_of=1)

    elif cat == "unresolved_conflict":
        store.write_record({
            "id": f"{tid}_m1",
            "task_scope": tid,
            "type": "requirement",
            "statement": "Standard requirement doc: Throttling limit 10 requests per minute.",
            "evidence_ids": ["ev_1"],
            "valid_from": 1,
            "valid_to": 999999,
            "role_tags": ["coder"],
            "artifact_hash": "hash_v1"
        }, as_of=1)
        store.write_record({
            "id": f"{tid}_m2",
            "task_scope": tid,
            "type": "conflict_warning",
            "statement": "Requirement doc B: Throttling limit 1000 requests per minute (Unresolved conflict).",
            "evidence_ids": ["ev_2"],
            "valid_from": 2,
            "valid_to": 999999,
            "role_tags": ["reviewer"],
            "artifact_hash": "hash_v1"
        }, as_of=2)

    elif cat == "no_update":
        store.write_record({
            "id": f"{tid}_m1",
            "task_scope": tid,
            "type": "requirement",
            "statement": "Migrate DB timeout settings from seconds to milliseconds format in db_config.py: TIMEOUT_MS = 5000.",
            "evidence_ids": ["ev_1"],
            "valid_from": 1,
            "valid_to": 999999,
            "role_tags": ["coder", "reviewer", "all"],
            "artifact_hash": "hash_v1"
        }, as_of=1)

def run_evaluation(
    tasks: List[Dict[str, Any]],
    method: str = "full",
    token_budget: int = 512,
    output_dir: str = "runs/run_output"
) -> Dict[str, Any]:
    os.makedirs(output_dir, exist_ok=True)
    events_log = os.path.join(output_dir, "events.jsonl")
    preds_log = os.path.join(output_dir, "predictions.jsonl")

    total = len(tasks)
    passed_count = 0
    stale_error_count = 0
    total_latency_ms = 0
    predictions = []

    with open(events_log, "w", encoding="utf-8") as f_ev, open(preds_log, "w", encoding="utf-8") as f_pred:
        for idx, task in enumerate(tasks):
            t_start = time.time()
            tid = task["id"]
            cat = task["category"]
            family = task["family"]
            role = task.get("roles", {}).get("phase2", "reviewer")

            store = RoleMemoryStore()
            setup_task_memory(store, task)

            as_of = task.get("switch_point", 4)
            current_hash = "commit_v2" if cat == "stale_evidence" else "hash_v2"
            
            retrieved = store.retrieve(
                query=task.get("title", ""),
                role=role,
                as_of=as_of,
                task_scope=tid,
                current_artifact_hash=current_hash,
                method=method,
                token_budget=token_budget,
                role_bonus=0.8
            )

            sandbox = TaskSandbox(task)
            passed, err_msg, exec_meta = sandbox.execute_mock_action(method, retrieved)
            sandbox.cleanup()
            store.close()

            latency_ms = int((time.time() - t_start) * 1000)
            total_latency_ms += latency_ms

            if passed:
                passed_count += 1
            if exec_meta.get("stale_used", False):
                stale_error_count += 1

            event_record = {
                "task_id": tid,
                "family": family,
                "category": cat,
                "method": method,
                "role": role,
                "status": "PASSED" if passed else "FAILED",
                "stale_used": exec_meta.get("stale_used", False),
                "latency_ms": latency_ms,
                "retrieved_count": len(retrieved),
                "error": err_msg if not passed else None
            }
            f_ev.write(json.dumps(event_record) + "\n")

            pred_record = {
                "task_id": tid,
                "passed": passed,
                "error": err_msg,
                "retrieved_ids": [m["id"] for m in retrieved]
            }
            f_pred.write(json.dumps(pred_record) + "\n")
            predictions.append(pred_record)

    tsr = passed_count / max(total, 1)
    stale_error_rate = stale_error_count / max(total, 1)
    avg_latency = total_latency_ms / max(total, 1)

    metrics = {
        "total_tasks": total,
        "passed_tasks": passed_count,
        "tsr": round(tsr, 4),
        "stale_error_count": stale_error_count,
        "stale_error_rate": round(stale_error_rate, 4),
        "avg_latency_ms": round(avg_latency, 2),
        "method": method,
        "token_budget": token_budget
    }

    with open(os.path.join(output_dir, "metrics.json"), "w", encoding="utf-8") as f_met:
        json.dump(metrics, f_met, indent=2)

    return metrics
