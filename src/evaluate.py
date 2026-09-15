"""
Evaluation and scoring engine for RoleMem experiments.
Executes episodes, logs events.jsonl, predictions.jsonl, and calculates rigorous metrics.
"""
import os
import json
import time
import hashlib
from typing import Dict, Any, List
from src.memory import RoleMemoryStore
from src.sandbox import TaskSandbox

def setup_task_memory(store: RoleMemoryStore, task_spec: Dict[str, Any]):
    """Populates memory store with task history and update events."""
    tid = task_spec["id"]
    cat = task_spec["category"]

    # Write initial events
    if cat == "explicit_update":
        if "cache_config" in str(task_spec):
            store.write_record({
                "id": f"{tid}_m1",
                "task_scope": tid,
                "type": "requirement",
                "statement": "Set DEFAULT_TTL = 60 in cache_config.py for fixed cache expiration.",
                "evidence_ids": ["ev_1"],
                "valid_from": 1,
                "valid_to": 3,
                "role_tags": ["coder", "all"],
                "artifact_hash": "d4e5f6a1"
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
                "artifact_hash": "d4e5f6a2"
            }, as_of=3)
        elif "payment_service" in str(task_spec):
            store.write_record({
                "id": f"{tid}_m1",
                "task_scope": tid,
                "type": "requirement",
                "statement": "Return dict with flat status {'status': 'SUCCESS', 'tx_id': id}.",
                "evidence_ids": ["ev_1"],
                "valid_from": 1,
                "valid_to": 3,
                "role_tags": ["coder", "all"],
                "artifact_hash": "e5f6a1b2"
            }, as_of=1)
            store.write_record({
                "id": f"{tid}_m2",
                "task_scope": tid,
                "type": "requirement",
                "statement": "BREAKING UPDATE: Return standard wrapper {'code': 200, 'data': {'tx_id': id, 'status': 'SUCCESS'}}.",
                "evidence_ids": ["ev_2"],
                "valid_from": 3,
                "valid_to": 999999,
                "supersedes": f"{tid}_m1",
                "role_tags": ["coder", "reviewer", "all"],
                "artifact_hash": "e5f6a1b3"
            }, as_of=3)
        elif "billing" in str(task_spec):
            store.write_record({
                "id": f"{tid}_m1",
                "task_scope": tid,
                "type": "requirement",
                "statement": "Store billing amounts as float with 2 decimal places.",
                "evidence_ids": ["ev_1"],
                "valid_from": 1,
                "valid_to": 3,
                "role_tags": ["coder", "all"],
                "artifact_hash": "f6a1b2c3"
            }, as_of=1)
            store.write_record({
                "id": f"{tid}_m2",
                "task_scope": tid,
                "type": "requirement",
                "statement": "URGENT UPDATE: Floating point precision error found. All amounts MUST be integer micro-units (multiply by 1,000,000).",
                "evidence_ids": ["ev_2"],
                "valid_from": 3,
                "valid_to": 999999,
                "supersedes": f"{tid}_m1",
                "role_tags": ["coder", "reviewer", "all"],
                "artifact_hash": "f6a1b2c4"
            }, as_of=3)
    elif cat == "stale_evidence":
        if "auth.py" in str(task_spec):
            store.write_record({
                "id": f"{tid}_m1",
                "task_scope": tid,
                "type": "fact",
                "statement": "auth.py defines SALT = 'legacy_salt_value'.",
                "evidence_ids": ["ev_1"],
                "valid_from": 1,
                "valid_to": 999999,
                "role_tags": ["coder"],
                "artifact_hash": "a2b3c4d5"  # Old hash
            }, as_of=1)
        elif "orders.py" in str(task_spec):
            store.write_record({
                "id": f"{tid}_m1",
                "task_scope": tid,
                "type": "fact",
                "statement": "OrderStatus = ['PENDING', 'PAID', 'SHIPPED'].",
                "evidence_ids": ["ev_1"],
                "valid_from": 1,
                "valid_to": 999999,
                "role_tags": ["coder"],
                "artifact_hash": "b3c4d5e6"  # Old hash
            }, as_of=1)
        elif "policy.py" in str(task_spec):
            store.write_record({
                "id": f"{tid}_m1",
                "task_scope": tid,
                "type": "fact",
                "statement": "user permissions checked via user.has_role('admin').",
                "evidence_ids": ["ev_1"],
                "valid_from": 1,
                "valid_to": 999999,
                "role_tags": ["coder"],
                "artifact_hash": "c4d5e6f7"  # Old hash
            }, as_of=1)
    elif cat == "no_update":
        store.write_record({
            "id": f"{tid}_m1",
            "task_scope": tid,
            "type": "requirement",
            "statement": f"Valid initial requirement for {tid}.",
            "evidence_ids": ["ev_1"],
            "valid_from": 1,
            "valid_to": 999999,
            "role_tags": ["coder", "reviewer", "all"],
            "artifact_hash": "initial_hash"
        }, as_of=1)

def run_evaluation(
    tasks: List[Dict[str, Any]],
    method: str = "full",
    token_budget: int = 2048,
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

            # Create ephemeral memory store for this task
            store = RoleMemoryStore()
            setup_task_memory(store, task)

            # Retrieve memories as of switch point
            as_of = task.get("switch_point", 4)
            current_hash = "updated_hash_v2" if cat == "stale_evidence" else None
            
            retrieved = store.retrieve(
                query=task.get("title", ""),
                role=role,
                as_of=as_of,
                task_scope=tid,
                current_artifact_hash=current_hash,
                method=method,
                token_budget=token_budget
            )

            # Execute in sandbox
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
