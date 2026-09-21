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
        level = getattr(node, "level", 0) or 0
        dots = "." * level if level > 0 else ""
        mod = node.module or ""
        mod_prefix = f"{dots}{mod}" if mod else dots

        for alias in node.names:
            name = alias.name
            asname = alias.asname or name
            if mod_prefix:
                full_name = f"{mod_prefix}.{name}" if not mod_prefix.endswith(".") else f"{mod_prefix}{name}"
            else:
                full_name = name
            self.imported_names[asname] = full_name
            self.all_imports.add(full_name)
            self.dependencies.append(
                DependencyReference(kind="import_from", qualified_name=full_name, imported_from=mod_prefix, lineno=node.lineno)
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

    def _resolve_local_module_path(self, repository_root: str, current_file: str, mod_name: str) -> List[str]:
        """Resolves potential relative or package-level Python file paths in repository."""
        candidates = []
        if not mod_name or not current_file:
            return candidates

        curr_dir = os.path.dirname(current_file)

        # Handle relative imports (e.g. .foo, ..bar)
        if mod_name.startswith("."):
            dots = len(mod_name) - len(mod_name.lstrip("."))
            rem = mod_name.lstrip(".")
            parts = curr_dir.split(os.sep)
            if dots <= len(parts) + 1:
                target_base = os.path.join(*parts[: len(parts) - (dots - 1)]) if dots > 1 else curr_dir
                if rem:
                    rel_sub = rem.replace(".", os.sep)
                    candidates.append(os.path.normpath(os.path.join(target_base, f"{rel_sub}.py")))
                    candidates.append(os.path.normpath(os.path.join(target_base, rel_sub, "__init__.py")))
                else:
                    candidates.append(os.path.normpath(os.path.join(target_base, "__init__.py")))
        else:
            # Absolute module name within repo
            sub = mod_name.replace(".", os.sep)
            candidates.append(f"{sub}.py")
            candidates.append(f"{sub}/__init__.py")
            candidates.append(f"src/{sub}.py")
            candidates.append(f"src/{sub}/__init__.py")
            if curr_dir:
                candidates.append(os.path.normpath(os.path.join(curr_dir, f"{sub}.py")))
                candidates.append(os.path.normpath(os.path.join(curr_dir, sub, "__init__.py")))

        return candidates

    def _symbol_exists_in_ast(self, source: str, sym_name: str) -> Optional[bool]:
        """Checks if a symbol is defined or exported in a Python source file AST."""
        try:
            tree = ast.parse(source)
        except Exception:
            return None

        # Check top-level and class-level definitions
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if node.name == sym_name:
                    return True
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == sym_name:
                        return True
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                for alias in node.names:
                    asname = alias.asname or alias.name
                    if asname == sym_name:
                        return True

        return False

    def _is_repo_local_import(self, repository_root: str, file_path: str, mod_name: str) -> bool:
        if not mod_name:
            return False
        if mod_name.startswith("."):
            return True
        top = mod_name.split(".")[0]
        if repository_root and os.path.isdir(repository_root):
            candidates = [top, f"src/{top}", f"{top}.py", f"src/{top}.py"]
            for c in candidates:
                if os.path.exists(os.path.join(repository_root, c)):
                    return True
            repo_base = os.path.basename(repository_root).replace("-", "_")
            if top == repo_base:
                return True
        if file_path:
            parts = file_path.split("/")
            first_part = parts[0]
            if first_part == "src" and len(parts) > 1:
                first_part = parts[1]
            if first_part in (top, f"{top}.py"):
                return True
        return False

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

        # 1. Check required imports used by the symbol
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

        # 2. Local Module Import Resolution: Check if referenced imported symbols actually exist in target repo files
        unresolved_local_dep = None
        if repository_root and target_commit and file_path:
            for dep in base_deps:
                target_mod_name = ""
                sym_imported = ""
                if "." in dep.qualified_name:
                    target_mod_name, sym_imported = dep.qualified_name.rsplit(".", 1)
                elif dep.imported_from and "." in dep.imported_from:
                    target_mod_name, sym_imported = dep.imported_from.rsplit(".", 1)

                if target_mod_name and sym_imported:
                    cand_paths = self._resolve_local_module_path(repository_root, file_path, target_mod_name)
                    found_mod = False
                    for cp in cand_paths:
                        target_mod_src = self._read_git_file(repository_root, target_commit, cp)
                        if target_mod_src is not None:
                            found_mod = True
                            # Module exists in target commit, verify symbol
                            exists = self._symbol_exists_in_ast(target_mod_src, sym_imported)
                            if exists is False:
                                return ValidityResult(
                                    decision="STALE",
                                    confidence=0.92,
                                    reasons=[f"Symbol `{sym_imported}` in local module `{cp}` removed in target commit."],
                                    evidence=[
                                        ValidityEvidence(
                                            evidence_type="local_dependency_symbol_missing",
                                            source="target_repo_ast_resolution",
                                            detail=f"Module `{cp}` found in target commit but symbol `{sym_imported}` is missing from its AST.",
                                            confidence=0.92
                                        )
                                    ],
                                    file_changed=None,
                                    symbol_changed=None,
                                    symbol_removed=None,
                                    dependency_changed=True
                                )
                            break
                    if not found_mod and self._is_repo_local_import(repository_root, file_path, target_mod_name):
                        unresolved_local_dep = dep.qualified_name

        if unresolved_local_dep:
            return ValidityResult(
                decision="UNCERTAIN",
                confidence=0.50,
                reasons=[f"Local repository dependency `{unresolved_local_dep}` could not be resolved in target commit."],
                evidence=[
                    ValidityEvidence(
                        evidence_type="unresolved_local_dependency",
                        source="target_repo_ast_resolution",
                        detail=f"Module path for local dependency `{unresolved_local_dep}` not found in target repo tree.",
                        confidence=0.50
                    )
                ],
                file_changed=None,
                symbol_changed=None,
                symbol_removed=None,
                dependency_changed=None
            )


        # 3. Check for explicit diff-based removals of referenced attributes/symbols
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

