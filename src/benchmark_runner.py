r"""
src/benchmark_runner.py

RoleMem Unified Benchmark Runner:
Coordinates batch inference across RoleMem and baseline models (Majority, Static AST, Naive RAG),
logs retrieval traces and predictions to results/, evaluates against gold labels,
and renders the comparative experimental performance table.
"""

from __future__ import annotations
import argparse
import json
import os
import sys
import time
from typing import Dict, Any, List, Optional, Tuple

from src.rolemem.adapter import RoleMemEvaluationAdapter
from src.baselines.majority import MajorityBaselinePredictor
from src.baselines.static_ast import StaticASTBaselinePredictor
from src.baselines.naive_rag import NaiveRAGBaselinePredictor
from src.evaluation.metrics import evaluate_predictions


class BenchmarkRunner:
    """End-to-end benchmark execution and evaluation orchestrator."""

    def __init__(
        self,
        inputs_path: str = "data/formal_v2_2/formal_inputs.jsonl",
        gold_path: str = "data/formal_v2_2/formal_gold_private.jsonl",
        case_map_path: str = "data/formal_v2_2/formal_case_map_private.json",
        output_dir: str = "results"
    ):
        self.inputs_path = inputs_path
        self.gold_path = gold_path
        self.case_map_path = case_map_path
        self.output_dir = output_dir

        self.inputs: List[Dict[str, Any]] = []
        self.gold_annotations: List[Dict[str, Any]] = []
        self.case_map: Dict[str, Dict[str, Any]] = {}

        self._load_datasets()

    def _load_datasets(self) -> None:
        """Load benchmark input manifests, gold ground truth, and case mapping."""
        if os.path.exists(self.inputs_path):
            with open(self.inputs_path, "r", encoding="utf-8") as f:
                self.inputs = [json.loads(line) for line in f if line.strip()]

        if os.path.exists(self.gold_path):
            with open(self.gold_path, "r", encoding="utf-8") as f:
                self.gold_annotations = [json.loads(line) for line in f if line.strip()]

        if os.path.exists(self.case_map_path):
            with open(self.case_map_path, "r", encoding="utf-8") as f:
                self.case_map = json.load(f)

    def run_method(
        self,
        method_name: str,
        limit: Optional[int] = None
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Execute prediction pipeline for a given method.
        Returns (predictions, traces).
        """
        cases = self.inputs[:limit] if limit else self.inputs
        predictions: List[Dict[str, Any]] = []
        traces: List[Dict[str, Any]] = []

        if method_name == "rolemem":
            adapter = RoleMemEvaluationAdapter(case_map_path=self.case_map_path)
            for case in cases:
                t0 = time.time()
                pred = adapter.evaluate_case(case)
                predictions.append(pred)
                traces.append({
                    "case_id": case.get("case_id"),
                    "method": "rolemem",
                    "claim_type": case.get("claim_type"),
                    "predicted_label": pred["predicted_label"],
                    "confidence": pred["confidence"],
                    "escalation_tier": pred["escalation_tier"],
                    "action_count": pred["action_count"],
                    "elapsed_sec": round(time.time() - t0, 4)
                })

        elif method_name == "majority":
            predictor = MajorityBaselinePredictor()
            for case in cases:
                meta = self.case_map.get(case.get("case_id", ""), {})
                pred = predictor.predict(case, meta)
                predictions.append(pred)
                traces.append({
                    "case_id": case.get("case_id"),
                    "method": "majority",
                    "predicted_label": pred["predicted_label"]
                })

        elif method_name == "static_ast":
            predictor = StaticASTBaselinePredictor()
            for case in cases:
                meta = self.case_map.get(case.get("case_id", ""), {})
                pred = predictor.predict(case, meta)
                predictions.append(pred)
                traces.append({
                    "case_id": case.get("case_id"),
                    "method": "static_ast",
                    "predicted_label": pred["predicted_label"],
                    "action_count": pred["action_count"]
                })

        elif method_name == "naive_rag":
            predictor = NaiveRAGBaselinePredictor()
            for case in cases:
                meta = self.case_map.get(case.get("case_id", ""), {})
                pred = predictor.predict(case, meta)
                predictions.append(pred)
                traces.append({
                    "case_id": case.get("case_id"),
                    "method": "naive_rag",
                    "predicted_label": pred["predicted_label"],
                    "action_count": pred["action_count"]
                })

        else:
            raise ValueError(f"Unknown method name: {method_name}")

        return predictions, traces

    def execute_all(
        self,
        methods: Optional[List[str]] = None,
        limit: Optional[int] = None,
        track: str = "strict"
    ) -> Dict[str, Any]:
        """Run all designated methods, evaluate metrics, and save artifacts."""
        target_methods = methods or ["majority", "static_ast", "naive_rag", "rolemem"]
        os.makedirs(self.output_dir, exist_ok=True)

        all_metrics: Dict[str, Any] = {}
        all_traces: List[Dict[str, Any]] = []

        # Gold subset matching limit
        evaluated_cases = self.inputs[:limit] if limit else self.inputs
        evaluated_ids = {c["case_id"] for c in evaluated_cases}
        gold_subset = [g for g in self.gold_annotations if g["case_id"] in evaluated_ids]

        for method in target_methods:
            preds, traces = self.run_method(method, limit=limit)
            all_traces.extend(traces)

            # Write predictions file
            pred_file = os.path.join(self.output_dir, f"predictions_{method}.jsonl")
            with open(pred_file, "w", encoding="utf-8") as f:
                for p in preds:
                    f.write(json.dumps(p) + "\n")

            if method == "rolemem":
                # Also save primary predictions.jsonl
                primary_pred_file = os.path.join(self.output_dir, "predictions.jsonl")
                with open(primary_pred_file, "w", encoding="utf-8") as f:
                    for p in preds:
                        f.write(json.dumps(p) + "\n")

            # Evaluate metrics
            m_eval = evaluate_predictions(preds, gold_subset, track=track)
            all_metrics[method] = m_eval

        # Save metrics.json
        metrics_file = os.path.join(self.output_dir, "metrics.json")
        with open(metrics_file, "w", encoding="utf-8") as f:
            json.dump({
                "experiment_metadata": {
                    "evaluated_cases_count": len(evaluated_cases),
                    "track": track,
                    "methods_evaluated": target_methods,
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                },
                "methods": all_metrics
            }, f, indent=2)

        # Save retrieval_trace.json
        trace_file = os.path.join(self.output_dir, "retrieval_trace.json")
        with open(trace_file, "w", encoding="utf-8") as f:
            json.dump(all_traces, f, indent=2)

        return all_metrics

    def render_table(self, all_metrics: Dict[str, Any], track: str = "strict") -> str:
        """Render markdown comparison table from metrics."""
        lines = []
        lines.append("\n### Experimental Performance Comparison Table (RoleMem vs Baselines)\n")
        lines.append(f"**Evaluation Track**: `{track.upper()}` | **Evaluated Cases**: {next(iter(all_metrics.values())).get('total_evaluated', 0)}\n")
        lines.append("| Method | 3-Class Acc | Macro-F1 | Track A Acc | FIR (False Inval) | SER (Stale Escape) | Avg Actions | Wall Time/Case |")
        lines.append("| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |")

        display_order = ["majority", "static_ast", "naive_rag", "rolemem"]
        method_labels = {
            "majority": "Baseline-1: Majority",
            "static_ast": "Baseline-2: Static AST",
            "naive_rag": "Baseline-3: Naive RAG",
            "rolemem": "**RoleMem (Ours)**"
        }

        for m_key in display_order:
            if m_key not in all_metrics:
                continue
            m = all_metrics[m_key]
            p3 = m.get("primary_3class", {})
            ta = m.get("track_a_strict", {})
            risk = m.get("selective_risk_metrics", {})
            eff = m.get("operational_efficiency", {})

            acc_3 = f"{p3.get('accuracy', 0.0) * 100:.1f}%"
            f1_3 = f"{p3.get('macro_f1', 0.0) * 100:.1f}%"
            acc_ta = f"{ta.get('accuracy', 0.0) * 100:.1f}%"
            fir = f"{risk.get('false_invalid_rate_FIR', 0.0) * 100:.1f}%"
            ser = f"{risk.get('stale_escape_rate_SER', 0.0) * 100:.1f}%"
            act = f"{eff.get('avg_action_count', 0.0):.1f}"
            wall = f"{eff.get('avg_wall_time_sec', 0.0):.4f}s"

            lines.append(f"| {method_labels.get(m_key, m_key)} | {acc_3} | {f1_3} | {acc_ta} | {fir} | {ser} | {act} | {wall} |")

        return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Run RoleMem and baseline experiments.")
    parser.add_argument("--limit", "-n", type=int, default=None, help="Limit number of benchmark cases (e.g. 10 for sanity test).")
    parser.add_argument("--track", "-t", type=str, default="strict", choices=["strict", "compatible", "all"], help="Evaluation track.")
    parser.add_argument("--method", "-m", type=str, default="all", choices=["rolemem", "majority", "static_ast", "naive_rag", "all"], help="Method to evaluate.")
    parser.add_argument("--inputs", type=str, default="data/formal_v2_2/formal_inputs.jsonl", help="Inputs JSONL path.")
    parser.add_argument("--gold", type=str, default="data/formal_v2_2/formal_gold_private.jsonl", help="Gold JSONL path.")
    parser.add_argument("--case-map", type=str, default="data/formal_v2_2/formal_case_map_private.json", help="Case map path.")
    parser.add_argument("--output-dir", "-o", type=str, default="results", help="Output directory.")
    args = parser.parse_args()

    runner = BenchmarkRunner(
        inputs_path=args.inputs,
        gold_path=args.gold,
        case_map_path=args.case_map,
        output_dir=args.output_dir
    )

    methods = None if args.method == "all" else [args.method]
    metrics = runner.execute_all(methods=methods, limit=args.limit, track=args.track)
    table = runner.render_table(metrics, track=args.track)
    print(table)


if __name__ == "__main__":
    main()
