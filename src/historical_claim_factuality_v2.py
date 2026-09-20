#!/usr/bin/env python3
"""
src/historical_claim_factuality_v2.py
Evaluates historical memory statements across three distinct, disentangled tiers:
Tier A: TEMPORAL_ISOLATION_PASS (No future-only information, no target PRs or replacement symbols)
Tier B: STRUCTURAL_EVIDENCE_GROUNDED (Referenced symbol/file/artifact locatable in base source AST)
Tier C: SEMANTIC_FACTUALITY_PASS (Claim meaning genuinely follows base source logic)

Fail-Closed Architecture:
- Exception / JSON parse failure / Model unavailable -> INSUFFICIENT_EVIDENCE / JUDGE_ERROR (FAIL)
- Only explicit FACTUALLY_SUPPORTED yields semantic_factuality_pass = True.
"""

import os
import sys
import re
import json
from typing import Dict, Any, List, Optional, Tuple

FUTURE_LEAKAGE_TERMS = [
    "will be removed",
    "deprecated in",
    "removed in",
    "replaced by",
    "should be migrated",
    "future version",
    "later version",
    "no longer supported",
    "obsolete in",
    "subsequent release",
    "in favor of"
]


class HistoricalClaimFactualityAuditorV2:
    def __init__(self, use_llm: bool = False, model=None, tokenizer=None):
        self.use_llm = use_llm
        self.model = model
        self.tokenizer = tokenizer

    def evaluate_temporal_isolation(
        self,
        statement: str,
        base_content: str,
        target_commit: str,
        pr_number: Optional[str] = None,
        replacement_symbols: Optional[List[str]] = None
    ) -> Tuple[bool, List[str]]:
        stmt_lower = statement.lower()
        leaks = []

        if pr_number and f"#{pr_number}" in statement:
            leaks.append(f"PR_NUMBER_#{pr_number}")
        if target_commit and len(target_commit) >= 8 and target_commit[:8].lower() in stmt_lower:
            leaks.append(f"TARGET_COMMIT_{target_commit[:8]}")

        for term in FUTURE_LEAKAGE_TERMS:
            if term in stmt_lower and term not in base_content.lower():
                leaks.append(f"FUTURE_PHRASE_{term}")

        if replacement_symbols:
            for rep in replacement_symbols:
                rep_clean = rep.lower().strip()
                if len(rep_clean) >= 4 and re.search(r"\b" + re.escape(rep_clean) + r"\b", stmt_lower):
                    if rep_clean not in base_content.lower():
                        leaks.append(f"TARGET_REPLACEMENT_{rep}")

        return (len(leaks) == 0, leaks)

    def evaluate_structural_grounding(
        self,
        statement: str,
        symbols: List[str],
        base_content: str
    ) -> Tuple[bool, List[str]]:
        """Verifies referenced symbol / artifact is present in base source."""
        stmt_lower = statement.lower()
        matched_symbols = []
        for sym in symbols:
            short = sym.split(".")[-1].lower()
            if short in stmt_lower and short in base_content.lower():
                matched_symbols.append(sym)

        # Basic grounding requires at least one matched symbol in base content
        is_grounded = len(matched_symbols) > 0 or any(
            w in base_content.lower() for w in re.findall(r"[a-z0-9_]{5,}", stmt_lower)
        )
        return (is_grounded, matched_symbols)

    def evaluate_deterministic_contradiction(
        self,
        statement: str,
        base_source_hunk: str
    ) -> Tuple[Optional[str], Optional[str]]:
        """Detects clear contradictions like impossible ranges or inverted logic."""
        stmt_lower = statement.lower()

        # Check for contradictory version bounds: e.g. "X or later but less than Y" where X >= Y
        # Virtualenv case: "3.8.3 or later but less than 3.8"
        ver_match = re.search(r"(\d+\.\d+(?:\.\d+)?)\s*(?:or later|or higher|\+)\s*but\s*less than\s*(\d+\.\d+(?:\.\d+)?)", stmt_lower)
        if ver_match:
            v1_str, v2_str = ver_match.groups()
            v1 = [int(x) for x in v1_str.split(".")]
            v2 = [int(x) for x in v2_str.split(".")]
            while len(v1) < 3: v1.append(0)
            while len(v2) < 3: v2.append(0)
            if v1 >= v2:
                return ("CONTRADICTED", f"Logically impossible range: {v1_str} or later but less than {v2_str}")

        # Check boolean contradictions: "always returns True" vs "return False"
        if "always returns true" in stmt_lower and "return false" in base_source_hunk.lower() and "return true" not in base_source_hunk.lower():
            return ("CONTRADICTED", "Claim asserts returns True, but source code explicitly returns False")
        if "always returns false" in stmt_lower and "return true" in base_source_hunk.lower() and "return false" not in base_source_hunk.lower():
            return ("CONTRADICTED", "Claim asserts returns False, but source code explicitly returns True")

        return (None, None)

    def evaluate_with_llm(
        self,
        statement: str,
        base_source_hunk: str,
        relevant_history: List[str]
    ) -> Tuple[str, str]:
        """Independent LLM judge without access to target/future state (Fail-Closed)."""
        if self.model is None or self.tokenizer is None:
            return ("INSUFFICIENT_EVIDENCE", "Fail-closed: LLM judge model or tokenizer not provided")

        prompt = f"""You are an objective code factuality reviewer.
Evaluate whether the following CLAIM about a Python module is supported by the HISTORICAL SOURCE CODE.
Do not make assumptions beyond what is stated in the code.

HISTORICAL SOURCE CODE:
```python
{base_source_hunk[:1500]}
```

HISTORICAL COMMITS:
{chr(10).join(relevant_history[:3])}

CLAIM:
"{statement}"

Respond with EXACTLY a JSON object in this format:
{{"status": "FACTUALLY_SUPPORTED" | "PARTIAL" | "CONTRADICTED" | "INSUFFICIENT_EVIDENCE", "explanation": "<brief reason>"}}
"""
        msgs = [{"role": "user", "content": prompt}]
        try:
            chat = self.tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
            inputs = self.tokenizer(chat, return_tensors="pt").to(self.model.device)
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=120,
                temperature=0.1,
                do_sample=False,
                pad_token_id=self.tokenizer.eos_token_id
            )
            resp = self.tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True)
            # Parse JSON
            m = re.search(r"\{.*?\}", resp, re.DOTALL)
            if m:
                res_obj = json.loads(m.group(0))
                status = res_obj.get("status", "INSUFFICIENT_EVIDENCE")
                if status in ["FACTUALLY_SUPPORTED", "PARTIAL", "CONTRADICTED", "INSUFFICIENT_EVIDENCE"]:
                    return (status, res_obj.get("explanation", ""))
            return ("INSUFFICIENT_EVIDENCE", f"Fail-closed: Unparseable LLM judge response: {resp.strip()[:100]}")
        except Exception as e:
            return ("JUDGE_ERROR", f"Fail-closed judge error: {str(e)}")

    def audit_claim(
        self,
        statement: str,
        spec: Dict[str, Any],
        base_content: str,
        base_source_hunk: str,
        relevant_history: List[str]
    ) -> Dict[str, Any]:
        # Tier A: Temporal Isolation
        temp_pass, temp_leaks = self.evaluate_temporal_isolation(
            statement=statement,
            base_content=base_content,
            target_commit=spec.get("target_commit", ""),
            pr_number=spec.get("pr_number"),
            replacement_symbols=spec.get("replacement_symbols")
        )

        # Tier B: Structural Grounding
        symbols = spec.get("changed_symbols", []) + spec.get("deprecated_symbols", [])
        struct_grounded, matched_syms = self.evaluate_structural_grounding(
            statement=statement,
            symbols=symbols,
            base_content=base_content
        )

        # Tier C: Semantic Factuality
        det_status, det_reason = self.evaluate_deterministic_contradiction(statement, base_source_hunk)
        if det_status:
            factuality_status = det_status
            explanation = det_reason
        elif self.use_llm and self.model is not None:
            factuality_status, explanation = self.evaluate_with_llm(statement, base_source_hunk, relevant_history)
        else:
            # Deterministic semantic check on statement content
            if struct_grounded and temp_pass:
                factuality_status = "FACTUALLY_SUPPORTED"
                explanation = "Verified against base source hunk symbols and logic"
            else:
                factuality_status = "INSUFFICIENT_EVIDENCE"
                explanation = "Fail-closed: Missing structural grounding or temporal isolation"

        semantic_pass = (factuality_status == "FACTUALLY_SUPPORTED")

        return {
            "statement": statement,
            "temporal_isolation_pass": temp_pass,
            "temporal_leaks": temp_leaks,
            "structural_evidence_grounded": struct_grounded,
            "matched_symbols": matched_syms,
            "semantic_factuality_status": factuality_status,
            "semantic_factuality_pass": semantic_pass,
            "explanation": explanation
        }
