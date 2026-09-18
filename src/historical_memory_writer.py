"""
src/historical_memory_writer.py
Real Agent A Historical Memory Writer for RoleMem.

Strict Boundary:
- Agent A only observes repository state as of base commit (commit <= base_commit).
- Zero visibility into target commit, future diffs, valid/stale candidate labels, or hidden tests.
- Extracts historical usage, signature, or design conventions of the component at base commit.
- Saves telemetry to runs/historical-memory-writer/<task>/<seed>.json.
"""

import os
import sys
import json
import re
import hashlib
import subprocess
import torch
from typing import Dict, Any, List, Optional, Tuple

sys.path.insert(0, "/code/rolemem-agent-memory")
from src.schema_v1 import MemoryRecordV1
from transformers import AutoTokenizer, AutoModelForCausalLM


class HistoricalMemoryWriter:
    """Agent A Historical Memory Writer generating baseline memories strictly from base commit state."""

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

    def get_base_state_evidence(
        self,
        repo_path: str,
        base_commit: str,
        target_file: str,
        symbol: Optional[str] = None
    ) -> Dict[str, Any]:
        """Extract only repository state visible at or before base_commit."""
        # 1. Commit message of base commit
        base_msg = subprocess.check_output(
            ["git", "-C", repo_path, "log", "-1", "--format=%B", base_commit]
        ).decode("utf-8", errors="ignore").strip()

        # 2. File content at base commit
        file_content = subprocess.check_output(
            ["git", "-C", repo_path, "show", f"{base_commit}:{target_file}"],
            stderr=subprocess.DEVNULL
        ).decode("utf-8", errors="ignore")

        # 3. Artifact digest
        digest = hashlib.sha256(file_content.encode("utf-8")).hexdigest()

        # Extract relevant code slice around symbol if file is large
        code_context = file_content
        if len(code_context) > 12000 and symbol:
            lines = code_context.splitlines()
            sym_indices = [i for i, line in enumerate(lines) if symbol in line]
            if sym_indices:
                idx = sym_indices[0]
                start_l = max(0, idx - 40)
                end_l = min(len(lines), idx + 120)
                code_context = "\n".join(lines[start_l:end_l])
            else:
                code_context = "\n".join(lines[:150])
        elif len(code_context) > 12000:
            code_context = "\n".join(code_context.splitlines()[:150])

        return {
            "base_commit": base_commit,
            "target_file": target_file,
            "base_commit_msg": base_msg,
            "code_context": code_context,
            "artifact_digest": digest
        }

    def generate_historical_memory(
        self,
        repo_path: str,
        base_commit: str,
        target_file: str,
        symbol: str,
        seed: int = 42,
        task_id: str = "task"
    ) -> Tuple[MemoryRecordV1, Dict[str, Any]]:
        """
        Runs Agent A to generate historical memory without any future foresight.
        """
        torch.manual_seed(seed)
        evidence = self.get_base_state_evidence(repo_path, base_commit, target_file, symbol)

        prompt = f"""You are an expert software engineer and automated memory writer for a development assistant.
You are inspecting the repository at commit `{base_commit}`.
Below is the historical source code of `{target_file}` and the recent commit log as of `{base_commit}`.

Analyze how the component `{symbol}` is implemented, structured, or used at this commit.
Record a concise, single-sentence architectural or usage memory describing how other agents should invoke or interact with `{symbol}` based strictly on this code.

CRITICAL INSTRUCTIONS:
- You must ONLY describe the behavior and API visible in the code below.
- Do NOT speculate about future changes, deprecations, or replacements.
- Format your response as a valid JSON object:
```json
{{
  "artifact_uri": "{target_file}",
  "symbol": "{symbol}",
  "statement": "<Concise statement of how {symbol} is used or structured at this commit>",
  "evidence_ref": "git show {base_commit}:{target_file}"
}}
```

Source code of `{target_file}` at commit `{base_commit}`:
```python
{evidence['code_context']}
```

Commit message at `{base_commit}`:
{evidence['base_commit_msg']}
"""

        msgs = [{"role": "user", "content": prompt}]
        chat = self.tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
        inputs = self.tokenizer(chat, return_tensors="pt").to(self.device)

        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=250,
                do_sample=True,
                temperature=0.2
            )

        gen_text = self.tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True)

        # Parse JSON output
        parsed_claim = {}
        try:
            match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", gen_text, re.DOTALL)
            if match:
                parsed_claim = json.loads(match.group(1))
            else:
                match2 = re.search(r"\{[^{}]*\"statement\"[^{}]*\}", gen_text, re.DOTALL)
                if match2:
                    parsed_claim = json.loads(match2.group(0))
        except Exception:
            parsed_claim = {}

        statement = parsed_claim.get("statement", "").strip()
        if not statement:
            statement = f"At commit {base_commit[:8]}, {symbol} in {target_file} provides historical functionality."

        mem_record = MemoryRecordV1(
            memory_id=f"hist_mem_{task_id}_{symbol}_{seed}",
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
            "raw_prompt": prompt,
            "visible_repository_evidence": {
                "base_commit_msg": evidence["base_commit_msg"],
                "code_context_snippet": evidence["code_context"][:500],
                "artifact_digest": evidence["artifact_digest"]
            },
            "raw_generation": gen_text,
            "parsed_memory": {
                "artifact_uri": target_file,
                "symbol": symbol,
                "statement": statement,
                "evidence_ref": f"git show {base_commit}:{target_file}"
            },
            "evidence_refs": [f"git show {base_commit}:{target_file}"],
            "artifact_digest": evidence["artifact_digest"]
        }

        # Persist to runs/historical-memory-writer/<task>/<seed>.json
        out_dir = f"/code/rolemem-agent-memory/runs/historical-memory-writer/{task_id}"
        os.makedirs(out_dir, exist_ok=True)
        out_file = os.path.join(out_dir, f"{seed}.json")
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(telemetry, f, indent=2)

        return mem_record, telemetry
