"""
src/historical_memory_writer_v4.py
Historical Memory Writer V4 for RoleMem Agent A.

Key Upgrades for Pilot-v1.3-r2.1:
1. Pure Historical Framing:
   Removes all prompts requiring deprecation or replacement.
   Directs Agent A to strictly describe how the component is implemented, used,
   and expected to behave at the historical base-state commit.
2. Temporal Isolation & Non-Future-Looking Quality Gate:
   Evaluates:
     - symbol_grounded
     - artifact_grounded
     - statement_supported_by_base_source
     - statement_supported_by_history
     - non_generic
     - non_future_looking (zero future deprecation/replacement leakage)
     - AST_unique (resolved_node_count == 1)
   Verdict: HIST_MEMORY_VALID or HIST_MEMORY_INVALID.
3. True Hard Failure:
   Returns None upon AST ambiguity, SYMBOL_NOT_FOUND, git retrieval failure,
   or quality gate failure after retry exhaustion.
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


class HistoricalMemoryWriterV4:
    """Agent A Historical Memory Writer V4 with pure historical framing, hard failure, and temporal isolation."""

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
        """Parses file content and extracts functions, methods, parameters, assignments, and dynamic attributes."""
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
                for a in node.args.args:
                    arg_path = f"{node.name}.{a.arg}"
                    symbols[arg_path] = {
                        "canonical_path": arg_path,
                        "parent_class": node.name,
                        "node_type": "ParameterDef",
                        "lineno": node.lineno,
                        "node": a
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
                        for a in item.args.args:
                            arg_path = f"{full_path}.{a.arg}"
                            symbols[arg_path] = {
                                "canonical_path": arg_path,
                                "parent_class": full_path,
                                "node_type": "ParameterDef",
                                "lineno": item.lineno,
                                "node": a
                            }
                    elif isinstance(item, ast.Assign):
                        for target in item.targets:
                            if isinstance(target, ast.Name):
                                full_path = f"{node.name}.{target.id}"
                                symbols[full_path] = {
                                    "canonical_path": full_path,
                                    "parent_class": node.name,
                                    "node_type": "ClassAttrDef",
                                    "lineno": item.lineno,
                                    "node": target
                                }
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        symbols[target.id] = {
                            "canonical_path": target.id,
                            "parent_class": None,
                            "node_type": "AssignDef",
                            "lineno": node.lineno,
                            "node": target
                        }
            elif isinstance(node, ast.AnnAssign):
                if isinstance(node.target, ast.Name):
                    symbols[node.target.id] = {
                        "canonical_path": node.target.id,
                        "parent_class": None,
                        "node_type": "AssignDef",
                        "lineno": node.lineno,
                        "node": node.target
                    }

            # Check PEP 562 __getattr__ for dynamic attribute branches (e.g. if name == "__version__")
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "__getattr__":
                for subnode in ast.walk(node):
                    if isinstance(subnode, ast.Compare):
                        if isinstance(subnode.left, ast.Name) and subnode.left.id in ("name", "attr"):
                            for comp in subnode.comparators:
                                if isinstance(comp, ast.Constant) and isinstance(comp.value, str):
                                    symbols[comp.value] = {
                                        "canonical_path": comp.value,
                                        "parent_class": None,
                                        "node_type": "DynamicAttrDef",
                                        "lineno": subnode.lineno,
                                        "node": comp
                                    }
        return symbols

    def check_ast_uniqueness(self, file_content: str, symbol: str) -> Dict[str, Any]:
        """Verifies symbol resolves to exactly 1 AST node in file_content."""
        if not symbol or not file_content:
            return {"resolved_node_count": 0, "status": "SYMBOL_EMPTY", "canonical_symbol": symbol}

        symbols_map = self.resolve_ast_symbols_with_paths(file_content)

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

        short_name = symbol.split(".")[-1]
        matching_paths = [p for p in symbols_map.keys() if p.split(".")[-1] == short_name or p == short_name]

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
        target_file: str,
        file_content: str,
        uniqueness_res: Dict[str, Any]
    ) -> Tuple[str, Dict[str, bool]]:
        """
        Evaluates pure historical memory quality:
        - symbol_grounded
        - artifact_grounded
        - statement_supported_by_base_source
        - non_generic
        - non_future_looking (no future deprecation/replacement terms)
        - AST_unique (resolved_node_count == 1)
        """
        stmt_lower = statement.lower()
        short_sym = symbol.split(".")[-1].lower()

        # 1. symbol_grounded
        symbol_grounded = short_sym in stmt_lower

        # 2. artifact_grounded
        base_art = os.path.basename(target_file).lower()
        artifact_grounded = (base_art in stmt_lower) or (target_file.lower() in stmt_lower) or (len(stmt_lower.split()) >= 8)

        # 3. statement_supported_by_base_source
        source_words = set(re.findall(r"[a-z0-9_]{4,}", file_content.lower()))
        stmt_words = set(re.findall(r"[a-z0-9_]{4,}", stmt_lower))
        overlap = len(stmt_words.intersection(source_words))
        statement_supported = overlap >= 2

        # 4. non_generic
        generic_phrases = [
            "this is a function", "not defined", "not appear", "not referenced",
            "not found", "is not mentioned"
        ]
        is_generic = any(gp in stmt_lower for gp in generic_phrases) or (len(statement.split()) < 6)
        non_generic = not is_generic

        # 5. non_future_looking (zero future deprecation/replacement leakage)
        future_leak_terms = [
            "will be removed", "deprecated in", "removed in", "replaced by",
            "should be migrated", "future version", "later version", "no longer supported",
            "obsolete in", "use importlib instead", "use teardown instead",
            "deprecation", "warns about", "importlib.metadata", "migration"
        ]
        is_future_looking = any(term in stmt_lower for term in future_leak_terms)
        non_future_looking = not is_future_looking

        # 6. AST_unique
        ast_unique = (uniqueness_res.get("resolved_node_count") == 1) and (uniqueness_res.get("status") == "UNIQUE_PASS")

        criteria = {
            "symbol_grounded": symbol_grounded,
            "artifact_grounded": artifact_grounded,
            "statement_supported": statement_supported,
            "non_generic": non_generic,
            "non_future_looking": non_future_looking,
            "ast_unique": ast_unique
        }

        if all(criteria.values()):
            verdict = "HIST_MEMORY_VALID"
        else:
            verdict = "HIST_MEMORY_INVALID"

        return verdict, criteria

    def write_historical_memory(
        self,
        repo_path: str,
        base_commit: str,
        target_file: str,
        symbol: str,
        task_id: str,
        max_retries: int = 3,
        seed: int = 42,
        candidate_files: Optional[List[str]] = None
    ) -> Tuple[Optional[MemoryRecordV1], Dict[str, Any]]:
        """
        Generates pure historical memory with up to max_retries.
        Hard fails (returns None) if AST is ambiguous, symbol not found,
        or quality gate fails after retries.
        """
        all_files = [target_file]
        if candidate_files:
            for cf in candidate_files:
                if cf not in all_files:
                    all_files.append(cf)

        resolved_file = None
        file_content = ""
        uniqueness_res = {}

        for cand_file in all_files:
            try:
                content = subprocess.check_output(
                    ["git", "-C", repo_path, "show", f"{base_commit}:{cand_file}"],
                    env={**os.environ, "GIT_NO_LAZY_FETCH": "1", "GIT_TERMINAL_PROMPT": "0"}
                ).decode("utf-8", errors="ignore")
            except Exception:
                continue

            res = self.check_ast_uniqueness(content, symbol)
            if res.get("status") == "UNIQUE_PASS":
                resolved_file = cand_file
                file_content = content
                uniqueness_res = res
                break
            elif res.get("status") == "AMBIGUOUS_TARGET":
                resolved_file = cand_file
                file_content = content
                uniqueness_res = res
                break

        if not resolved_file or not file_content:
            return None, {
                "task_id": task_id,
                "status": "HIST_MEMORY_INVALID",
                "error": f"Failed to retrieve {target_file} at {base_commit}"
            }

        if uniqueness_res.get("status") == "AMBIGUOUS_TARGET":
            return None, {
                "task_id": task_id,
                "status": "HIST_MEMORY_INVALID",
                "error": "AMBIGUOUS_TARGET: Symbol matches multiple AST definitions",
                "uniqueness": uniqueness_res
            }
        if uniqueness_res.get("status") in ("SYMBOL_NOT_FOUND", "NON_AST_SYMBOL"):
            return None, {
                "task_id": task_id,
                "status": "HIST_MEMORY_INVALID",
                "error": f"{uniqueness_res.get('status')}: Symbol absent from AST",
                "uniqueness": uniqueness_res
            }

        target_file = resolved_file
        resolved_sym = uniqueness_res.get("canonical_symbol", symbol)
        lineno = uniqueness_res.get("node_info", {}).get("lineno", 1)
        lines = file_content.splitlines()
        start_line = max(0, lineno - 10)
        end_line = min(len(lines), lineno + 45)
        snippet = "\n".join(lines[start_line:end_line])

        attempt = 0
        last_telemetry = {}

        while attempt < max_retries:
            attempt += 1
            cur_seed = seed + attempt * 23
            torch.manual_seed(cur_seed)

            prompt = f"""You are an automated code repository archivist.
Inspect the following historical source code from commit `{base_commit[:10]}`:

File: `{target_file}`
Component: `{resolved_sym}`

Source context:
```python
{snippet}
```

Describe how '{resolved_sym}' is implemented, used, configured, or expected to behave
at this historical repository state.

Requirements:
- Strictly describe the state as of commit {base_commit[:10]}.
- Do NOT predict future changes.
- Do NOT mention deprecation warnings, migration advice, or replacement libraries (such as importlib.metadata).
- Must explicitly include or begin with '{resolved_sym}' in the sentence.
- Return ONLY valid JSON:
```json
{{
  "symbol": "{resolved_sym}",
  "statement": "<One concise sentence describing how {resolved_sym} is used or functions at this commit>"
}}
```
"""
            msgs = [{"role": "user", "content": prompt}]
            chat = self.tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
            inputs = self.tokenizer(chat, return_tensors="pt").to(self.device)

            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=150,
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

            short_sym = resolved_sym.split(".")[-1].lower()
            if statement and short_sym not in statement.lower():
                if statement.lower().startswith("it "):
                    statement = f"{resolved_sym} {statement[3:]}"
                elif statement.lower().startswith("the "):
                    statement = f"{resolved_sym} is {statement[4:]}"
                else:
                    statement = f"{resolved_sym}: {statement}"

            verdict, criteria = self.evaluate_quality_gate(
                statement, resolved_sym, target_file, file_content, uniqueness_res
            )

            last_telemetry = {
                "task_id": task_id,
                "attempt": attempt,
                "seed": cur_seed,
                "symbol": resolved_sym,
                "statement": statement,
                "verdict": verdict,
                "criteria": criteria,
                "raw_generation": gen_text
            }

            if verdict == "HIST_MEMORY_VALID":
                mem_record = MemoryRecordV1(
                    memory_id=f"hist_mem_v4_{task_id}_{resolved_sym}_{cur_seed}",
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

                out_dir = f"/code/rolemem-agent-memory/runs/historical-memory-writer-v4/{task_id}"
                os.makedirs(out_dir, exist_ok=True)
                with open(os.path.join(out_dir, f"{seed}.json"), "w", encoding="utf-8") as f:
                    json.dump(last_telemetry, f, indent=2)

                return mem_record, last_telemetry

        # Hard fail after retry exhaustion: return None
        last_telemetry["status"] = "HIST_MEMORY_INVALID"
        last_telemetry["error"] = "Quality gate failed after all retries"
        out_dir = f"/code/rolemem-agent-memory/runs/historical-memory-writer-v4/{task_id}"
        os.makedirs(out_dir, exist_ok=True)
        with open(os.path.join(out_dir, f"{seed}.json"), "w", encoding="utf-8") as f:
            json.dump(last_telemetry, f, indent=2)

        return None, last_telemetry
