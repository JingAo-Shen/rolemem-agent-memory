"""
src/validity/dependency_graph.py

Static AST Dependency Graph & Linkage Verifier for Protocol V2.1-R3.
Constructs lightweight call and import graphs (1-2 hops) from a source symbol
to verify whether a target symbol semantically and causally depends on a broken dependency.
"""

import ast
import os
import subprocess
from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional, Tuple, Any


@dataclass
class DependencyPath:
    source_symbol: str
    target_symbol: str
    path: List[str]
    confidence: float
    linkage_verified: bool
    details: str = ""


class ASTSymbolCallExtractor(ast.NodeVisitor):
    """Extracts all function calls, attribute accesses, and name references inside a symbol AST node."""

    def __init__(self):
        self.calls: Set[str] = set()
        self.attributes: Set[str] = set()
        self.names: Set[str] = set()

    def visit_Call(self, node: ast.Call):
        if isinstance(node.func, ast.Name):
            self.calls.add(node.func.id)
        elif isinstance(node.func, ast.Attribute):
            # e.g. self.helper() or obj.method()
            self.calls.add(node.func.attr)
            chain = self._resolve_attr_chain(node.func)
            if chain:
                self.attributes.add(chain)
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute):
        chain = self._resolve_attr_chain(node)
        if chain:
            self.attributes.add(chain)
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name):
        self.names.add(node.id)
        self.generic_visit(node)

    def _resolve_attr_chain(self, node: ast.AST) -> str:
        chain = []
        curr = node
        while isinstance(curr, ast.Attribute):
            chain.append(curr.attr)
            curr = curr.value
        if isinstance(curr, ast.Name):
            chain.append(curr.id)
            chain.reverse()
            return ".".join(chain)
        return ""


class DependencyGraphVerifier:
    """Verifies semantic linkage between a source symbol and a downstream dependency."""

    @staticmethod
    def extract_symbol_node(source_code: str, symbol_name: str) -> Optional[ast.AST]:
        try:
            tree = ast.parse(source_code)
        except Exception:
            return None

        # Direct name match
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if node.name == symbol_name or symbol_name.endswith(f".{node.name}"):
                    return node
        return None

    @staticmethod
    def verify_linkage(
        source_code: str,
        source_symbol: str,
        dependency_symbol: str,
        file_path: str = "",
        repository_root: Optional[str] = None,
        commit: Optional[str] = None
    ) -> DependencyPath:
        """
        Builds 1-hop and 2-hop linkage between source_symbol and dependency_symbol:
        1-hop: source_symbol directly calls / references dependency_symbol.
        2-hop: source_symbol calls helper_func inside the same module, and helper_func calls dependency_symbol.
        """
        sym_node = DependencyGraphVerifier.extract_symbol_node(source_code, source_symbol)
        if not sym_node:
            return DependencyPath(
                source_symbol=source_symbol,
                target_symbol=dependency_symbol,
                path=[],
                confidence=0.0,
                linkage_verified=False,
                details=f"Source symbol `{source_symbol}` not found in AST."
            )

        # 1-hop check inside source_symbol
        extractor = ASTSymbolCallExtractor()
        extractor.visit(sym_node)

        # Check if dependency_symbol is directly called or referenced
        dep_base = dependency_symbol.split(".")[-1]
        if dep_base in extractor.calls or dep_base in extractor.names or any(dep_base in attr for attr in extractor.attributes):
            return DependencyPath(
                source_symbol=source_symbol,
                target_symbol=dependency_symbol,
                path=[source_symbol, dependency_symbol],
                confidence=0.95,
                linkage_verified=True,
                details=f"Direct 1-hop AST reference from `{source_symbol}` to `{dependency_symbol}`."
            )

        # 2-hop check: Search helper functions/methods called by source_symbol
        try:
            full_tree = ast.parse(source_code)
        except Exception:
            full_tree = None

        if full_tree:
            all_defs = {}
            for node in ast.walk(full_tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    all_defs[node.name] = node

            for called_helper in extractor.calls:
                if called_helper in all_defs and called_helper != source_symbol:
                    helper_node = all_defs[called_helper]
                    helper_ext = ASTSymbolCallExtractor()
                    helper_ext.visit(helper_node)
                    if dep_base in helper_ext.calls or dep_base in helper_ext.names:
                        return DependencyPath(
                            source_symbol=source_symbol,
                            target_symbol=dependency_symbol,
                            path=[source_symbol, called_helper, dependency_symbol],
                            confidence=0.88,
                            linkage_verified=True,
                            details=f"2-hop AST call path: `{source_symbol}` -> `{called_helper}` -> `{dependency_symbol}`."
                        )

        return DependencyPath(
            source_symbol=source_symbol,
            target_symbol=dependency_symbol,
            path=[],
            confidence=0.0,
            linkage_verified=False,
            details=f"No static AST dependency path found from `{source_symbol}` to `{dependency_symbol}`."
        )
