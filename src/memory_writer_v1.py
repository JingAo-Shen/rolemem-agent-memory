"""
src/memory_writer_v1.py
Real Agent A Memory Writer for RoleMem.
Receives raw Git commit diff and commit log (with distractor hunks, docs, tests),
generates structured memory claims using Qwen2.5-Coder-7B,
and binds them to real repository artifact digests computed via git show.
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


class RealAgentAMemoryWriter:
    """Agent A Memory Writer extracting verified memory claims from raw git commit diffs."""

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

    def compute_file_digest(self, repo_path: str, commit_hash: str, file_path: str) -> Optional[str]:
        """Compute real SHA256 digest of file at commit using git show."""
        try:
            content = subprocess.check_output(
                ["git", "-C", repo_path, "show", f"{commit_hash}:{file_path}"],
                stderr=subprocess.DEVNULL
            )
            return hashlib.sha256(content).hexdigest()
        except subprocess.CalledProcessError:
            return None

    def get_commit_context(self, repo_path: str, base_commit: str, target_commit: str) -> Dict[str, Any]:
        """Extract commit message, raw diff including distractors, and changed files."""
        msg = subprocess.check_output(
            ["git", "-C", repo_path, "log", "-1", "--format=%B", target_commit]
        ).decode("utf-8", errors="ignore").strip()

        # Full diff including distractors (docs, release notes, tests)
        raw_diff = subprocess.check_output(
            ["git", "-C", repo_path, "diff", f"{base_commit}..{target_commit}"]
        ).decode("utf-8", errors="ignore")

        changed_files = subprocess.check_output(
            ["git", "-C", repo_path, "diff", "--name-only", f"{base_commit}..{target_commit}"]
        ).decode("utf-8", errors="ignore").strip().splitlines()

        # Limit diff size to fit LLM context while retaining full primary code changes
        if len(raw_diff) > 10000:
            lines = raw_diff.splitlines()
            code_lines = []
            other_lines = []
            curr_file = ""
            for l in lines:
                if l.startswith("diff --git"):
                    curr_file = l
                if "src/" in curr_file or "urllib3/" in curr_file or "requests/" in curr_file:
                    code_lines.append(l)
                else:
                    other_lines.append(l)
            # Combine code hunks + distractor hunks up to 10000 chars
            combined = "\n".join(code_lines)
            remaining_budget = 10000 - len(combined)
            if remaining_budget > 500:
                combined += "\n" + "\n".join(other_lines)[:remaining_budget]
            raw_diff = combined

        return {
            "commit_msg": msg,
            "raw_diff": raw_diff,
            "changed_files": changed_files
        }

    def generate_memory_claims(
        self,
        repo_path: str,
        base_commit: str,
        target_commit: str,
        seed: int = 42
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Agent A analyzes raw diff and commit log.
        No access to oracle memory candidates or test specs.
        """
        ctx = self.get_commit_context(repo_path, base_commit, target_commit)
        commit_msg = ctx["commit_msg"]
        raw_diff = ctx["raw_diff"]

        prompt = f"""You are an expert software engineer and memory writer for an automated development system.
Analyze the following Git commit message and diff from the repository.
Your task is to identify and record key API changes, deprecations, replacements, or architectural shifts that future agents working on this codebase must know to avoid using obsolete APIs.

CRITICAL INSTRUCTIONS:
- Ignore superficial documentation formatting, release notes changelog lines, and internal test harness changes unless they represent a public API transition.
- Focus strictly on source code API changes (deprecations, renames, replacements).
- For each genuine API change or deprecation, extract:
  * "artifact_uri": relative file path of the modified source file (e.g., "src/werkzeug/utils.py")
  * "symbol": name of the deprecated, modified, or introduced function/class/method
  * "claim_type": "DEPRECATION", "REPLACEMENT", or "ARCHITECTURAL_DECISION"
  * "statement": a concise, actionable statement explaining what is deprecated/changed and what replacement should be used instead
  * "evidence_ref": the file path and brief line description where this change is visible in the diff

[COMMIT MESSAGE]
{commit_msg}

[GIT DIFF]
{raw_diff}

Respond ONLY with a valid JSON object inside ```json ``` code block in this exact schema:
```json
{{
  "claims": [
    {{
      "artifact_uri": "path/to/file.py",
      "symbol": "function_or_class_name",
      "claim_type": "DEPRECATION",
      "statement": "Explanation of the change and recommended replacement",
      "evidence_ref": "path/to/file.py"
    }}
  ]
}}
```
"""
        msgs = [{"role": "user", "content": prompt}]
        chat = self.tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
        inputs = self.tokenizer(chat, return_tensors="pt").to(self.device)

        torch.manual_seed(seed)
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=500,
                do_sample=True,
                temperature=0.2
            )

        gen_text = self.tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True)

        # Parse JSON
        claims = []
        try:
            if "```json" in gen_text:
                json_str = gen_text.split("```json")[1].split("```")[0].strip()
            elif "```" in gen_text:
                json_str = gen_text.split("```")[1].split("```")[0].strip()
            else:
                json_str = gen_text.strip()
            parsed = json.loads(json_str)
            claims = parsed.get("claims", [])
        except Exception as e:
            print(f"Warning: Failed to parse JSON from generation: {e}")
            claims = []

        return gen_text, claims

    def build_memory_records(
        self,
        task_id: str,
        repo_path: str,
        base_commit: str,
        target_commit: str,
        claims: List[Dict[str, Any]]
    ) -> List[MemoryRecordV1]:
        """Transform raw extracted claims into verified MemoryRecordV1 objects with artifact hashes."""
        records = []
        for i, c in enumerate(claims):
            artifact_uri = c.get("artifact_uri", "")
            target_digest = self.compute_file_digest(repo_path, target_commit, artifact_uri)
            base_digest = self.compute_file_digest(repo_path, base_commit, artifact_uri)

            rec = MemoryRecordV1(
                memory_id=f"mem_writer_{task_id}_{i+1}",
                artifact_uri=artifact_uri,
                artifact_type="file",
                symbol=c.get("symbol"),
                source_commit=target_commit,
                observed_at=200.0,
                evidence_type="diff_analysis",
                evidence_ref=c.get("evidence_ref", artifact_uri),
                valid_from=200.0,
                valid_to=float("inf"),
                status="ACTIVE",
                role_tags=["coder", "architect"],
                statement=c.get("statement", ""),
                artifact_digest=target_digest
            )
            records.append(rec)
        return records
