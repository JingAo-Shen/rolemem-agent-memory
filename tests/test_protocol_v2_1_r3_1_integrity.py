"""
tests/test_protocol_v2_1_r3_1_integrity.py

Rigorous Protocol V2.1-R3.1 Benchmark Integrity Test Suite:
1. test_no_synthetic_symbol_digest(): Verifies zero synthetic surrogate SHA digests.
2. test_cat_d1_d2_taxonomy_disjoint(): Verifies strict disjointness of D1 and D2 taxonomy.
3. test_absolute_repo_local_unresolved_is_uncertain(): Verifies fail-uncertain for unresolvable repo-local imports.
4. test_human_annotation_semantic_blindness(): Verifies zero gold/category/editorial leakage in human annotation package.
"""

import os
import re
import json
import hashlib
import tempfile
import subprocess
import pytest

from src.validity import DependencyValidityChecker

DATA_DIR = "/code/rolemem-agent-memory/data/memory_validity_v2_1"
GOLD_PATH = os.path.join(DATA_DIR, "gold_labels.jsonl")
BLIND_PATH = os.path.join(DATA_DIR, "blind_inputs.jsonl")
PKG_PATH = os.path.join(DATA_DIR, "human_annotation_package_v2_1.jsonl")


def load_gold_records():
    with open(GOLD_PATH, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def load_pkg_records():
    with open(PKG_PATH, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def test_no_synthetic_symbol_digest():
    """Checks that zero synthetic surrogate digests (e.g. sha256 of symbol name string) are used in benchmark."""
    records = load_gold_records()
    assert len(records) > 0, "Gold labels cannot be empty"

    with open(os.path.join(DATA_DIR, "case_id_map_private.json"), "r", encoding="utf-8") as f:
        private_map = json.load(f)

    for r in records:
        cid = r["case_id"]
        sym_name = private_map[cid]["symbol_qualified_name"]
        
        # Compute surrogate digests
        surrogate_1 = hashlib.sha256(sym_name.encode("utf-8")).hexdigest()
        surrogate_2 = hashlib.sha256((sym_name + "_v2").encode("utf-8")).hexdigest()
        surrogate_3 = hashlib.sha256((sym_name + "_base").encode("utf-8")).hexdigest()

        b_dig = r.get("symbol_digest_base", "")
        t_dig = r.get("symbol_digest_target", "")

        assert b_dig not in (surrogate_1, surrogate_2, surrogate_3), f"Case {cid} has synthetic surrogate base digest!"
        if t_dig != "NONE":
            assert t_dig not in (surrogate_1, surrogate_2, surrogate_3), f"Case {cid} has synthetic surrogate target digest!"


def test_cat_d1_d2_taxonomy_disjoint():
    """Checks strict taxonomy disjointness between Category D1 and Category D2."""
    records = load_gold_records()
    d1_cases = [r for r in records if r["category"] == "CAT_D1_SYM_REM_STALE"]
    d2_cases = [r for r in records if r["category"] == "CAT_D2_SYM_CHG_BEHAVIOR_STALE"]

    assert len(d1_cases) > 0, "Cat D1 must contain cases"
    assert len(d2_cases) > 0, "Cat D2 must contain cases"

    d1_ids = {r["case_id"] for r in d1_cases}
    d2_ids = {r["case_id"] for r in d2_cases}
    assert d1_ids.isdisjoint(d2_ids), f"D1 and D2 case IDs overlap: {d1_ids & d2_ids}"

    # D1 cases must have symbol_digest_target == "NONE" (removed symbols)
    for r in d1_cases:
        assert r["symbol_digest_target"] == "NONE", f"D1 case {r['case_id']} target digest is not NONE: {r['symbol_digest_target']}"
        assert r["gold_label"] == "STALE"
        assert r["symbol_changed"] is True

    # D2 cases must have symbol_digest_target != "NONE" (changed symbols with behavior breaks)
    for r in d2_cases:
        assert r["symbol_digest_target"] != "NONE", f"D2 case {r['case_id']} target digest is NONE"
        assert r["symbol_digest_target"] != r["symbol_digest_base"], f"D2 case {r['case_id']} digests are identical"
        assert r["gold_label"] == "STALE"
        assert r["symbol_changed"] is True


def test_absolute_repo_local_unresolved_is_uncertain():
    """Checks that DependencyValidityChecker returns UNCERTAIN when a repo-local import cannot be resolved."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_dir = os.path.join(tmpdir, "repo")
        os.makedirs(repo_dir)

        subprocess.run(["git", "init"], cwd=repo_dir, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=repo_dir, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo_dir, check=True)

        # Create package directory structure (mypkg is definitely repo-local)
        os.makedirs(os.path.join(repo_dir, "src", "mypkg"), exist_ok=True)
        init_path = os.path.join(repo_dir, "src", "mypkg", "__init__.py")
        with open(init_path, "w", encoding="utf-8") as f:
            f.write("# init\n")

        # app.py imports from an unresolvable submodule mypkg.dynamically_generated
        app_code = "from mypkg.dynamically_generated import special_helper\n\ndef main():\n    return special_helper()\n"
        app_path = os.path.join(repo_dir, "src", "mypkg", "app.py")
        with open(app_path, "w", encoding="utf-8") as f:
            f.write(app_code)

        subprocess.run(["git", "add", "-A"], cwd=repo_dir, check=True)
        subprocess.run(["git", "commit", "-m", "base commit"], cwd=repo_dir, check=True)
        base_commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo_dir, capture_output=True, text=True).stdout.strip()

        # Target commit: app.py is unchanged, but mypkg.dynamically_generated remains unresolvable via AST in target commit
        subprocess.run(["git", "commit", "--allow-empty", "-m", "target commit"], cwd=repo_dir, check=True)
        target_commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo_dir, capture_output=True, text=True).stdout.strip()

        dep_checker = DependencyValidityChecker()
        result = dep_checker.evaluate(
            base_source=app_code,
            target_source=app_code,
            symbol_qualified_name="main",
            repository_root=repo_dir,
            base_commit=base_commit,
            target_commit=target_commit,
            file_path="src/mypkg/app.py"
        )

        assert result.decision == "UNCERTAIN", f"Expected UNCERTAIN for unresolvable repo-local import, got {result.decision}"
        assert any("unresolved_local_dependency" in e.evidence_type for e in result.evidence)


def test_human_annotation_semantic_blindness():
    """Checks that human_annotation_package_v2_1.jsonl contains zero gold labels, category tags, or researcher bias."""
    assert os.path.exists(PKG_PATH), "human_annotation_package_v2_1.jsonl must exist"

    banned_keys = {"gold", "gold_label", "category", "gold_category", "expected", "expected_decision", "expected_label", "ground_truth"}
    banned_phrases = [
        "verified valid",
        "verified stale",
        "dependency break confirmed",
        "behavioral break verified",
        "ast removal",
        "ast digest match",
        "expected answer",
        "expected label",
        "expected decision",
    ]

    records = load_pkg_records()
    assert len(records) > 0, "Package records cannot be empty"

    for r in records:
        cid = r["case_id"]
        # 1. No leaked keys
        for bk in banned_keys:
            assert bk not in r, f"Case {cid} contains leaked key '{bk}'"

        # 2. Check metadata & editorial fields for banned phrases
        for field in ["case_id", "repository", "symbol_qualified_name", "memory_statement"]:
            val = str(r.get(field, "")).lower()
            for bp in banned_phrases:
                assert bp not in val, f"Case {cid} field '{field}' contains banned phrase '{bp}': {val}"

        # 3. Execution object must be raw exit codes only
        exec_info = r.get("execution", {})
        assert isinstance(exec_info, dict)
        for k in ["base_exit_code", "target_exit_code", "stderr_excerpt"]:
            assert k in exec_info, f"Case {cid} missing '{k}' in execution dict"
        for bp in banned_phrases:
            assert bp not in str(exec_info.get("stderr_excerpt", "")).lower()
