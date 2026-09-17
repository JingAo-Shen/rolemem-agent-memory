"""
AST-Based Stale Action Detector.
Distinguishes active executable usage (imports, calls, attributes, assignments, keyword args)
from benign mentions (comments, docstrings, explanatory text).
Supports multi-level symbol extraction (deprecated_symbols, removed_symbols, stale_action_patterns).
"""

import ast
import re
import tokenize
import io
from typing import List, Dict, Any, Set, Tuple, Union, Optional
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
    """Walks the Python Abstract Syntax Tree to identify active invocations of stale symbols and patterns."""

    def __init__(self, stale_symbols: Set[str], action_patterns: List[Dict[str, Any]], docstring_node_ids: Set[int]):
        self.stale_symbols = stale_symbols
        self.action_patterns = action_patterns
        self.docstring_node_ids = docstring_node_ids
        self.active_nodes: List[Dict[str, Any]] = []

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            sym_name = alias.name.split(".")[-1]
            if alias.name in self.stale_symbols or sym_name in self.stale_symbols or (alias.asname and alias.asname in self.stale_symbols):
                self.active_nodes.append({
                    "type": "Import",
                    "lineno": node.lineno,
                    "symbol": alias.name
                })
            for pat in self.action_patterns:
                if pat.get("node_type") == "import" and pat.get("name") in (alias.name, sym_name):
                    self.active_nodes.append({
                        "type": "ImportPattern",
                        "lineno": node.lineno,
                        "symbol": alias.name,
                        "pattern": pat
                    })
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        for alias in node.names:
            sym_name = alias.name.split(".")[-1]
            if alias.name in self.stale_symbols or sym_name in self.stale_symbols or (alias.asname and alias.asname in self.stale_symbols):
                self.active_nodes.append({
                    "type": "ImportFrom",
                    "lineno": node.lineno,
                    "module": node.module,
                    "symbol": alias.name
                })
            for pat in self.action_patterns:
                if pat.get("node_type") == "import" and pat.get("name") in (alias.name, sym_name):
                    self.active_nodes.append({
                        "type": "ImportPattern",
                        "lineno": node.lineno,
                        "symbol": alias.name,
                        "pattern": pat
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
        for pat in self.action_patterns:
            if pat.get("node_type") == "name" and pat.get("name") == node.id:
                self.active_nodes.append({
                    "type": "NamePattern",
                    "lineno": node.lineno,
                    "symbol": node.id,
                    "pattern": pat
                })
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if node.attr in self.stale_symbols:
            self.active_nodes.append({
                "type": "Attribute",
                "lineno": node.lineno,
                "symbol": node.attr
            })
        for pat in self.action_patterns:
            if pat.get("node_type") == "attribute" and pat.get("name") == node.attr:
                self.active_nodes.append({
                    "type": "AttributePattern",
                    "lineno": node.lineno,
                    "symbol": node.attr,
                    "pattern": pat
                })
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        # Check call target function name
        call_name = ""
        if isinstance(node.func, ast.Name):
            call_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            call_name = node.func.attr

        for pat in self.action_patterns:
            if pat.get("node_type") == "call" and pat.get("name") == call_name:
                self.active_nodes.append({
                    "type": "CallPattern",
                    "lineno": node.lineno,
                    "symbol": call_name,
                    "pattern": pat
                })

        # Check keyword arguments (e.g. Retry(method_whitelist=methods) or func(ttl=60))
        for kw in node.keywords:
            if kw.arg:
                matched_pattern = False
                for pat in self.action_patterns:
                    if pat.get("node_type") == "keyword" and pat.get("name") == kw.arg:
                        val_req = pat.get("value_type")
                        if val_req == "empty_collection":
                            # Matches [] or set() or () or {}
                            is_empty = False
                            if isinstance(kw.value, (ast.List, ast.Tuple, ast.Set)) and len(kw.value.elts) == 0:
                                is_empty = True
                            elif isinstance(kw.value, ast.Call) and isinstance(kw.value.func, ast.Name) and kw.value.func.id in ("set", "list", "tuple") and len(kw.value.args) == 0:
                                is_empty = True
                            if is_empty:
                                self.active_nodes.append({
                                    "type": "KeywordArgPattern",
                                    "lineno": node.lineno,
                                    "symbol": kw.arg,
                                    "pattern": pat
                                })
                                matched_pattern = True
                        else:
                            self.active_nodes.append({
                                "type": "KeywordArgPattern",
                                "lineno": node.lineno,
                                "symbol": kw.arg,
                                "pattern": pat
                            })
                            matched_pattern = True

                if not matched_pattern and kw.arg in self.stale_symbols:
                    has_constrained_pat = any(
                        p.get("node_type") == "keyword" and p.get("name") == kw.arg and p.get("value_type")
                        for p in self.action_patterns
                    )
                    if not has_constrained_pat:
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
    def parse_stale_config(
        stale_input: Union[List[Any], Dict[str, Any], Set[str]]
    ) -> Tuple[Set[str], List[Dict[str, Any]]]:
        """
        Parses multi-format stale input into (stale_symbols, action_patterns).
        Supports:
        - List of string symbols
        - List of dict patterns
        - TransitionSpec dict with deprecated_symbols, removed_symbols, stale_action_patterns
        """
        stale_symbols = set()
        action_patterns = []

        if isinstance(stale_input, dict):
            # Extract from spec dictionary
            dep = stale_input.get("deprecated_symbols", [])
            rem = stale_input.get("removed_symbols", [])
            chg = stale_input.get("changed_symbols", [])
            pats = stale_input.get("stale_action_patterns", [])

            # Priority: deprecated/removed, fallback to changed
            target_syms = dep + rem if (dep or rem) else chg
            for s in target_syms:
                if isinstance(s, str):
                    stale_symbols.add(s)
                    stale_symbols.add(s.split(".")[-1])

            if isinstance(pats, list):
                for p in pats:
                    if isinstance(p, dict):
                        action_patterns.append(p)
                        if "name" in p:
                            stale_symbols.add(p["name"])
                    elif isinstance(p, str):
                        stale_symbols.add(p)
                        stale_symbols.add(p.split(".")[-1])

        elif isinstance(stale_input, (list, set, tuple)):
            for item in stale_input:
                if isinstance(item, str):
                    stale_symbols.add(item)
                    stale_symbols.add(item.split(".")[-1])
                elif isinstance(item, dict):
                    action_patterns.append(item)
                    if "name" in item:
                        stale_symbols.add(item["name"])

        return stale_symbols, action_patterns

    @staticmethod
    def analyze(
        code: str,
        stale_patterns: Union[List[Any], Dict[str, Any], Set[str]]
    ) -> StaleAnalysisResult:
        if not code or not stale_patterns:
            return StaleAnalysisResult(stale_active_use=False, stale_mention=False)

        stale_symbols, action_patterns = ASTStaleActionDetector.parse_stale_config(stale_patterns)
        if not stale_symbols and not action_patterns:
            return StaleAnalysisResult(stale_active_use=False, stale_mention=False)

        active_nodes = []
        stale_mention = False
        mention_contexts = []

        # 1. Parse AST
        try:
            tree = ast.parse(code)
            docstring_ids = _find_docstring_node_ids(tree)
            visitor = ASTStaleVisitor(stale_symbols, action_patterns, docstring_ids)
            visitor.visit(tree)
            active_nodes = visitor.active_nodes
        except SyntaxError:
            # Fallback regex for active syntax if code has syntax error
            for sym in stale_symbols:
                pattern = rf"(?m)^\s*(?:from\s+\S+\s+import\s+.*{re.escape(sym)}|{re.escape(sym)}\s*=|import\s+.*{re.escape(sym)}|.*\[['\"]{re.escape(sym)}['\"]\]|\b{re.escape(sym)}\s*=)"
                if re.search(pattern, code):
                    active_nodes.append({"type": "RegexFallbackActive", "lineno": 0, "symbol": sym})

        # 2. Extract comments and docstrings to check for passive mentions
        if 'tree' in locals():
            for node in ast.walk(tree):
                if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    doc = ast.get_docstring(node)
                    if doc:
                        for sym in stale_symbols:
                            if sym in doc:
                                stale_mention = True
                                mention_contexts.append(f"Docstring in {getattr(node, 'name', 'module')}: {doc[:60]}")

        # Check comments via tokenize
        try:
            tokens = tokenize.tokenize(io.BytesIO(code.encode('utf-8')).readline)
            for tok_type, tok_string, (srow, _), _, _ in tokens:
                if tok_type == tokenize.COMMENT:
                    for sym in stale_symbols:
                        if sym in tok_string:
                            stale_mention = True
                            mention_contexts.append(f"Line {srow}: {tok_string.strip()[:60]}")
        except Exception:
            for line in code.split("\n"):
                if line.strip().startswith("#"):
                    for sym in stale_symbols:
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

    @staticmethod
    def analyze_spec(code: str, spec: Dict[str, Any]) -> StaleAnalysisResult:
        """Helper to analyze code against a full TransitionSpec dict."""
        return ASTStaleActionDetector.analyze(code, spec)
