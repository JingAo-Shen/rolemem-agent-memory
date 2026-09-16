"""
AST-Based Stale Action Detector.
Distinguishes active executable usage (imports, calls, attributes, assignments)
from benign mentions (comments, docstrings, explanatory text).
"""

import ast
import re
import tokenize
import io
from typing import List, Dict, Any, Set, Tuple
from dataclasses import dataclass, field


@dataclass
class StaleAnalysisResult:
    stale_active_use: bool
    stale_mention: bool
    active_nodes: List[Dict[str, Any]] = field(default_factory=list)
    mention_contexts: List[str] = field(default_factory=list)


class ASTStaleVisitor(ast.NodeVisitor):
    """Walks the Python Abstract Syntax Tree to identify active invocations of stale symbols."""

    def __init__(self, stale_symbols: Set[str]):
        self.stale_symbols = stale_symbols
        self.active_nodes: List[Dict[str, Any]] = []

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            if alias.name in self.stale_symbols or (alias.asname and alias.asname in self.stale_symbols):
                self.active_nodes.append({
                    "type": "Import",
                    "lineno": node.lineno,
                    "symbol": alias.name
                })
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        for alias in node.names:
            if alias.name in self.stale_symbols or (alias.asname and alias.asname in self.stale_symbols):
                self.active_nodes.append({
                    "type": "ImportFrom",
                    "lineno": node.lineno,
                    "module": node.module,
                    "symbol": alias.name
                })
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        if node.id in self.stale_symbols:
            ctx_name = type(node.ctx).__name__
            self.active_nodes.append({
                "type": f"Name({ctx_name})",
                "lineno": node.lineno,
                "symbol": node.id
            })
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if node.attr in self.stale_symbols:
            self.active_nodes.append({
                "type": "Attribute",
                "lineno": node.lineno,
                "symbol": node.attr
            })
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        # Check keyword arguments (e.g. func(ttl=60))
        for kw in node.keywords:
            if kw.arg and kw.arg in self.stale_symbols:
                self.active_nodes.append({
                    "type": "KeywordArg",
                    "lineno": node.lineno,
                    "symbol": kw.arg
                })
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        if node.name in self.stale_symbols:
            self.active_nodes.append({
                "type": "FunctionDef",
                "lineno": node.lineno,
                "symbol": node.name
            })
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        if node.name in self.stale_symbols:
            self.active_nodes.append({
                "type": "ClassDef",
                "lineno": node.lineno,
                "symbol": node.name
            })
        self.generic_visit(node)


class ASTStaleActionDetector:
    """Evaluates Python code for active stale actions vs passive mentions."""

    @staticmethod
    def analyze(code: str, stale_patterns: List[str]) -> StaleAnalysisResult:
        if not code or not stale_patterns:
            return StaleAnalysisResult(stale_active_use=False, stale_mention=False)

        stale_symbols_set = set(stale_patterns)
        active_nodes = []
        stale_mention = False
        mention_contexts = []

        # 1. Parse AST
        try:
            tree = ast.parse(code)
            visitor = ASTStaleVisitor(stale_symbols_set)
            visitor.visit(tree)
            active_nodes = visitor.active_nodes
        except SyntaxError:
            # Fallback regex for active syntax if code has syntax error
            for sym in stale_patterns:
                # Look for assignment or invocation
                pattern = rf"(?m)^\s*(?:from\s+\S+\s+import\s+.*{re.escape(sym)}|{re.escape(sym)}\s*=|import\s+.*{re.escape(sym)})"
                if re.search(pattern, code):
                    active_nodes.append({"type": "RegexFallbackActive", "lineno": 0, "symbol": sym})

        # 2. Extract comments and docstrings to check for passive mentions
        try:
            tokens = tokenize.tokenize(io.BytesIO(code.encode('utf-8')).readline)
            for tok_type, tok_string, (srow, _), _, _ in tokens:
                if tok_type in (tokenize.COMMENT, tokenize.STRING):
                    for sym in stale_patterns:
                        if sym in tok_string:
                            stale_mention = True
                            mention_contexts.append(f"Line {srow}: {tok_string.strip()[:60]}")
        except Exception:
            for line in code.split("\n"):
                if line.strip().startswith("#"):
                    for sym in stale_patterns:
                        if sym in line:
                            stale_mention = True
                            mention_contexts.append(line.strip()[:60])

        stale_active_use = len(active_nodes) > 0
        return StaleAnalysisResult(
            stale_active_use=stale_active_use,
            stale_mention=stale_mention,
            active_nodes=active_nodes,
            mention_contexts=mention_contexts
        )
