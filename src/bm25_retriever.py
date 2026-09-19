"""
src/bm25_retriever.py
Self-contained, deterministic BM25Okapi repository context retriever for RoleMem.

Chunks workspace files into semantic blocks (functions/classes/blocks),
indexes them with BM25Okapi, and retrieves top relevant context within a token budget.
"""

import re
import math
from typing import List, Dict, Any, Tuple


class BM25Okapi:
    def __init__(self, corpus: List[List[str]], k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.corpus_size = len(corpus)
        self.avgdl = sum(len(doc) for doc in corpus) / self.corpus_size if self.corpus_size > 0 else 0
        self.doc_lens = [len(doc) for doc in corpus]
        self.doc_freqs: Dict[str, int] = {}
        self.term_freqs: List[Dict[str, int]] = []

        for doc in corpus:
            tf = {}
            for term in doc:
                tf[term] = tf.get(term, 0) + 1
            self.term_freqs.append(tf)
            for term in tf:
                self.doc_freqs[term] = self.doc_freqs.get(term, 0) + 1

        self.idf = {}
        for term, freq in self.doc_freqs.items():
            self.idf[term] = math.log((self.corpus_size - freq + 0.5) / (freq + 0.5) + 1.0)

    def get_scores(self, query: List[str]) -> List[float]:
        scores = [0.0] * self.corpus_size
        for term in query:
            if term not in self.idf:
                continue
            q_idf = self.idf[term]
            for i, tf in enumerate(self.term_freqs):
                term_count = tf.get(term, 0)
                if term_count > 0:
                    num = term_count * (self.k1 + 1)
                    denom = term_count + self.k1 * (1 - self.b + self.b * (self.doc_lens[i] / (self.avgdl or 1)))
                    scores[i] += q_idf * (num / denom)
        return scores


def tokenize(text: str) -> List[str]:
    return [t.lower() for t in re.findall(r"\b[A-Za-z0-9_]+\b", text)]


class RepoBM25Retriever:
    """Retriever that indexes workspace files and retrieves relevant code context under token budget."""

    def __init__(self, workspace_files: Dict[str, str], chunk_lines: int = 40):
        self.chunks: List[Dict[str, Any]] = []
        tokenized_corpus: List[List[str]] = []

        for rel_path, content in workspace_files.items():
            lines = content.splitlines()
            for i in range(0, max(1, len(lines)), chunk_lines):
                chunk_lines_slice = lines[i:i + chunk_lines]
                chunk_text = "\n".join(chunk_lines_slice)
                meta = {
                    "file": rel_path,
                    "start_line": i + 1,
                    "end_line": min(len(lines), i + chunk_lines),
                    "code": chunk_text
                }
                self.chunks.append(meta)
                tokenized_corpus.append(tokenize(f"{rel_path}\n{chunk_text}"))

        self.bm25 = BM25Okapi(tokenized_corpus)

    def retrieve_context(self, query: str, tokenizer, max_tokens: int = 1500) -> Tuple[str, int]:
        """Retrieve top matching chunks up to max_tokens."""
        if not self.chunks:
            return "", 0

        q_tokens = tokenize(query)
        scores = self.bm25.get_scores(q_tokens)

        # Rank chunks by score
        ranked_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)

        selected_chunks = []
        total_tokens = 0

        header = "[REPOSITORY CONTEXT (RETRIEVED)]\n"
        accumulated_text = header
        header_tokens = len(tokenizer.encode(header, add_special_tokens=False))
        total_tokens = header_tokens

        for idx in ranked_indices:
            if scores[idx] <= 0:
                break
            chunk = self.chunks[idx]
            block = f"# File: {chunk['file']} (Lines {chunk['start_line']}-{chunk['end_line']})\n{chunk['code']}\n\n"
            block_tokens = len(tokenizer.encode(block, add_special_tokens=False))

            if total_tokens + block_tokens <= max_tokens:
                selected_chunks.append(block)
                total_tokens += block_tokens
            else:
                # Room for truncated chunk?
                remaining = max_tokens - total_tokens
                if remaining > 100:
                    encoded = tokenizer.encode(block, add_special_tokens=False)[:remaining]
                    selected_chunks.append(tokenizer.decode(encoded) + "\n... [TRUNCATED]\n\n")
                    total_tokens += len(encoded)
                break

        if not selected_chunks:
            return "", 0

        final_context = header + "".join(selected_chunks)
        return final_context, total_tokens
