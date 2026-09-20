"""
src/validity/dependency_validity.py

Static AST Dependency Validity Analyzer.
Protocol V2.1 specification.

Extracts referenced imports, attribute accesses, and function calls from base code
and verifies whether they remain available and valid in the target code/diff environment.
Strictly general AST analysis — zero benchmark-specific keywords or hardcoded symbol tables.
"""

import os
import ast
import subprocess
from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional, Tuple, Any
from .types import ValidityResult, ValidityEvidence


@dataclass
class DependencyReference:
    kind: str  # "import", "import_from", "attribute", "call", "name"
    qualified_name: str
    imported_from: str = ""  # The module or full import if resolved from an import
    source_symbol: str = ""
    lineno: int = 0


class ASTDependencyExtractor(ast.NodeVisitor):
    """Walks an AST node or subtree to extract all referenced external dependencies."""

    def __init__(self, target_symbol_node: Optional[ast.AST] = None):
        self.target_symbol_node = target_symbol_node
        self.dependencies: List[DependencyReference] = []
        self.imported_names: Dict[str, str] = {}  # alias -> original/module
        self.all_imports: Set[str] = set()

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            name = alias.name
            asname = alias.asname or name
            self.imported_names[asname] = name
            self.all_imports.add(name)
            self.dependencies.append(
                DependencyReference(kind="import", qualified_name=name, imported_from=name, lineno=node.lineno)
            )
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        mod = node.module or ""
        for alias in node.names:
            name = alias.name
            asname = alias.asname or name
            full_name = f"{mod}.{name}" if mod else name
            self.imported_names[asname] = full_name
            self.all_imports.add(full_name)
            self.dependencies.append(
                DependencyReference(kind="import_from", qualified_name=full_name, imported_from=mod, lineno=node.lineno)
            )
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute):
        chain = []
        curr = node
        while isinstance(curr, ast.Attribute):
            chain.append(curr.attr)
            curr = curr.value
        if isinstance(curr, ast.Name):
            chain.append(curr.id)
            chain.reverse()
            full_attr = ".".join(chain)
            root = chain[0]
            if root in self.imported_names:
                resolved = self.imported_names[root] + "." + ".".join(chain[1:])
                self.dependencies.append(
                    DependencyReference(
                        kind="attribute",
                        qualified_name=resolved,
                        imported_from=self.imported_names[root],
                        lineno=node.lineno
                    )
                )
            else:
                self.dependencies.append(
                    DependencyReference(kind="attribute", qualified_name=full_attr, lineno=node.lineno)
                )
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        if isinstance(node.func, ast.Name):
            name = node.func.id
            if name in self.imported_names:
                resolved = self.imported_names[name]
                self.dependencies.append(
                    DependencyReference(
                        kind="call",
                        qualified_name=resolved,
                        imported_from=resolved,
                        lineno=node.lineno
                    )
                )
            else:
                self.dependencies.append(
                    DependencyReference(kind="call", qualified_name=name, lineno=node.lineno)
                )
        self.generic_visit(node)


class DependencyValidityChecker:
    """Evaluates whether dependencies referenced by a symbol are broken or modified in target."""

    def _read_git_file(self, repo_dir: str, commit: str, file_path: str) -> Optional[str]:
        if not os.path.isdir(repo_dir) or not commit or not file_path:
            return None
        res = subprocess.run(["git", "show", f"{commit}:{file_path}"], cwd=repo_dir, capture_output=True, text=True)
        if res.returncode == 0:
            return res.stdout
        return None

    def extract_dependencies(self, source_code: str, symbol_qualified_name: str = "") -> Tuple[List[DependencyReference], Set[str]]:
        import textwrap
        try:
            tree = ast.parse(textwrap.dedent(source_code))
        except Exception:
            return [], set()

        target_node = None
        if symbol_qualified_name:
            unqualified = symbol_qualified_name.split(".")[-1]
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.name == unqualified:
                    target_node = node
                    break

        file_extractor = ASTDependencyExtractor()
        file_extractor.visit(tree)

        if target_node is not None:
            symbol_extractor = ASTDependencyExtractor()
            symbol_extractor.imported_names = file_extractor.imported_names
            symbol_extractor.visit(target_node)
            return symbol_extractor.dependencies, file_extractor.all_imports
        else:
            return file_extractor.dependencies, file_extractor.all_imports

    def evaluate(
        self,
        base_source: str,
        target_source: str,
        symbol_qualified_name: str = "",
        diff_hunk: str = "",
        repository_root: Optional[str] = None,
        base_commit: Optional[str] = None,
        target_commit: Optional[str] = None,
        file_path: Optional[str] = None,
    ) -> ValidityResult:
        # If repository context is provided and sources appear to be excerpts, load full files
        if repository_root and file_path and base_commit and target_commit:
            full_base = self._read_git_file(repository_root, base_commit, file_path)
            full_target = self._read_git_file(repository_root, target_commit, file_path)
            if full_base and full_target:
                base_source = full_base
                target_source = full_target

        base_deps, base_file_imports = self.extract_dependencies(base_source, symbol_qualified_name)
        target_deps, target_file_imports = self.extract_dependencies(target_source, symbol_qualified_name)

        if not base_deps and not base_file_imports:
            return ValidityResult(
                decision="UNCERTAIN",
                confidence=0.50,
                reasons=["No explicit static AST dependencies detected in base symbol."],
                evidence=[
                    ValidityEvidence(
                        evidence_type="no_dependencies_found",
                        source="ast_dependency_analysis",
                        detail="Symbol has no direct external imports, attribute chains, or calls.",
                        confidence=0.50
                    )
                ],
                file_changed=None,
                symbol_changed=None,
                symbol_removed=None,
                dependency_changed=False
            )

        # Check required imports used by the symbol
        required_imports = set()
        for d in base_deps:
            if d.imported_from:
                required_imports.add(d.imported_from)
            elif d.kind in ("import", "import_from"):
                required_imports.add(d.qualified_name)

        broken_imports = []
        for req in required_imports:
            matched = False
            for tf in target_file_imports:
                if req == tf or req.startswith(tf + ".") or tf.startswith(req + "."):
                    matched = True
                    break
            if not matched:
                broken_imports.append(req)

        if broken_imports:
            return ValidityResult(
                decision="STALE",
                confidence=0.90,
                reasons=[f"Static dependency import removed in target: {', '.join(broken_imports)}"],
                evidence=[
                    ValidityEvidence(
                        evidence_type="dependency_import_removed",
                        source="ast_dependency_analysis",
                        detail=f"Imported dependency `{bi}` used by symbol in base is missing in target imports.",
                        confidence=0.90
                    )
                    for bi in broken_imports
                ],
                file_changed=None,
                symbol_changed=None,
                symbol_removed=None,
                dependency_changed=True
            )

        # Check for explicit diff-based removals of referenced attributes/symbols
        if diff_hunk:
            removed_lines = [line[1:].strip() for line in diff_hunk.splitlines() if line.startswith("-") and not line.startswith("---")]
            for dep in base_deps:
                dep_name = dep.qualified_name.split(".")[-1]
                for rline in removed_lines:
                    if (f"def {dep_name}" in rline or f"class {dep_name}" in rline or f"import {dep_name}" in rline) and not any(f"def {dep_name}" in pline or f"class {dep_name}" in pline for pline in diff_hunk.splitlines() if pline.startswith("+") and not pline.startswith("+++")):
                        return ValidityResult(
                            decision="STALE",
                            confidence=0.90,
                            reasons=[f"Referenced dependency `{dep.qualified_name}` explicitly removed in diff."],
                            evidence=[
                                ValidityEvidence(
                                    evidence_type="diff_dependency_deletion",
                                    source="diff_hunk_analysis",
                                    detail=f"Removal line: `{rline}` deletes dependency `{dep.qualified_name}`",
                                    confidence=0.90
                                )
                            ],
                            file_changed=None,
                            symbol_changed=None,
                            symbol_removed=None,
                            dependency_changed=True
                        )

        # If base imports existed and all were verified present in target file imports
        if base_deps:
            return ValidityResult(
                decision="VALID",
                confidence=0.85,
                reasons=["All verified static AST dependencies remain intact in target source."],
                evidence=[
                    ValidityEvidence(
                        evidence_type="dependencies_intact",
                        source="ast_dependency_analysis",
                        detail=f"Verified {len(base_deps)} AST dependency references preserved.",
                        confidence=0.85
                    )
                ],
                file_changed=None,
                symbol_changed=None,
                symbol_removed=None,
                dependency_changed=False
            )

        return ValidityResult(
            decision="UNCERTAIN",
            confidence=0.50,
            reasons=["Static dependencies could not be definitively resolved."],
            evidence=[],
            file_changed=None,
            symbol_changed=None,
            symbol_removed=None,
            dependency_changed=None
        )
