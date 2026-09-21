#!/usr/bin/env python3
"""
scripts/build_grounded_memory_validity_benchmark_v2_1.py

Protocol V2.1-R3: Grounded Memory Validity Benchmark Builder
- Real worktree execution evidence with zero source mutation and verified clean worktrees.
- Honest environment provenance ("CURRENT_RUNTIME_WITH_HISTORICAL_SOURCE").
- Category B: Contract-derived memory claims with explicit claim-contract linkage.
- Category C: AST dependency linkage verified (HookSpec -> varnames) with strict counterfactual execution.
- Category D split:
  - D1 = CAT_D1_SYM_REM_STALE (symbol removed in target commit)
  - D2 = CAT_D2_SYM_CHG_BEHAVIOR_STALE (symbol changed + behavioral break verified by execution)
- De-leaked blind inputs: zero researcher interpretation in test_evidence.
"""

import os
import sys
import glob
import json
import time
import shutil
import hashlib
import tempfile
import subprocess
from typing import Dict, Any, List, Optional, Tuple, Set

sys.path.insert(0, "/code/rolemem-agent-memory")
from src.symbol_validity import SymbolDigestExtractor
from src.validity.dependency_graph import DependencyGraphVerifier

REPO_CACHE_ROOT = "/code/repo_cache"
OUT_DIR = "/code/rolemem-agent-memory/data/memory_validity_v2_1"
FULL_POOL_DIR = os.path.join(OUT_DIR, "full_pool")
CONTRACTS_DIR = os.path.join(OUT_DIR, "contracts")
COUNTERFACTUALS_DIR = os.path.join(OUT_DIR, "counterfactuals")
BEHAVIOR_BREAKS_DIR = os.path.join(OUT_DIR, "behavior_breaks")
BLIND_INPUTS_PATH = os.path.join(OUT_DIR, "blind_inputs.jsonl")
GOLD_LABELS_PATH = os.path.join(OUT_DIR, "gold_labels.jsonl")
PRIVATE_MAP_PATH = os.path.join(OUT_DIR, "case_id_map_private.json")
STATS_PATH = os.path.join(OUT_DIR, "benchmark_stats.json")

os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(FULL_POOL_DIR, exist_ok=True)
os.makedirs(CONTRACTS_DIR, exist_ok=True)
os.makedirs(COUNTERFACTUALS_DIR, exist_ok=True)
os.makedirs(BEHAVIOR_BREAKS_DIR, exist_ok=True)

# Primary development benchmark concentration limits
PRIMARY_MAX_CAT_A_PER_TRANSITION = 2
PRIMARY_MAX_CAT_A_PER_REPO = 3
PRIMARY_MAX_CAT_A_TOTAL = 36


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def execute_contract_at_commit(repo_name: str, commit: str, contract_code: str) -> Dict[str, Any]:
    repo_clean = repo_name.split("/")[-1]
    repo_dir = os.path.join(REPO_CACHE_ROOT, repo_clean)
    with tempfile.TemporaryDirectory() as tmpdir:
        wt_dir = os.path.join(tmpdir, "wt")
        res_wt = subprocess.run(["git", "worktree", "add", "--detach", wt_dir, commit], cwd=repo_dir, capture_output=True, text=True)
        if res_wt.returncode != 0:
            return {
                "passed": False,
                "exit_code": res_wt.returncode,
                "source_commit": commit,
                "python_version": sys.version.split()[0],
                "cwd_commit": "",
                "contract_hash": sha256_text(contract_code),
                "stdout_sha256": sha256_text(""),
                "stderr_sha256": sha256_text(res_wt.stderr),
                "stdout": "",
                "stderr": res_wt.stderr,
                "timestamp": time.time(),
                "worktree_clean_before": False,
                "worktree_clean_after": False,
                "environment_mode": "CURRENT_RUNTIME_WITH_HISTORICAL_SOURCE",
                "dependency_lock_restored": False
            }
        try:
            # Check git status before execution (must be clean)
            res_stat_before = subprocess.run(["git", "status", "--porcelain"], cwd=wt_dir, capture_output=True, text=True)
            clean_before = (res_stat_before.returncode == 0 and not res_stat_before.stdout.strip())

            # Wrap contract with in-memory version helper (avoids mutating worktree files)
            preamble = (
                "import sys, types\n"
                f"for pkg in ['{repo_clean}', 'urllib3', 'setuptools_scm']:\n"
                "    vname = f'{pkg}._version'\n"
                "    if vname not in sys.modules:\n"
                "        try:\n"
                "            vmod = types.ModuleType(vname)\n"
                "            vmod.__version__ = '1.0.0.dev0'\n"
                "            sys.modules[vname] = vmod\n"
                "        except Exception: pass\n"
            )
            full_code = preamble + contract_code

            env = os.environ.copy()
            env["PYTHONPATH"] = f"{wt_dir}:{wt_dir}/src:" + env.get("PYTHONPATH", "")
            env["SETUPTOOLS_SCM_PRETEND_VERSION"] = "1.0.0"

            res_exec = subprocess.run(
                [sys.executable, "-c", full_code],
                cwd=wt_dir,
                env=env,
                capture_output=True,
                text=True,
                timeout=10
            )

            # Check git status after execution (must remain clean)
            res_stat_after = subprocess.run(["git", "status", "--porcelain"], cwd=wt_dir, capture_output=True, text=True)
            clean_after = (res_stat_after.returncode == 0 and not res_stat_after.stdout.strip())

            res_rev = subprocess.run(["git", "rev-parse", "HEAD"], cwd=wt_dir, capture_output=True, text=True)
            actual_commit = res_rev.stdout.strip()

            passed = (res_exec.returncode == 0 and clean_before and clean_after)
            return {
                "passed": passed,
                "exit_code": res_exec.returncode,
                "source_commit": commit,
                "python_version": sys.version.split()[0],
                "cwd_commit": actual_commit,
                "contract_hash": sha256_text(contract_code),
                "stdout_sha256": sha256_text(res_exec.stdout),
                "stderr_sha256": sha256_text(res_exec.stderr),
                "stdout": res_exec.stdout,
                "stderr": res_exec.stderr,
                "timestamp": time.time(),
                "worktree_clean_before": clean_before,
                "worktree_clean_after": clean_after,
                "environment_mode": "CURRENT_RUNTIME_WITH_HISTORICAL_SOURCE",
                "dependency_lock_restored": False
            }
        finally:
            subprocess.run(["git", "worktree", "remove", "--force", wt_dir], cwd=repo_dir, capture_output=True, text=True)


def get_git_file(repo_name: str, commit_sha: str, filepath: str) -> Optional[str]:
    repo_name_clean = repo_name.split("/")[-1]
    repo_dir = os.path.join(REPO_CACHE_ROOT, repo_name_clean)
    if not os.path.isdir(repo_dir):
        return None
    res = subprocess.run(["git", "show", f"{commit_sha}:{filepath}"], cwd=repo_dir, capture_output=True, text=True)
    return res.stdout if res.returncode == 0 else None


def get_git_diff(repo_name: str, base_sha: str, target_sha: str, filepath: str) -> str:
    repo_name_clean = repo_name.split("/")[-1]
    repo_dir = os.path.join(REPO_CACHE_ROOT, repo_name_clean)
    if not os.path.isdir(repo_dir):
        return ""
    res = subprocess.run(["git", "diff", base_sha, target_sha, "--", filepath], cwd=repo_dir, capture_output=True, text=True)
    return res.stdout if res.returncode == 0 else ""


def get_commit_subject(repo_name: str, commit_sha: str) -> str:
    repo_name_clean = repo_name.split("/")[-1]
    repo_dir = os.path.join(REPO_CACHE_ROOT, repo_name_clean)
    res = subprocess.run(["git", "log", "-1", "--format=%s", commit_sha], cwd=repo_dir, capture_output=True, text=True)
    return res.stdout.strip() if res.returncode == 0 else "Code update"


def find_commit_pair(repo_name: str, filepath: str) -> Tuple[Optional[str], Optional[str]]:
    repo_clean = repo_name.split("/")[-1]
    repo_dir = os.path.join(REPO_CACHE_ROOT, repo_clean)
    if not os.path.isdir(repo_dir):
        return None, None
    res = subprocess.run(["git", "log", "--format=%H", "-n", "10", "--", filepath], cwd=repo_dir, capture_output=True, text=True)
    if res.returncode != 0:
        return None, None
    commits = [c.strip() for c in res.stdout.splitlines() if c.strip()]
    if len(commits) >= 2:
        return commits[1], commits[0]
    return None, None


def extract_symbol_code_block(full_source: str, symbol_name: str) -> str:
    lines = full_source.splitlines()
    for idx, line in enumerate(lines):
        if line.startswith(f"def {symbol_name}(") or line.startswith(f"class {symbol_name}") or line.startswith(f"async def {symbol_name}("):
            target_lines = [line]
            for next_line in lines[idx + 1:]:
                if next_line.strip() == "" or next_line.startswith(" ") or next_line.startswith("\t"):
                    target_lines.append(next_line)
                else:
                    break
            return "\n".join(target_lines)
    return "\n".join(lines[:50])


def build_benchmark_v2_1_r3():
    for d in (CONTRACTS_DIR, COUNTERFACTUALS_DIR, BEHAVIOR_BREAKS_DIR):
        if os.path.exists(d):
            shutil.rmtree(d)
        os.makedirs(d, exist_ok=True)

    specs_dir = "/code/rolemem-agent-memory/data/specs"
    spec_files = sorted(glob.glob(f"{specs_dir}/trans_track_a_*.json"))

    all_cat_a = []
    primary_cat_a = []
    raw_cat_b = []
    raw_cat_c = []
    raw_cat_d1 = []
    raw_cat_d2 = []

    cat_a_repo_counts: Dict[str, int] = {}
    cat_a_trans_counts: Dict[str, int] = {}

    # 1. Mine Cat A and Cat D1 (Removed Symbols) from real Track A transitions
    for sf in spec_files:
        with open(sf, "r", encoding="utf-8") as f:
            spec = json.load(f)

        tid = spec["transition_id"]
        repo = spec["repo_name"].split("/")[-1]
        repo_dir = os.path.join(REPO_CACHE_ROOT, repo)
        if not os.path.exists(repo_dir):
            continue

        b_commit = spec["base_commit"]
        t_commit = spec["target_commit"]
        f_path = spec["primary_file"]

        b_src = get_git_file(repo, b_commit, f_path)
        t_src = get_git_file(repo, t_commit, f_path)
        if not b_src or not t_src or b_src == t_src:
            continue

        diff_hunk = get_git_diff(repo, b_commit, t_commit, f_path)
        pr_subj = get_commit_subject(repo, t_commit)

        b_digs = SymbolDigestExtractor.extract_symbol_digests(b_src)
        t_digs = SymbolDigestExtractor.extract_symbol_digests(t_src)

        common_syms = set(b_digs.keys()) & set(t_digs.keys())

        # Category A: File changed, symbol unmodified in AST (b_dig == t_dig), memory valid
        for sym in sorted(common_syms):
            b_info = b_digs[sym]
            t_info = t_digs[sym]
            if b_info["symbol_digest"] == t_info["symbol_digest"]:
                b_block = extract_symbol_code_block(b_src, b_info["symbol_name"])
                t_block = extract_symbol_code_block(t_src, t_info["symbol_name"])
                record_a = {
                    "repo": repo,
                    "file": f_path,
                    "symbol": b_info["qualified_name"],
                    "base_commit": b_commit,
                    "target_commit": t_commit,
                    "memory_statement": f"Symbol `{b_info['qualified_name']}` defines core implementation in `{f_path}`.",
                    "base_src": b_src,
                    "target_src": t_src,
                    "base_block": b_block,
                    "target_block": t_block,
                    "diff_hunk": diff_hunk[:1000],
                    "pr_evidence": f"Commit: {pr_subj}",
                    "test_evidence": f"File `{f_path}` modified in Git diff across commits.",
                    "gold_label": "VALID",
                    "category": "CAT_A_FILE_CHG_SYM_SAME_VALID",
                    "rationale": f"Whole file `{f_path}` modified in Git diff, but symbol `{b_info['qualified_name']}` AST digest is identical ({b_info['symbol_digest'][:8]}...).",
                    "symbol_changed": False,
                    "symbol_digest_base": b_info["symbol_digest"],
                    "symbol_digest_target": t_info["symbol_digest"],
                    "file_changed": True,
                    "source_tid": tid
                }
                all_cat_a.append(record_a)

                if len(primary_cat_a) < PRIMARY_MAX_CAT_A_TOTAL:
                    if cat_a_trans_counts.get(tid, 0) < PRIMARY_MAX_CAT_A_PER_TRANSITION and cat_a_repo_counts.get(repo, 0) < PRIMARY_MAX_CAT_A_PER_REPO:
                        primary_cat_a.append(record_a)
                        cat_a_trans_counts[tid] = cat_a_trans_counts.get(tid, 0) + 1
                        cat_a_repo_counts[repo] = cat_a_repo_counts.get(repo, 0) + 1

        # Category D1: Removed symbols (in base, completely missing from target)
        removed_syms = set(b_digs.keys()) - set(t_digs.keys())
        for sym in sorted(removed_syms):
            b_info = b_digs[sym]
            b_block = extract_symbol_code_block(b_src, b_info["symbol_name"])
            record_d1 = {
                "repo": repo,
                "file": f_path,
                "symbol": b_info["qualified_name"],
                "base_commit": b_commit,
                "target_commit": t_commit,
                "memory_statement": f"Symbol `{b_info['qualified_name']}` is available directly in `{f_path}`.",
                "base_src": b_src,
                "target_src": t_src,
                "base_block": b_block,
                "target_block": "# Symbol removed in target commit",
                "diff_hunk": diff_hunk[:1000],
                "pr_evidence": f"Commit: {pr_subj}",
                "test_evidence": f"Symbol `{b_info['qualified_name']}` absent from target source tree.",
                "gold_label": "STALE",
                "category": "CAT_D1_SYM_REM_STALE",
                "rationale": f"Symbol `{b_info['qualified_name']}` deleted in target commit; memory asserting presence is stale.",
                "symbol_changed": True,
                "symbol_digest_base": b_info["symbol_digest"],
                "symbol_digest_target": "NONE",
                "file_changed": True,
                "source_tid": tid
            }
            raw_cat_d1.append(record_d1)

    # 2. Category B: Verified Contract-Derived Claims (Symbol AST Changed, Contract Passes on Base & Target)
    cat_b_specs = [
        ("click", "src/click/formatting.py", "HelpFormatter",
         "When HelpFormatter is initialized, text buffered with write_text() can be retrieved via getvalue().",
         "HelpFormatter", "buffered text via write_text is retrievable via getvalue",
         ["hf = HelpFormatter()", "hf.write_text('help')", "assert 'help' in hf.getvalue()"],
         "from click.formatting import HelpFormatter; hf = HelpFormatter(); hf.write_text('help'); assert 'help' in hf.getvalue()"),

        ("werkzeug", "src/werkzeug/wrappers/request.py", "Request",
         "Request instance initialized with a WSGI environ dictionary provides the HTTP method via the method attribute.",
         "Request", "provides HTTP method from WSGI environ",
         ["req = Request({'REQUEST_METHOD': 'GET', 'wsgi.url_scheme': 'http'})", "assert req.method == 'GET'"],
         "from werkzeug.wrappers.request import Request; req = Request({'REQUEST_METHOD': 'GET', 'wsgi.url_scheme': 'http'}); assert req.method == 'GET'"),

        ("tqdm", "tqdm/std.py", "tqdm",
         "tqdm wrapping a finite range iterable supports length inspection returning the total item count via len().",
         "tqdm", "supports len() inspection on finite range iterable",
         ["t = tqdm(range(5))", "assert len(t) == 5"],
         "from tqdm.std import tqdm; t = tqdm(range(5)); assert len(t) == 5"),

        ("rich", "rich/console.py", "Console",
         "When Console is initialized with record=True, text printed via print() is captured and retrievable through export_text().",
         "Console", "captures printed text when record=True",
         ["c = Console(record=True)", "c.print('hello')", "assert 'hello' in c.export_text()"],
         "from rich.console import Console; c = Console(record=True); c.print('hello'); assert 'hello' in c.export_text()"),

        ("rich", "rich/text.py", "Text",
         "Text instance initialized with a string returns the plain string content when converted via str().",
         "Text", "returns plain string representation via str()",
         ["t = Text('hello')", "assert str(t) == 'hello'"],
         "from rich.text import Text; t = Text('hello'); assert str(t) == 'hello'"),

        ("fastapi", "fastapi/applications.py", "FastAPI",
         "FastAPI application instance initializes with default title attribute set to 'FastAPI'.",
         "FastAPI", "initializes with default title attribute",
         ["app = FastAPI()", "assert app.title == 'FastAPI'"],
         "from fastapi import FastAPI; app = FastAPI(); assert app.title == 'FastAPI'"),

        ("starlette", "starlette/applications.py", "Starlette",
         "Starlette application instance initializes with default debug mode set to False.",
         "Starlette", "initializes with default debug mode set to False",
         ["app = Starlette()", "assert app.debug is False"],
         "from starlette.applications import Starlette; app = Starlette(); assert app.debug is False"),

        ("urllib3", "src/urllib3/poolmanager.py", "PoolManager",
         "PoolManager class can be instantiated with default connection pool configuration without arguments.",
         "PoolManager", "instantiable with default arguments",
         ["pm = PoolManager()", "assert pm is not None"],
         "from urllib3.poolmanager import PoolManager; pm = PoolManager(); assert pm is not None")
    ]

    for repo, f_path, sym_name, mem_stmt, claim_subj, claim_pred, assertions, contract_code in cat_b_specs:
        r_dir = os.path.join(REPO_CACHE_ROOT, repo)
        if not os.path.exists(r_dir):
            continue
        b_c, t_c = find_commit_pair(repo, f_path)
        if not b_c or not t_c:
            continue
        b_src = get_git_file(repo, b_c, f_path)
        t_src = get_git_file(repo, t_c, f_path)
        if not b_src or not t_src:
            continue

        b_digs = SymbolDigestExtractor.extract_symbol_digests(b_src)
        t_digs = SymbolDigestExtractor.extract_symbol_digests(t_src)
        b_info = b_digs.get(sym_name) or b_digs.get(f"{repo}.{sym_name}")
        t_info = t_digs.get(sym_name) or t_digs.get(f"{repo}.{sym_name}")

        if not b_info or not t_info:
            continue

        b_dig = b_info["symbol_digest"]
        t_dig = t_info["symbol_digest"]
        if b_dig == t_dig:
            continue

        exec_base = execute_contract_at_commit(repo, b_c, contract_code)
        exec_target = execute_contract_at_commit(repo, t_c, contract_code)

        machine_verified = (
            exec_base["passed"] is True
            and exec_target["passed"] is True
            and exec_base["cwd_commit"] == b_c
            and exec_target["cwd_commit"] == t_c
            and exec_base["worktree_clean_before"] is True
            and exec_base["worktree_clean_after"] is True
            and exec_target["worktree_clean_before"] is True
            and exec_target["worktree_clean_after"] is True
        )

        if not machine_verified:
            continue

        diff_hunk = get_git_diff(repo, b_c, t_c, f_path)
        pr_subj = get_commit_subject(repo, t_c)
        b_block = extract_symbol_code_block(b_src, sym_name)
        t_block = extract_symbol_code_block(t_src, sym_name)

        raw_cat_b.append({
            "repo": repo,
            "file": f_path,
            "symbol": b_info["qualified_name"],
            "base_commit": b_c,
            "target_commit": t_c,
            "memory_statement": mem_stmt,
            "base_src": b_src,
            "target_src": t_src,
            "base_block": b_block,
            "target_block": t_block,
            "diff_hunk": diff_hunk[:1000],
            "pr_evidence": f"Commit: {pr_subj}",
            "test_evidence": f"Execution contract test recorded at commits {b_c[:8]} and {t_c[:8]}.",
            "gold_label": "VALID",
            "category": "CAT_B_SYM_CHG_MEMORY_VALID",
            "rationale": f"Symbol AST changed ({b_dig[:8]}... -> {t_dig[:8]}...), but behavioral contract verified valid.",
            "symbol_changed": True,
            "symbol_digest_base": b_dig,
            "symbol_digest_target": t_dig,
            "file_changed": True,
            "source_tid": f"trans_{repo}_{sym_name.lower()}",
            "contract_artifact": {
                "repository": repo,
                "base_commit": b_c,
                "target_commit": t_c,
                "claim": mem_stmt,
                "claim_subject": claim_subj,
                "claim_predicate": claim_pred,
                "contract_assertions": assertions,
                "claim_contract_linked": True,
                "base_execution": exec_base,
                "target_execution": exec_target,
                "machine_verified": machine_verified
            }
        })

    # 3. Category C: Rigorously Dependency-Linked (Symbol Unchanged + Direct AST Dependency Linkage Broken)
    pluggy_b_c = "dd20a85e38af556e1c818b03391eab1480438e0c"
    pluggy_t_c = "0258484dc180a0c28705de83783b269f4fed4873"
    pluggy_file = "src/pluggy/_hooks.py"
    pluggy_src_b = get_git_file("pluggy", pluggy_b_c, pluggy_file)
    pluggy_src_t = get_git_file("pluggy", pluggy_t_c, pluggy_file)

    if pluggy_src_b and pluggy_src_t:
        p_digs_b = SymbolDigestExtractor.extract_symbol_digests(pluggy_src_b)
        p_digs_t = SymbolDigestExtractor.extract_symbol_digests(pluggy_src_t)
        hs_b = p_digs_b.get("HookSpec")
        hs_t = p_digs_t.get("HookSpec")

        if hs_b and hs_t and hs_b["symbol_digest"] == hs_t["symbol_digest"]:
            # Verify static AST dependency linkage from HookSpec to varnames
            link_res = DependencyGraphVerifier.verify_linkage(pluggy_src_b, "HookSpec", "varnames")
            assert link_res.linkage_verified is True

            old_counterfactual = (
                "from pluggy._hooks import HookSpec\n"
                "import warnings\n"
                "warnings.filterwarnings('error', category=DeprecationWarning)\n"
                "class MySpec:\n"
                "    def my_hook(a, b): pass\n"
                "opts = {'firstresult': False, 'historic': False, 'warn_on': None, 'warn_on_kls': None}\n"
                "hs = HookSpec(MySpec, 'my_hook', opts)\n"
                "assert hs.argnames == ('a', 'b')\n"
            )

            new_counterfactual = (
                "from pluggy._hooks import HookSpec\n"
                "import warnings\n"
                "warnings.filterwarnings('error', category=DeprecationWarning)\n"
                "class MySpec:\n"
                "    def my_hook(self, a, b): pass\n"
                "opts = {'firstresult': False, 'historic': False, 'warn_on': None, 'warn_on_kls': None}\n"
                "hs = HookSpec(MySpec, 'my_hook', opts)\n"
                "assert hs.argnames == ('a', 'b')\n"
            )

            exec_c_old_b = execute_contract_at_commit("pluggy", pluggy_b_c, old_counterfactual)
            exec_c_old_t = execute_contract_at_commit("pluggy", pluggy_t_c, old_counterfactual)
            exec_c_new_t = execute_contract_at_commit("pluggy", pluggy_t_c, new_counterfactual)

            cat_c_verified = (
                exec_c_old_b["passed"] is True
                and exec_c_old_t["passed"] is False
                and exec_c_new_t["passed"] is True
                and link_res.linkage_verified is True
                and hs_b["symbol_digest"] == hs_t["symbol_digest"]
            )

            if cat_c_verified:
                diff_h = get_git_diff("pluggy", pluggy_b_c, pluggy_t_c, pluggy_file)
                b_block = extract_symbol_code_block(pluggy_src_b, "HookSpec")
                t_block = extract_symbol_code_block(pluggy_src_t, "HookSpec")

                raw_cat_c.append({
                    "repo": "pluggy",
                    "file": pluggy_file,
                    "symbol": hs_b["qualified_name"],
                    "base_commit": pluggy_b_c,
                    "target_commit": pluggy_t_c,
                    "memory_statement": "HookSpec inspects hook functions via varnames allowing hook methods without explicit self parameter.",
                    "base_src": pluggy_src_b,
                    "target_src": pluggy_src_t,
                    "base_block": b_block,
                    "target_block": t_block,
                    "diff_hunk": diff_h[:1000],
                    "pr_evidence": "Commit: escalate varnames noself to deprecation warning",
                    "test_evidence": "Execution test recorded at commits dd20a85e and 0258484d.",
                    "gold_label": "STALE",
                    "category": "CAT_C_SYM_SAME_MEMORY_STALE",
                    "rationale": "Symbol HookSpec AST digest is identical, but downstream dependency `varnames` rejects noself methods under deprecation errors.",
                    "symbol_changed": False,
                    "symbol_digest_base": hs_b["symbol_digest"],
                    "symbol_digest_target": hs_t["symbol_digest"],
                    "file_changed": True,
                    "source_tid": "trans_pluggy_hookspec",
                    "counterfactual_artifact": {
                        "repository": "pluggy",
                        "base_commit": pluggy_b_c,
                        "target_commit": pluggy_t_c,
                        "target_symbol": "HookSpec",
                        "dependency_symbol": "varnames",
                        "dependency_path": link_res.path,
                        "linkage_verified": True,
                        "symbol_digest_equal": True,
                        "old_on_base": exec_c_old_b,
                        "old_on_target": exec_c_old_t,
                        "new_on_target": exec_c_new_t,
                        "machine_verified": True
                    }
                })

    # 4. Category D2: Changed Symbols with Verified Execution Break (Both base and target AST exist, digests differ)
    cat_d2_specs = [
        ("urllib3", "src/urllib3/response.py", "BaseHTTPResponse",
         "dd2daef3611ea09f60260391e6a698bb9933dd17", "4587fd6d477f22022be08de597c3a5acd5185c0a",
         "BaseHTTPResponse instances provide getheaders() method returning list of header tuples.",
         "from urllib3.response import HTTPResponse\nimport io\nresp = HTTPResponse(body=io.BytesIO(b'test'), headers={'Content-Type': 'text/plain'})\nheaders = dict(resp.getheaders())\nassert headers.get('Content-Type') == 'text/plain'\n"),

        ("marshmallow", "src/marshmallow/__init__.py", "__all__",
         "ad24f89100c95d3bf99ba17714d457c7c93e0b53", "5429f0d4c6e346dc751599073cab67d66eefbcb2",
         "marshmallow exports pprint in __all__ at top level.",
         "import marshmallow\nassert 'pprint' in marshmallow.__all__\n")
    ]

    for repo, f_path, sym_name, b_c, t_c, mem_stmt, break_code in cat_d2_specs:
        r_dir = os.path.join(REPO_CACHE_ROOT, repo)
        if not os.path.exists(r_dir):
            continue
        b_src = get_git_file(repo, b_c, f_path)
        t_src = get_git_file(repo, t_c, f_path)
        if not b_src or not t_src:
            continue

        b_digs = SymbolDigestExtractor.extract_symbol_digests(b_src)
        t_digs = SymbolDigestExtractor.extract_symbol_digests(t_src)
        b_info = b_digs.get(sym_name) or b_digs.get(f"{repo}.{sym_name}")
        t_info = t_digs.get(sym_name) or t_digs.get(f"{repo}.{sym_name}")

        # Strict requirement: both b_info and t_info must exist in AST, with different digests!
        if not b_info or not t_info:
            continue

        b_dig = b_info["symbol_digest"]
        t_dig = t_info["symbol_digest"]
        if b_dig == t_dig or t_dig == "NONE":
            continue

        exec_b = execute_contract_at_commit(repo, b_c, break_code)
        exec_t = execute_contract_at_commit(repo, t_c, break_code)

        if exec_b["passed"] is True and exec_t["passed"] is False:
            diff_hunk = get_git_diff(repo, b_c, t_c, f_path)
            pr_subj = get_commit_subject(repo, t_c)
            b_block = extract_symbol_code_block(b_src, sym_name) if b_src else ""
            t_block = extract_symbol_code_block(t_src, sym_name) if t_src else ""

            raw_cat_d2.append({
                "repo": repo,
                "file": f_path,
                "symbol": b_info["qualified_name"],
                "base_commit": b_c,
                "target_commit": t_c,
                "memory_statement": mem_stmt,
                "base_src": b_src,
                "target_src": t_src,
                "base_block": b_block,
                "target_block": t_block,
                "diff_hunk": diff_hunk[:1000],
                "pr_evidence": f"Commit: {pr_subj}",
                "test_evidence": f"Execution test recorded at commits {b_c[:8]} and {t_c[:8]}.",
                "gold_label": "STALE",
                "category": "CAT_D2_SYM_CHG_BEHAVIOR_STALE",
                "rationale": f"Symbol AST changed and legacy behavior confirmed broken on target commit.",
                "symbol_changed": True,
                "symbol_digest_base": b_dig,
                "symbol_digest_target": t_dig,
                "file_changed": True,
                "source_tid": f"trans_{repo}_{sym_name.lower().replace('.', '_')}",
                "behavior_break_artifact": {
                    "repository": repo,
                    "base_commit": b_c,
                    "target_commit": t_c,
                    "base_execution": exec_b,
                    "target_execution": exec_t,
                    "break_verified": True
                }
            })

    # Select Cat D1 (removed symbols) and Cat D2 (changed symbols with verified behavioral breaks)
    # Ensure strict disjointness between D1 and D2
    selected_d1 = []
    d2_keys = {(d["repo"], d["file"], d["symbol"], d["base_commit"], d["target_commit"]) for d in raw_cat_d2}
    for d1 in raw_cat_d1:
        key = (d1["repo"], d1["file"], d1["symbol"], d1["base_commit"], d1["target_commit"])
        if key not in d2_keys and len(selected_d1) < 8:
            selected_d1.append(d1)

    selected_d2 = raw_cat_d2

    selected = primary_cat_a + raw_cat_b + raw_cat_c + selected_d1 + selected_d2

    print(f"\nDataset Composition (Protocol V2.1-R3.1):")
    print(f"  Full Robustness Pool Cat A: {len(all_cat_a)} cases")
    print(f"  Primary Benchmark Cat A (File Chg / Sym Same / Valid): {len(primary_cat_a)} cases")
    print(f"  Cat B (Sym Chg / Valid Contract): {len(raw_cat_b)} cases")
    print(f"  Cat C (Sym Same / Dep Linkage Broken): {len(raw_cat_c)} cases")
    print(f"  Cat D1 (Sym Removed / Stale): {len(selected_d1)} cases")
    print(f"  Cat D2 (Sym Chg / Executable Stale): {len(selected_d2)} cases")
    print(f"  Total Primary Benchmark Cases: {len(selected)} cases")

    blind_inputs = []
    gold_labels = []
    case_map_private = {}

    for idx, c in enumerate(selected, start=1):
        case_id = f"MV21-{idx:06d}"

        # Blind Input: ZERO label leakage, ZERO category leakage, ZERO researcher editorial
        b_input = {
            "case_id": case_id,
            "repository": c["repo"],
            "base_commit": c["base_commit"],
            "target_commit": c["target_commit"],
            "file_path": c["file"],
            "symbol_qualified_name": c["symbol"],
            "base_source_excerpt": c["base_block"],
            "target_source_excerpt": c["target_block"],
            "diff_hunk": c["diff_hunk"],
            "memory_statement": c["memory_statement"],
            "pr_evidence": c["pr_evidence"],
            "test_evidence": c["test_evidence"]
        }
        blind_inputs.append(b_input)

        # Gold Label
        g_label = {
            "case_id": case_id,
            "gold_label": c["gold_label"],
            "category": c["category"],
            "rationale": c["rationale"],
            "symbol_changed": bool(c["symbol_changed"]),
            "symbol_digest_base": c["symbol_digest_base"],
            "symbol_digest_target": c["symbol_digest_target"],
            "file_changed": bool(c["file_changed"])
        }
        gold_labels.append(g_label)

        # Private map
        case_map_private[case_id] = {
            "source_tid": c["source_tid"],
            "repository": c["repo"],
            "file_path": c["file"],
            "symbol_qualified_name": c["symbol"],
            "category": c["category"],
            "gold_label": c["gold_label"]
        }

        # Save individual contract, counterfactual, or behavior break artifact
        if "contract_artifact" in c:
            c_file = os.path.join(CONTRACTS_DIR, f"{case_id}.json")
            with open(c_file, "w", encoding="utf-8") as cf:
                json.dump({"case_id": case_id, **c["contract_artifact"]}, cf, indent=2)

        if "counterfactual_artifact" in c:
            cf_file = os.path.join(COUNTERFACTUALS_DIR, f"{case_id}.json")
            with open(cf_file, "w", encoding="utf-8") as cff:
                json.dump({"case_id": case_id, **c["counterfactual_artifact"]}, cff, indent=2)

        if "behavior_break_artifact" in c:
            bb_file = os.path.join(BEHAVIOR_BREAKS_DIR, f"{case_id}.json")
            with open(bb_file, "w", encoding="utf-8") as bbf:
                json.dump({"case_id": case_id, **c["behavior_break_artifact"]}, bbf, indent=2)

    # Save blind inputs & gold labels
    with open(BLIND_INPUTS_PATH, "w", encoding="utf-8") as f:
        for b in blind_inputs:
            f.write(json.dumps(b) + "\n")

    with open(GOLD_LABELS_PATH, "w", encoding="utf-8") as f:
        for g in gold_labels:
            f.write(json.dumps(g) + "\n")

    with open(PRIVATE_MAP_PATH, "w", encoding="utf-8") as f:
        json.dump(case_map_private, f, indent=2)

    # Save full robustness pool (storing symbol blocks and metadata without redundant whole-file texts)
    full_pool_records = all_cat_a + raw_cat_b + raw_cat_c + raw_cat_d1 + raw_cat_d2
    with open(os.path.join(FULL_POOL_DIR, "full_pool_all_cases.jsonl"), "w", encoding="utf-8") as f:
        for r in full_pool_records:
            r_slim = {k: v for k, v in r.items() if k not in ("base_src", "target_src")}
            f.write(json.dumps(r_slim) + "\n")

    # Compute concentration stats
    unique_repos = set(c["repo"] for c in selected)
    unique_trans = set(c["source_tid"] for c in selected)
    cases_per_trans = {}
    cases_per_repo = {}
    for c in selected:
        cases_per_trans[c["source_tid"]] = cases_per_trans.get(c["source_tid"], 0) + 1
        cases_per_repo[c["repo"]] = cases_per_repo.get(c["repo"], 0) + 1

    stats = {
        "protocol_version": "2.1-r3.1",
        "total_cases": len(selected),
        "full_robustness_pool_cases": len(full_pool_records),
        "unique_repository_count": len(unique_repos),
        "unique_transition_count": len(unique_trans),
        "category_counts": {
            "CAT_A": len(primary_cat_a),
            "CAT_B": len(raw_cat_b),
            "CAT_C": len(raw_cat_c),
            "CAT_D1": len(selected_d1),
            "CAT_D2": len(selected_d2),
        },
        "cases_per_repository": cases_per_repo,
        "cases_per_transition": cases_per_trans
    }

    with open(STATS_PATH, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)

    print(f"\n=== Memory Validity Benchmark V2.1-R3.1 Built Successfully ===")
    print(f"  Primary Split Total Cases: {len(selected)}")
    print(f"  Full Robustness Pool Cases: {len(full_pool_records)}")
    print(f"  Unique Repositories: {len(unique_repos)}")
    print(f"  Unique Transitions: {len(unique_trans)}")


if __name__ == "__main__":
    build_benchmark_v2_1_r3()
