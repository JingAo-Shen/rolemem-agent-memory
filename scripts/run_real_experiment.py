"""
Script to execute REAL empirical experiments using DeepSeek-V3 LLM API.
"""
import sys
import os
import json
import time

sys.path.insert(0, "/code/rolemem-agent-memory")

from src.memory import RoleMemoryStore
from src.real_llm_runner import RealTaskEnvironment

def run_real_experiment():
    with open("data/task-specs.jsonl", "r", encoding="utf-8") as f:
        tasks = [json.loads(line) for line in f if line.strip()]

    methods = [
        ("B0_no_memory", "no_memory"),
        ("A2_unscoped_stale", "unscoped"),
        ("F_rolemem_scoped", "rolemem")
    ]

    results_by_method = {}

    print(f"=== Starting Real LLM Experiments with DeepSeek API on {len(tasks)} Tasks ===")
    print("Evaluating real Python code generation, real prompt tokens, and real pytest assertions...\n")

    for method_id, method_type in methods:
        print(f"\n========================================================")
        print(f"  RUNNING METHOD: {method_id}")
        print(f"========================================================")

        passed_count = 0
        stale_error_count = 0
        total_tokens = 0
        task_logs = []

        for idx, task in enumerate(tasks):
            tid = task["id"]
            cat = task["category"]
            role = task["roles"]["phase2"]

            # Setup memory store for this task
            store = RoleMemoryStore()
            if cat == "explicit_update":
                store.write_record({
                    "id": f"{tid}_m1",
                    "task_scope": tid,
                    "statement": "In cache_config.py, set DEFAULT_TTL = 60.",
                    "valid_from": 1,
                    "valid_to": 3,
                    "role_tags": ["coder"],
                    "artifact_hash": "hash_v1"
                }, as_of=1)
                store.write_record({
                    "id": f"{tid}_m2",
                    "task_scope": tid,
                    "statement": "In cache_config.py, set POLICY = 'ADAPTIVE_LRU' and MAX_KEYS = 10000. Do NOT set DEFAULT_TTL.",
                    "valid_from": 3,
                    "valid_to": 999999,
                    "supersedes": f"{tid}_m1",
                    "role_tags": ["coder", "reviewer"],
                    "artifact_hash": "hash_v2"
                }, as_of=3)

            elif cat == "stale_evidence":
                store.write_record({
                    "id": f"{tid}_m1",
                    "task_scope": tid,
                    "statement": "auth_service.py defines constant SALT = 'legacy_salt_value'.",
                    "valid_from": 1,
                    "valid_to": 999999,
                    "role_tags": ["coder"],
                    "artifact_hash": "commit_v1" # Old hash
                }, as_of=1)

            elif cat == "unresolved_conflict":
                store.write_record({
                    "id": f"{tid}_m1",
                    "task_scope": tid,
                    "statement": "Requirement note A: Set RATE_LIMIT = 10 requests/min.",
                    "valid_from": 1,
                    "valid_to": 999999,
                    "role_tags": ["coder"],
                    "artifact_hash": "hash_v1"
                }, as_of=1)
                store.write_record({
                    "id": f"{tid}_m2",
                    "task_scope": tid,
                    "statement": "Requirement note B: Conflicting requirement requests RATE_LIMIT = 1000 requests/min. Flag conflict and request clarification.",
                    "valid_from": 2,
                    "valid_to": 999999,
                    "role_tags": ["reviewer"],
                    "artifact_hash": "hash_v1"
                }, as_of=2)

            else: # no_update
                store.write_record({
                    "id": f"{tid}_m1",
                    "task_scope": tid,
                    "statement": "Active requirement: In db_config.py, migrate timeout setting to TIMEOUT_MS = 5000.",
                    "valid_from": 1,
                    "valid_to": 999999,
                    "role_tags": ["coder", "reviewer"],
                    "artifact_hash": "hash_v1"
                }, as_of=1)

            # Retrieve memory based on method
            if method_type == "no_memory":
                mem_context = ""
            elif method_type == "unscoped":
                retrieved = store.retrieve(task["title"], role=role, as_of=4, task_scope=tid, method="no_validity")
                mem_context = "\n".join([f"- [Record {m['id']}] {m['statement']}" for m in retrieved])
            else: # rolemem
                retrieved = store.retrieve(task["title"], role=role, as_of=4, task_scope=tid, current_artifact_hash="commit_v2" if cat == "stale_evidence" else ("hash_v2" if cat == "explicit_update" else "hash_v1"), method="full")
                mem_context = "\n".join([f"- [Valid Record {m['id']}] {m['statement']}" for m in retrieved])

            # Run in real environment with real LLM
            env = RealTaskEnvironment(task)
            passed, err_msg, raw_reply, meta = env.run_agent_turn(mem_context, role)
            env.cleanup()
            store.close()

            if passed:
                passed_count += 1
            if meta.get("stale_used", False):
                stale_error_count += 1
            total_tokens += meta["tokens"].get("total_tokens", 0)

            status_str = "PASS" if passed else "FAIL"
            print(f"  [{tid} | {cat:19s}] -> {status_str:4s} | Stale used: {str(meta.get('stale_used', False)):5s} | Latency: {meta.get('latency', 0):.2f}s | Tokens: {meta['tokens'].get('total_tokens', 0)}")
            if not passed:
                print(f"       Reason: {err_msg}")

            task_logs.append({
                "task_id": tid,
                "category": cat,
                "passed": passed,
                "stale_used": meta.get("stale_used", False),
                "error": err_msg,
                "latency": meta.get("latency", 0),
                "tokens": meta.get("tokens", {})
            })

            time.sleep(0.3)

        tsr = passed_count / len(tasks)
        stale_rate = stale_error_count / len(tasks)
        results_by_method[method_id] = {
            "tsr": tsr,
            "stale_rate": stale_rate,
            "total_tokens": total_tokens,
            "passed_count": passed_count,
            "total_tasks": len(tasks),
            "logs": task_logs
        }
        print(f"\n>> {method_id} Summary: TSR = {tsr*100:.1f}%, Stale Error Rate = {stale_rate*100:.1f}%, Total Tokens = {total_tokens}")

    with open("runs/real_deepseek_experiment_results.json", "w", encoding="utf-8") as f:
        json.dump(results_by_method, f, indent=2)

    print("\n=== Real LLM Experiment Completed Successfully! ===")

if __name__ == "__main__":
    run_real_experiment()
