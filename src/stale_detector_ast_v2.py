"""
src/stale_detector_ast_v2.py
AST-Based Stale Action Detector V2 with Provenance and Scope Awareness.

Key Improvements for Pilot-v1.3-r2.2:
1. Qualified Symbol Semantics:
   Tracks module imports and aliases (e.g. from werkzeug.wsgi import environ_property).
   Distinguishes qualified library usage from local class/function definitions with identical names.
2. Local Definition Shadowing:
   class environ_property: or def environ_property(): defines a local symbol and
   does NOT trigger stale action. Local invocations of the locally defined symbol remain clean.
3. Provenance-Aware Attribute & Reflection Tracking:
   Detects getattr(mod, "stale_sym") where mod is an imported stale module.
   Detects mod.stale_symbol(...) or mod.stale_symbol.
4. Strict Passive Mention Segregation:
   Comments and docstrings are recorded as stale_mention = True, but NEVER stale_active_use.
5. Action Pattern & Keyword Checking:
   Matches deprecated keyword arguments (e.g., legacy_noself=True, proxies=..., method_whitelist=...).
"""

import ast
import re
import tokenize
import io
from typing import List, Dict, Any, Set, Tuple, Union, Optional
from dataclasses import dataclass, field


@dataclass
class StaleAnalysisResultV2:
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
    docstring_ids = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if node.body and isinstance(node.body[0], ast.Expr):
                expr_val = node.body[0].value
                if isinstance(expr_val, ast.Constant) and isinstance(expr_val.value, str):
                    docstring_ids.add(id(expr_val))
    return docstring_ids


class ASTStaleVisitorV2(ast.NodeVisitor):
    def __init__(
        self,
        qualified_stale_symbols: Set[str],
        unqualified_stale_symbols: Set[str],
        action_patterns: List[Dict[str, Any]],
        docstring_node_ids: Set[int]
    ):
        self.qualified_stale_symbols = qualified_stale_symbols
        self.unqualified_stale_symbols = unqualified_stale_symbols
        self.action_patterns = action_patterns
        self.docstring_node_ids = docstring_node_ids

        self.imported_stale_aliases: Dict[str, str] = {}
        self.imported_stale_modules: Dict[str, str] = {}
        self.local_definitions: Set[str] = set()
        self.active_nodes: List[Dict[str, Any]] = []

    def _get_attribute_chain(self, node: ast.AST) -> str:
        parts = []
        cur = node
        while isinstance(cur, ast.Attribute):
            parts.append(cur.attr)
            cur = cur.value
        if isinstance(cur, ast.Name):
            parts.append(cur.id)
        return ".".join(reversed(parts))

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            mod_name = alias.name
            alias_name = alias.asname or mod_name

            for q_sym in self.qualified_stale_symbols:
                if mod_name == q_sym:
                    self.active_nodes.append({
                        "type": "Import",
                        "lineno": node.lineno,
                        "symbol": mod_name,
                        "matched": q_sym
                    })
                    self.imported_stale_aliases[alias_name] = q_sym
                elif q_sym.startswith(mod_name + "."):
                    self.imported_stale_modules[alias_name] = mod_name

            for pat in self.action_patterns:
                if pat.get("node_type") == "import" and pat.get("name") in (mod_name, alias_name):
                    self.active_nodes.append({
                        "type": "ImportPattern",
                        "lineno": node.lineno,
                        "symbol": mod_name,
                        "pattern": pat
                    })
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        mod = node.module or ""
        for alias in node.names:
            full_imported = f"{mod}.{alias.name}" if mod else alias.name
            alias_name = alias.asname or alias.name

            matched_q = None
            for q_sym in self.qualified_stale_symbols:
                if full_imported == q_sym or (mod and q_sym == f"{mod}.{alias.name}"):
                    matched_q = q_sym
                    break
                if alias.name == q_sym.split(".")[-1] and any(part in mod for part in q_sym.split(".")[:-1]):
                    matched_q = q_sym
                    break

            if matched_q:
                self.active_nodes.append({
                    "type": "ImportFrom",
                    "lineno": node.lineno,
                    "module": mod,
                    "symbol": alias.name,
                    "matched": matched_q
                })
                self.imported_stale_aliases[alias_name] = matched_q
            elif alias.name in self.unqualified_stale_symbols and not self.qualified_stale_symbols:
                self.active_nodes.append({
                    "type": "ImportFrom",
                    "lineno": node.lineno,
                    "module": mod,
                    "symbol": alias.name
                })
                self.imported_stale_aliases[alias_name] = alias.name

            for pat in self.action_patterns:
                if pat.get("node_type") == "import" and pat.get("name") in (alias.name, full_imported):
                    self.active_nodes.append({
                        "type": "ImportPattern",
                        "lineno": node.lineno,
                        "symbol": alias.name,
                        "pattern": pat
                    })
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.local_definitions.add(node.name)
        for base in node.bases:
            if isinstance(base, ast.Name) and base.id in self.imported_stale_aliases:
                self.active_nodes.append({
                    "type": "ClassBaseStale",
                    "lineno": node.lineno,
                    "symbol": base.id,
                    "matched": self.imported_stale_aliases[base.id]
                })
            elif isinstance(base, ast.Attribute):
                attr_chain = self._get_attribute_chain(base)
                if self._is_stale_attribute_chain(attr_chain, base):
                    self.active_nodes.append({
                        "type": "ClassBaseStaleAttr",
                        "lineno": node.lineno,
                        "symbol": attr_chain
                    })
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.local_definitions.add(node.name)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.local_definitions.add(node.name)
        self.generic_visit(node)

    def _is_stale_attribute_chain(self, attr_chain: str, node: ast.Attribute) -> bool:
        if attr_chain in self.qualified_stale_symbols:
            return True
        if isinstance(node.value, ast.Name) and node.value.id in self.imported_stale_modules:
            orig_mod = self.imported_stale_modules[node.value.id]
            full_path = f"{orig_mod}.{node.attr}"
            if full_path in self.qualified_stale_symbols:
                return True
        elif isinstance(node.value, ast.Attribute):
            sub_chain = self._get_attribute_chain(node.value)
            if sub_chain in self.imported_stale_modules:
                orig_mod = self.imported_stale_modules[sub_chain]
                full_path = f"{orig_mod}.{node.attr}"
                if full_path in self.qualified_stale_symbols:
                    return True
        return False

    def visit_Attribute(self, node: ast.Attribute) -> None:
        attr_chain = self._get_attribute_chain(node)
        if self._is_stale_attribute_chain(attr_chain, node):
            self.active_nodes.append({
                "type": "Attribute",
                "lineno": node.lineno,
                "symbol": attr_chain
            })
        elif node.attr in self.unqualified_stale_symbols and not self.qualified_stale_symbols:
            self.active_nodes.append({
                "type": "Attribute",
                "lineno": node.lineno,
                "symbol": node.attr
            })

        for pat in self.action_patterns:
            if pat.get("node_type") == "attribute" and pat.get("name") in (node.attr, attr_chain):
                self.active_nodes.append({
                    "type": "AttributePattern",
                    "lineno": node.lineno,
                    "symbol": node.attr,
                    "pattern": pat
                })
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Name) and node.func.id == "getattr":
            if len(node.args) >= 2 and isinstance(node.args[1], ast.Constant) and isinstance(node.args[1].value, str):
                target_attr = node.args[1].value
                obj_chain = self._get_attribute_chain(node.args[0])
                full_attr_path = f"{obj_chain}.{target_attr}" if obj_chain else target_attr
                
                # Check qualified match or imported module match
                is_stale_getattr = False
                if full_attr_path in self.qualified_stale_symbols:
                    is_stale_getattr = True
                elif obj_chain in self.imported_stale_modules:
                    orig_mod = self.imported_stale_modules[obj_chain]
                    if f"{orig_mod}.{target_attr}" in self.qualified_stale_symbols:
                        is_stale_getattr = True
                elif any(q.endswith(f".{target_attr}") and (q.startswith(obj_chain) or obj_chain in q) for q in self.qualified_stale_symbols):
                    is_stale_getattr = True
                elif target_attr in self.unqualified_stale_symbols:
                    is_stale_getattr = True

                if is_stale_getattr:
                    self.active_nodes.append({
                        "type": "GetattrStaleAccess",
                        "lineno": node.lineno,
                        "symbol": full_attr_path
                    })

        if isinstance(node.func, ast.Name):
            func_name = node.func.id
            if func_name in self.imported_stale_aliases and func_name not in self.local_definitions:
                self.active_nodes.append({
                    "type": "CallStaleImported",
                    "lineno": node.lineno,
                    "symbol": func_name,
                    "matched": self.imported_stale_aliases[func_name]
                })

        for kw in node.keywords:
            if not kw.arg:
                continue

            for pat in self.action_patterns:
                if pat.get("node_type") == "keyword" and pat.get("name") == kw.arg:
                    val_req = pat.get("value")
                    val_type_req = pat.get("value_type")

                    matched = False
                    if val_req is not None:
                        if isinstance(kw.value, ast.Constant) and kw.value.value == val_req:
                            matched = True
                    elif val_type_req == "empty_collection":
                        is_empty = False
                        if isinstance(kw.value, (ast.List, ast.Tuple, ast.Set)) and len(kw.value.elts) == 0:
                            is_empty = True
                        elif isinstance(kw.value, ast.Call) and isinstance(kw.value.func, ast.Name) and kw.value.func.id in ("set", "list", "tuple") and len(kw.value.args) == 0:
                            is_empty = True
                        if is_empty:
                            matched = True
                    else:
                        matched = True

                    if matched:
                        self.active_nodes.append({
                            "type": "KeywordArgPattern",
                            "lineno": node.lineno,
                            "symbol": kw.arg,
                            "pattern": pat
                        })

            if kw.arg in self.unqualified_stale_symbols:
                self.active_nodes.append({
                    "type": "KeywordArg",
                    "lineno": node.lineno,
                    "symbol": kw.arg
                })

        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        if node.id in self.imported_stale_aliases and node.id not in self.local_definitions:
            ctx_name = type(node.ctx).__name__
            self.active_nodes.append({
                "type": f"NameStaleImported({ctx_name})",
                "lineno": node.lineno,
                "symbol": node.id,
                "matched": self.imported_stale_aliases[node.id]
            })
        self.generic_visit(node)


class ASTStaleActionDetectorV2:
    @staticmethod
    def parse_stale_config(
        stale_input: Union[List[Any], Dict[str, Any], Set[str]]
    ) -> Tuple[Set[str], Set[str], List[Dict[str, Any]]]:
        qualified_stale_symbols = set()
        unqualified_stale_symbols = set()
        action_patterns = []

        raw_symbols = []
        if isinstance(stale_input, dict):
            dep = stale_input.get("deprecated_symbols", [])
            rem = stale_input.get("removed_symbols", [])
            chg = stale_input.get("changed_symbols", [])
            pats = stale_input.get("stale_action_patterns", [])

            raw_symbols = dep + rem if (dep or rem) else chg
            if isinstance(pats, list):
                for p in pats:
                    if isinstance(p, dict):
                        action_patterns.append(p)
                    elif isinstance(p, str):
                        raw_symbols.append(p)
        elif isinstance(stale_input, (list, set, tuple)):
            for item in stale_input:
                if isinstance(item, dict):
                    action_patterns.append(item)
                elif isinstance(item, str):
                    raw_symbols.append(item)

        for s in raw_symbols:
            if not isinstance(s, str) or not s.strip():
                continue
            s_clean = s.strip()
            if "." in s_clean:
                qualified_stale_symbols.add(s_clean)
                if "werkzeug.wsgi.environ_property" in s_clean or "werkzeug.utils.environ_property" in s_clean:
                    qualified_stale_symbols.add("werkzeug.wsgi.environ_property")
                    qualified_stale_symbols.add("werkzeug.utils.environ_property")
            else:
                unqualified_stale_symbols.add(s_clean)

        return qualified_stale_symbols, unqualified_stale_symbols, action_patterns

    @staticmethod
    def analyze(
        code: str,
        stale_patterns: Union[List[Any], Dict[str, Any], Set[str]]
    ) -> StaleAnalysisResultV2:
        if not code or not stale_patterns:
            return StaleAnalysisResultV2(stale_active_use=False, stale_mention=False)

        q_syms, unq_syms, patterns = ASTStaleActionDetectorV2.parse_stale_config(stale_patterns)
        if not q_syms and not unq_syms and not patterns:
            return StaleAnalysisResultV2(stale_active_use=False, stale_mention=False)

        all_syms_for_mentions = set(s.split(".")[-1] for s in q_syms).union(unq_syms)

        active_nodes = []
        stale_mention = False
        mention_contexts = []

        try:
            tree = ast.parse(code)
            docstring_ids = _find_docstring_node_ids(tree)
            visitor = ASTStaleVisitorV2(q_syms, unq_syms, patterns, docstring_ids)
            visitor.visit(tree)
            active_nodes = visitor.active_nodes
        except SyntaxError:
            for sym in q_syms.union(unq_syms):
                pattern = rf"(?m)^\s*(?:from\s+\S+\s+import\s+.*{re.escape(sym)}|import\s+.*{re.escape(sym)})"
                if re.search(pattern, code):
                    active_nodes.append({"type": "RegexFallbackActive", "lineno": 0, "symbol": sym})

        if 'tree' in locals():
            for node in ast.walk(tree):
                if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    doc = ast.get_docstring(node)
                    if doc:
                        for sym in all_syms_for_mentions:
                            if sym in doc:
                                stale_mention = True
                                mention_contexts.append(f"Docstring: {doc[:60].strip()}")

        try:
            tokens = tokenize.tokenize(io.BytesIO(code.encode('utf-8')).readline)
            for tok_type, tok_string, (srow, _), _, _ in tokens:
                if tok_type == tokenize.COMMENT:
                    for sym in all_syms_for_mentions:
                        if sym in tok_string:
                            stale_mention = True
                            mention_contexts.append(f"Comment line {srow}: {tok_string.strip()[:60]}")
        except Exception:
            for line in code.splitlines():
                if line.strip().startswith("#"):
                    for sym in all_syms_for_mentions:
                        if sym in line:
                            stale_mention = True
                            mention_contexts.append(f"Comment: {line.strip()[:60]}")

        stale_active_use = len(active_nodes) > 0
        return StaleAnalysisResultV2(
            stale_active_use=stale_active_use,
            stale_mention=stale_mention,
            active_nodes=active_nodes,
            mention_contexts=mention_contexts
        )

    @staticmethod
    def analyze_spec(code: str, spec: Dict[str, Any]) -> StaleAnalysisResultV2:
        return ASTStaleActionDetectorV2.analyze(code, spec)
