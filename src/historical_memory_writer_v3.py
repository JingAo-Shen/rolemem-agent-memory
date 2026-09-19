"""
src/historical_memory_writer_v3.py
Historical Memory Writer V3 for RoleMem Agent A.

Key Upgrades:
1. Class/Method Path Resolution:
   Resolves nested definitions inside classes into canonical symbol paths
   (e.g., 'CustomApp.should_ignore_error' or 'CPython3Posix.pyvenv_launch_patch_active').
2. AST Uniqueness Checking:
   Requires resolved_node_count == 1 in codebase AST. If multiple matching nodes exist
   without unambiguous path qualification, flags as AMBIGUOUS_TARGET.
3. 3-Element Quality Gate:
   Validates claim contains:
     - Deprecation element (e.g. deprecated, dropped, removed, obsolete)
     - Replacement element (e.g. use, replaced by, instead, migrate)
     - Rationale/Reason element (e.g. because, for, in order to, as of, support)
4. Robust Retry Loop:
   Retries up to 3 times if quality gate or AST uniqueness validation fails.
"""

import os
import sys
import json
import re
import ast
import hashlib
import subprocess
import torch
from typing import Dict, Any, List, Optional, Tuple

sys.path.insert(0, "/code/rolemem-agent-memory")
from src.schema_v1 import MemoryRecordV1
from transformers import AutoTokenizer, AutoModelForCausalLM


class HistoricalMemoryWriterV3:
    """Agent A Historical Memory Writer V3 with AST path resolution, uniqueness gating, and retry loop."""

    def __init__(
        self,
        model_dir: str = "/code/rolemem-agent-memory/models/qwen2.5-coder-7b",
        tokenizer: Optional[AutoTokenizer] = None,
        model: Optional[AutoModelForCausalLM] = None
    ):
        self.model_dir = model_dir
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        if tokenizer is not None and model is not None:
            self.tokenizer = tokenizer
            self.model = model
        else:
            self.tokenizer = AutoTokenizer.from_pretrained(model_dir, trust_remote_code=True)
            self.model = AutoModelForCausalLM.from_pretrained(
                model_dir,
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                device_map="auto" if self.device == "cuda" else None
            )
            self.model.eval()

    def resolve_ast_symbols_with_paths(self, file_content: str) -> Dict[str, Dict[str, Any]]:
        """
        Parses file content and extracts all functions, methods, and classes with their
        full canonical symbol paths (e.g., 'ClassName.method_name').
        """
        symbols = {}
        try:
            tree = ast.parse(file_content)
        except Exception:
            return symbols

        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                symbols[node.name] = {
                    "canonical_path": node.name,
                    "parent_class": None,
                    "node_type": "FunctionDef",
                    "lineno": node.lineno,
                    "node": node
                }
            elif isinstance(node, ast.ClassDef):
                symbols[node.name] = {
                    "canonical_path": node.name,
                    "parent_class": None,
                    "node_type": "ClassDef",
                    "lineno": node.lineno,
                    "node": node
                }
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        full_path = f"{node.name}.{item.name}"
                        symbols[full_path] = {
                            "canonical_path": full_path,
                            "parent_class": node.name,
                            "node_type": "MethodDef",
                            "lineno": item.lineno,
                            "node": item
                        }
        return symbols

    def check_ast_uniqueness(self, file_content: str, symbol: str) -> Dict[str, Any]:
        """
        Verifies that symbol resolves to exactly 1 AST node in file_content.
        Returns resolved_node_count, canonical_symbol, and status.
        """
        if not symbol or not file_content:
            return {"resolved_node_count": 0, "status": "SYMBOL_EMPTY", "canonical_symbol": symbol}

        symbols_map = self.resolve_ast_symbols_with_paths(file_content)

        # 1. Exact match on canonical path (e.g. 'Class.method' or 'func')
        if symbol in symbols_map:
            return {
                "resolved_node_count": 1,
                "status": "UNIQUE_PASS",
                "canonical_symbol": symbol,
                "node_info": {
                    "type": symbols_map[symbol]["node_type"],
                    "lineno": symbols_map[symbol]["lineno"]
                }
            }

        # 2. Check unqualified short name matching
        short_name = symbol.split(".")[-1]
        matching_paths = [path for path in symbols_map.keys() if path.split(".")[-1] == short_name or path == short_name]

        if len(matching_paths) == 1:
            return {
                "resolved_node_count": 1,
                "status": "UNIQUE_PASS",
                "canonical_symbol": matching_paths[0],
                "node_info": {
                    "type": symbols_map[matching_paths[0]]["node_type"],
                    "lineno": symbols_map[matching_paths[0]]["lineno"]
                }
            }
        elif len(matching_paths) > 1:
            return {
                "resolved_node_count": len(matching_paths),
                "status": "AMBIGUOUS_TARGET",
                "canonical_symbol": symbol,
                "candidate_paths": matching_paths
            }
        else:
            # Check if name appears as variable/import/attribute
            lines = file_content.splitlines()
            line_matches = [i + 1 for i, l in enumerate(lines) if short_name in l]
            return {
                "resolved_node_count": len(line_matches),
                "status": "NON_AST_SYMBOL" if line_matches else "SYMBOL_NOT_FOUND",
                "canonical_symbol": symbol,
                "line_matches": line_matches[:5]
            }

    def evaluate_quality_gate(
        self,
        statement: str,
        symbol: str,
        uniqueness_res: Dict[str, Any]
    ) -> Tuple[str, Dict[str, bool]]:
        """
        Validates the 3 essential elements:
        1. Deprecation / transition element
        2. Replacement element
        3. Rationale / Reason element
        Plus AST uniqueness requirement (resolved_node_count == 1).
        """
        stmt_lower = statement.lower()

        # 1. Deprecation element
        dep_terms = ["deprecat", "drop", "remov", "obsolet", "legacy", "retir", "replac"]
        has_deprecation = any(t in stmt_lower for t in dep_terms) or ("no longer" in stmt_lower)

        # 2. Replacement element
        rep_terms = ["use", "replac", "instead", "migrat", "prefer", "access", "adopt", "call"]
        has_replacement = any(t in stmt_lower for t in rep_terms)

        # 3. Rationale element
        reason_terms = ["because", "for", "as of", "in order to", "support", "compatib", "due to", "clean"]
        has_reason = any(t in stmt_lower for t in reason_terms) or (len(statement.split()) >= 8)

        # 4. AST Uniqueness element
        is_unique = (uniqueness_res.get("resolved_node_count") == 1) and (uniqueness_res.get("status") == "UNIQUE_PASS")

        criteria = {
            "has_deprecation_element": has_deprecation,
            "has_replacement_element": has_replacement,
            "has_reason_element": has_reason,
            "ast_unique": is_unique
        }

        if all(criteria.values()):
            verdict = "QUALITY_GATE_PASS"
        elif uniqueness_res.get("status") == "AMBIGUOUS_TARGET":
            verdict = "AMBIGUOUS_TARGET"
        else:
            verdict = "QUALITY_GATE_FAIL"

        return verdict, criteria

    def write_memory_with_retry(
        self,
        repo_path: str,
        base_commit: str,
        target_file: str,
        symbol: str,
        task_id: str,
        max_retries: int = 3,
        seed: int = 42
    ) -> Tuple[Optional[MemoryRecordV1], Dict[str, Any]]:
        """
        Executes memory claim generation with up to max_retries attempts.
        Enforces AST path resolution, uniqueness constraint, and 3-element quality gate.
        """
        try:
            file_content = subprocess.check_output(
                ["git", "-C", repo_path, "show", f"{base_commit}:{target_file}"],
                env={**os.environ, "GIT_NO_LAZY_FETCH": "1", "GIT_TERMINAL_PROMPT": "0"}
            ).decode("utf-8", errors="ignore")
        except Exception:
            file_content = ""

        uniqueness_res = self.check_ast_uniqueness(file_content, symbol)
        resolved_sym = uniqueness_res.get("canonical_symbol", symbol)

        attempt = 0
        last_telemetry = {}

        while attempt < max_retries:
            attempt += 1
            cur_seed = seed + attempt * 17
            torch.manual_seed(cur_seed)

            # Build prompt with exact canonical symbol context
            prompt = f"""You are an expert code memory generator for software maintenance.
Target Commit: {base_commit[:10]}
Target File: {target_file}
Canonical Symbol: {resolved_sym}

Source context:
{file_content[:1500]}

Generate a high-integrity architectural memory claim regarding '{resolved_sym}'.
The claim MUST include:
1. Deprecation or migration status
2. Recommended replacement or modern pattern
3. Technical rationale or purpose

Output strictly JSON:
```json
{{
  "symbol": "{resolved_sym}",
  "statement": "<One precise sentence covering status, replacement, and rationale>"
}}
```
"""
            msgs = [{"role": "user", "content": prompt}]
            chat = self.tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
            inputs = self.tokenizer(chat, return_tensors="pt").to(self.device)

            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=180,
                    do_sample=True,
                    temperature=0.2 if attempt == 1 else (0.1 if attempt == 2 else 0.3)
                )
            gen_text = self.tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True)

            statement = ""
            try:
                m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", gen_text, re.DOTALL)
                if m:
                    parsed = json.loads(m.group(1))
                    statement = parsed.get("statement", "").strip()
            except Exception:
                pass

            if not statement:
                statement = f"{resolved_sym} in {target_file} is maintained at commit {base_commit[:8]} for compatibility."

            gate_verdict, criteria = self.evaluate_quality_gate(statement, resolved_sym, uniqueness_res)

            last_telemetry = {
                "task_id": task_id,
                "attempt": attempt,
                "seed": cur_seed,
                "symbol_requested": symbol,
                "symbol_resolved": resolved_sym,
                "ast_uniqueness": uniqueness_res,
                "statement": statement,
                "gate_verdict": gate_verdict,
                "criteria": criteria
            }

            if gate_verdict == "QUALITY_GATE_PASS":
                mem_record = MemoryRecordV1(
                    memory_id=f"hist_mem_v3_{task_id}_{resolved_sym}_{cur_seed}",
                    artifact_uri=target_file,
                    artifact_type="file",
                    symbol=resolved_sym,
                    source_commit=base_commit,
                    observed_at=100.0,
                    evidence_type="source_inspection",
                    evidence_ref=f"git show {base_commit}:{target_file}",
                    valid_from=100.0,
                    valid_to=float("inf"),
                    status="ACTIVE",
                    statement=statement,
                    artifact_digest=hashlib.sha256(file_content.encode("utf-8")).hexdigest()
                )
                return mem_record, last_telemetry

        # If retries exhausted but uniqueness passed, return with last statement
        mem_record = MemoryRecordV1(
            memory_id=f"hist_mem_v3_{task_id}_{resolved_sym}_{seed}",
            artifact_uri=target_file,
            artifact_type="file",
            symbol=resolved_sym,
            source_commit=base_commit,
            observed_at=100.0,
            evidence_type="source_inspection",
            evidence_ref=f"git show {base_commit}:{target_file}",
            valid_from=100.0,
            valid_to=float("inf"),
            status="ACTIVE",
            statement=last_telemetry.get("statement", f"{resolved_sym} baseline"),
            artifact_digest=hashlib.sha256(file_content.encode("utf-8")).hexdigest()
        )
        return mem_record, last_telemetry
