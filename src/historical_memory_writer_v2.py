"""
src/historical_memory_writer_v2.py
Historical Memory Writer V2 for RoleMem Agent A.

Key Enhancements:
1. AST Symbol Resolution: Precise AST visitor/search for target symbol (classes, functions, methods, assignments),
   extracting signature, docstring, and exact AST code slice.
2. History Context: Retrieves up to 5 recent commit logs for the specific target file up to base commit (git log -n 5).
3. Quality Gating: Evaluates parsed output into HIST_MEMORY_VALID or HIST_MEMORY_LOW_QUALITY.
4. Strict Base Boundary: Zero foresight beyond base_commit.
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


class HistoricalMemoryWriterV2:
    """Agent A Historical Memory Writer V2 with AST resolution, file commit history, and quality gating."""

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

    def resolve_ast_symbol(self, file_content: str, symbol: Optional[str]) -> Dict[str, Any]:
        """Precise AST symbol resolution to find definitions, signatures, and docstrings."""
        if not symbol or not file_content:
            return {"resolved": False, "snippet": file_content[:3000]}

        short_sym = symbol.split(".")[-1]
        parent_sym = symbol.split(".")[0] if "." in symbol else None

        try:
            tree = ast.parse(file_content)
        except Exception:
            # Fallback to line searching if syntax error
            lines = file_content.splitlines()
            sym_indices = [i for i, line in enumerate(lines) if short_sym in line]
            if sym_indices:
                idx = sym_indices[0]
                snippet = "\n".join(lines[max(0, idx - 10):min(len(lines), idx + 50)])
            else:
                snippet = "\n".join(lines[:60])
            return {"resolved": False, "snippet": snippet, "method": "line_fallback"}

        # Search AST
        matching_node = None
        docstring = None
        args_list = []

        if parent_sym:
            # Search within class
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and node.name == parent_sym:
                    for item in node.body:
                        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name == short_sym:
                            matching_node = item
                            docstring = ast.get_docstring(item)
                            args_list = [a.arg for a in item.args.args]
                            break
                    if matching_node:
                        break

        if not matching_node:
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.name == short_sym:
                    matching_node = node
                    docstring = ast.get_docstring(node)
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        args_list = [a.arg for a in node.args.args]
                    break

        if matching_node:
            segment = ast.get_source_segment(file_content, matching_node)
            if not segment:
                lines = file_content.splitlines()
                start = getattr(matching_node, "lineno", 1) - 1
                end = getattr(matching_node, "end_lineno", min(len(lines), start + 60))
                segment = "\n".join(lines[start:end])
            return {
                "resolved": True,
                "node_type": type(matching_node).__name__,
                "name": short_sym,
                "args": args_list,
                "docstring": docstring,
                "snippet": segment[:4000],
                "method": "ast_parse"
            }

        # Symbol not directly defined as class/func (maybe variable or import)
        lines = file_content.splitlines()
        sym_indices = [i for i, line in enumerate(lines) if short_sym in line]
        if sym_indices:
            idx = sym_indices[0]
            snippet = "\n".join(lines[max(0, idx - 10):min(len(lines), idx + 50)])
        else:
            snippet = "\n".join(lines[:60])
        return {"resolved": False, "snippet": snippet, "method": "line_search"}

    def get_base_state_evidence(
        self,
        repo_path: str,
        base_commit: str,
        target_file: str,
        symbol: Optional[str] = None
    ) -> Dict[str, Any]:
        """Extract repository state and history strictly visible as of base_commit."""
        # 1. Base commit summary
        base_msg = subprocess.check_output(
            ["git", "-C", repo_path, "log", "-1", "--format=%B", base_commit],
            env={**os.environ, "GIT_NO_LAZY_FETCH": "1", "GIT_TERMINAL_PROMPT": "0"}
        ).decode("utf-8", errors="ignore").strip()

        # 2. History context: last 5 commits touching target_file up to base_commit
        try:
            file_history = subprocess.check_output(
                ["git", "-C", repo_path, "log", "-n", "5", "--format=%h - %s", base_commit, "--", target_file],
                env={**os.environ, "GIT_NO_LAZY_FETCH": "1", "GIT_TERMINAL_PROMPT": "0"},
                stderr=subprocess.DEVNULL
            ).decode("utf-8", errors="ignore").strip()
        except Exception:
            file_history = base_msg

        # 3. File content at base commit
        file_content = subprocess.check_output(
            ["git", "-C", repo_path, "show", f"{base_commit}:{target_file}"],
            env={**os.environ, "GIT_NO_LAZY_FETCH": "1", "GIT_TERMINAL_PROMPT": "0"},
            stderr=subprocess.DEVNULL
        ).decode("utf-8", errors="ignore")

        # 4. Artifact digest
        digest = hashlib.sha256(file_content.encode("utf-8")).hexdigest()

        # 5. AST symbol resolution
        ast_info = self.resolve_ast_symbol(file_content, symbol)

        return {
            "base_commit": base_commit,
            "target_file": target_file,
            "base_commit_msg": base_msg,
            "file_history": file_history,
            "ast_info": ast_info,
            "code_context": ast_info["snippet"],
            "artifact_digest": digest
        }

    def evaluate_quality_gate(self, statement: str, symbol: str, is_parsed: bool) -> Tuple[str, Dict[str, Any]]:
        """Determines HIST_MEMORY_VALID vs HIST_MEMORY_LOW_QUALITY."""
        short_sym = symbol.split(".")[-1] if symbol else ""
        has_symbol = short_sym.lower() in statement.lower() if short_sym else True
        has_len = len(statement.strip()) >= 15
        no_fallback = not statement.startswith("At commit")

        criteria = {
            "is_parsed_json": is_parsed,
            "symbol_mentioned": has_symbol,
            "sufficient_length": has_len,
            "not_fallback_placeholder": no_fallback
        }

        if is_parsed and has_symbol and has_len and no_fallback:
            return "HIST_MEMORY_VALID", criteria
        return "HIST_MEMORY_LOW_QUALITY", criteria

    def generate_historical_memory_v2(
        self,
        repo_path: str,
        base_commit: str,
        target_file: str,
        symbol: str,
        seed: int = 42,
        task_id: str = "task"
    ) -> Tuple[MemoryRecordV1, Dict[str, Any]]:
        """Runs Agent A to generate historical memory with AST resolution and quality gating."""
        torch.manual_seed(seed)
        evidence = self.get_base_state_evidence(repo_path, base_commit, target_file, symbol)

        prompt = f"""You are an automated code memory writer for a software development system.
You are inspecting the repository as of commit `{base_commit}`.
Target File: `{target_file}`
Target Component: `{symbol}`

[Recent File History]
{evidence['file_history']}

[Component Source Snippet]
```python
{evidence['code_context']}
```

Analyze how `{symbol}` is implemented and intended to be used at this commit.
Provide a single concise sentence describing its usage or convention as of this commit.

Requirements:
- You must strictly describe the code above at commit {base_commit}.
- Do NOT hypothesize future changes or deprecations.
- Return ONLY valid JSON:
```json
{{
  "artifact_uri": "{target_file}",
  "symbol": "{symbol}",
  "statement": "<Concise sentence describing how {symbol} is used at this commit>",
  "evidence_ref": "git show {base_commit}:{target_file}"
}}
```
"""

        msgs = [{"role": "user", "content": prompt}]
        chat = self.tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
        inputs = self.tokenizer(chat, return_tensors="pt").to(self.device)

        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=220,
                do_sample=True,
                temperature=0.2
            )

        gen_text = self.tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True)

        # Parse JSON
        is_parsed = False
        parsed_claim = {}
        try:
            m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", gen_text, re.DOTALL)
            if m:
                parsed_claim = json.loads(m.group(1))
                is_parsed = True
            else:
                m2 = re.search(r'\{[^{}]*"statement"[^{}]*\}', gen_text, re.DOTALL)
                if m2:
                    parsed_claim = json.loads(m2.group(0))
                    is_parsed = True
        except Exception:
            is_parsed = False

        statement = parsed_claim.get("statement", "").strip()
        if not statement:
            statement = f"At commit {base_commit[:8]}, {symbol} in {target_file} provides baseline functionality."

        quality_gate, gate_criteria = self.evaluate_quality_gate(statement, symbol, is_parsed)

        mem_record = MemoryRecordV1(
            memory_id=f"hist_mem_v2_{task_id}_{symbol}_{seed}",
            artifact_uri=target_file,
            artifact_type="file",
            symbol=symbol,
            source_commit=base_commit,
            observed_at=100.0,
            evidence_type="source_inspection",
            evidence_ref=f"git show {base_commit}:{target_file}",
            valid_from=100.0,
            valid_to=float("inf"),
            status="ACTIVE",
            statement=statement,
            artifact_digest=evidence["artifact_digest"]
        )

        telemetry = {
            "task_id": task_id,
            "seed": seed,
            "base_commit": base_commit,
            "target_file": target_file,
            "symbol": symbol,
            "ast_resolution": evidence["ast_info"],
            "file_history": evidence["file_history"],
            "raw_prompt": prompt,
            "raw_generation": gen_text,
            "parsed_statement": statement,
            "quality_gate": quality_gate,
            "quality_criteria": gate_criteria,
            "artifact_digest": evidence["artifact_digest"]
        }

        out_dir = f"/code/rolemem-agent-memory/runs/historical-memory-writer-v2/{task_id}"
        os.makedirs(out_dir, exist_ok=True)
        with open(os.path.join(out_dir, f"{seed}.json"), "w", encoding="utf-8") as f:
            json.dump(telemetry, f, indent=2)

        return mem_record, telemetry
