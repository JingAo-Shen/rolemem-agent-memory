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

    @property
    def stale_mentions(self) -> bool:
        return self.stale_mention

    @property
    def active_stale_nodes(self) -> List[Dict[str, Any]]:
        return self.active_nodes


def _find_docstring_node_ids(tree: ast.AST) -> Set[int]:
    """Identify AST node IDs that represent passive docstrings."""
    docstring_ids = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if node.body and isinstance(node.body[0], ast.Expr):
                expr_val = node.body[0].value
                if isinstance(expr_val, ast.Constant) and isinstance(expr_val.value, str):
                    docstring_ids.add(id(expr_val))
    return docstring_ids


class ASTStaleVisitor(ast.NodeVisitor):
    """Walks the Python Abstract Syntax Tree to identify active invocations of stale symbols."""

    def __init__(self, stale_symbols: Set[str], docstring_node_ids: Set[int]):
        self.stale_symbols = stale_symbols
        self.docstring_node_ids = docstring_node_ids
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

    def visit_Constant(self, node: ast.Constant) -> None:
        # Ignore docstring constants
        if id(node) in self.docstring_node_ids:
            return
        
        val_str = str(node.value)
        # Check if the constant matches or contains a stale symbol
        for sym in self.stale_symbols:
            if sym == val_str or (isinstance(node.value, str) and sym in node.value and len(sym) >= 3):
                self.active_nodes.append({
                    "type": "ConstantLiteral",
                    "lineno": node.lineno,
                    "symbol": sym,
                    "literal_value": val_str
                })
                break
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
            docstring_ids = _find_docstring_node_ids(tree)
            visitor = ASTStaleVisitor(stale_symbols_set, docstring_ids)
            visitor.visit(tree)
            active_nodes = visitor.active_nodes
        except SyntaxError:
            # Fallback regex for active syntax if code has syntax error
            for sym in stale_patterns:
                pattern = rf"(?m)^\s*(?:from\s+\S+\s+import\s+.*{re.escape(sym)}|{re.escape(sym)}\s*=|import\s+.*{re.escape(sym)}|.*\[['\"]{re.escape(sym)}['\"]\])"
                if re.search(pattern, code):
                    active_nodes.append({"type": "RegexFallbackActive", "lineno": 0, "symbol": sym})

        # 2. Extract comments and docstrings to check for passive mentions
        # Check docstrings
        if 'tree' in locals():
            for node in ast.walk(tree):
                if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    doc = ast.get_docstring(node)
                    if doc:
                        for sym in stale_patterns:
                            if sym in doc:
                                stale_mention = True
                                mention_contexts.append(f"Docstring in {getattr(node, 'name', 'module')}: {doc[:60]}")

        # Check comments via tokenize
        try:
            tokens = tokenize.tokenize(io.BytesIO(code.encode('utf-8')).readline)
            for tok_type, tok_string, (srow, _), _, _ in tokens:
                if tok_type == tokenize.COMMENT:
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
