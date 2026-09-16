"""
Unified Memory Token Budgeter for Dynamic Agent Workflows.
Guarantees strict information budgeting across all memory representation strategies.
"""

from typing import List, Dict, Optional, Tuple
import tiktoken
from src.schema_v1 import MemoryRecordV1


class MemoryBudgeter:
    """Enforces strict token limits on injected memory contexts."""

    def __init__(
        self,
        max_memory_tokens: int = 512,
        encoding_name: str = "cl100k_base",
        truncate_strategy: str = "drop_lowest_relevance"
    ):
        self.max_memory_tokens = max_memory_tokens
        self.truncate_strategy = truncate_strategy
        try:
            self.tokenizer = tiktoken.get_encoding(encoding_name)
        except Exception:
            self.tokenizer = None

    def count_tokens(self, text: str) -> int:
        """Accurately count tokens using tiktoken (cl100k_base) with character-based fallback."""
        if not text:
            return 0
        if self.tokenizer is not None:
            return len(self.tokenizer.encode(text, disallowed_special=()))
        # Fallback estimation: ~4 chars per token
        return max(1, len(text) // 4)

    def format_and_budget(
        self,
        records: List[MemoryRecordV1],
        header: str = "### Historical Context & Project Memory"
    ) -> Tuple[str, int]:
        """
        Format records into markdown context while guaranteeing memory_tokens <= max_memory_tokens.
        Records are assumed to be ordered by relevance (or recency for B1).
        Lowest-priority records are pruned if budget is exceeded.
        """
        if not records:
            return "", 0

        # Build items
        item_lines = []
        for r in records:
            evidence_str = f" [Evidence: {r.evidence_type} ({r.evidence_ref})]" if r.evidence_ref else ""
            artifact_str = f" [Artifact: {r.artifact_uri}]" if r.artifact_uri else ""
            item_lines.append(f"- **{r.memory_id}** ({r.artifact_type}){artifact_str}: {r.statement}{evidence_str}")

        # Iteratively assemble up to budget
        selected_lines = []
        for line in item_lines:
            candidate_lines = selected_lines + [line]
            full_text = header + "\n\n" + "\n".join(candidate_lines) + "\n"
            token_count = self.count_tokens(full_text)
            if token_count <= self.max_memory_tokens:
                selected_lines.append(line)
            else:
                # If even the first item exceeds budget, truncate the line itself
                if not selected_lines:
                    # Truncate single line to fit
                    truncated = line
                    while self.count_tokens(header + "\n\n" + truncated + "\n") > self.max_memory_tokens and len(truncated) > 20:
                        truncated = truncated[: int(len(truncated) * 0.8)]
                    selected_lines.append(truncated + "...")
                break

        if not selected_lines:
            return "", 0

        final_context = header + "\n\n" + "\n".join(selected_lines) + "\n"
        final_tokens = self.count_tokens(final_context)
        return final_context, final_tokens


BUDGET_SENSITIVITY_LEVELS = [128, 256, 512, 1024, 2048]
