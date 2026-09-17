# Pilot-v1.2d-r1 Final Review: Semantic Grounding Repair & Seed Hardening

> [!IMPORTANT]
> **Scientific Status Declaration**:
> - `PILOT_V1_2D`: **REOPENED** (Strictly undergoing semantic grounding repair)
> - `BENCHMARK_FREEZE`: **NO** (Not frozen; truthfulness precedes freezing)
> - `FORMAL_RESULTS`: **NO** (No formal paper claims of model/method superiority)
> - `GOLD_EXPANSION`: **NO** (Expansion to 40-80 tasks prohibited until seed integrity is verified)
> - `CANDIDATE_MINING`: **YES** (Candidate mining into `data/candidates/` permitted; no automatic promotion)

---

## 1. TransitionVerifierV5 Master Gate Results (10 Seed Candidates)

`TransitionVerifierV5` evaluates 8 sequential gates, including a 10-layer semantic coherence audit and a 2x2 causal counterfactual matrix:

| Transition ID | Commit | 10-Layer Semantics | Dual GT v2 | 2x2 Causal | Orig Test | Hidden Test | Controls | Hash Bind | Final Status |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `trans_gold_click_01_option_parser` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **SEED_ACCEPT** |
| `trans_gold_click_02_isolated_filesystem` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **SEED_ACCEPT** |
| `trans_gold_flask_01_context_stack_removal` | PASS | PASS | PASS | **FAIL** | PASS | PASS | PASS | PASS | **REBUILD** |
| `trans_gold_flask_02_should_ignore_error` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **SEED_ACCEPT** |
| `trans_gold_requests_01_tls_context_adapter` | PASS | PASS | PASS | PASS | WAIVED | PASS | PASS | PASS | **SEED_ACCEPT** |
| `trans_gold_requests_02_pool_key_overrides` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **SEED_ACCEPT** |
| `trans_gold_urllib3_01_retry_allowed_methods` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **SEED_ACCEPT** |
| `trans_gold_urllib3_02_empty_allowed_methods` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **SEED_ACCEPT** |
| `trans_gold_werkzeug_01_cached_property` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **SEED_ACCEPT** |
| `trans_gold_werkzeug_02_environ_properties` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **SEED_ACCEPT** |

**Final Seed Benchmark Tally**:
- **SEED_ACCEPT**: **9** (90%)
- **REBUILD**: **1** (`trans_gold_flask_01_context_stack_removal`)
- **REJECT**: **0**

---

## 2. Answers to Mandatory Review Questions (Q1 – Q9)

### Q1: Dual-source External Ground Truth Audit v2 结果如何？
**Answer**: **10/10 PASS (100%)**.
`scripts/audit_external_ground_truth_v2.py` performed dual-source verification against local bare Git repositories (`/code/repo_cache/`) and Git PR head refs (`refs/pull/<num>/head`):
- All commit SHAs exist and match their respective Git trees.
- PR numbers match actual merge/squash references in the repository commit logs.
- PR titles match commit subjects.
- Changed files match the true Git diff between `base_commit` and `target_commit`.
- All audit JSON records in `data/ground_truth_audit_v2/<tid>.json` cryptographically record `spec_sha256` and `auditor_version: "2.0.0"`.

### Q2: 10-layer Semantic Coherence Gate 是否全部通过？
**Answer**: **10/10 PASS (100%)**.
`scripts/audit_semantic_coherence.py` verified all 10 invariance layers:
1. PR diff matches repository change.
2. Causality statement accurately reflects code modification.
3. Stale memory references actual deprecated symbols.
4. Valid memory references modern replacement symbols.
5. Task requires interacting with transition symbol.
6. Target file and symbol exist in fixture repository state.
7. Hidden test exercises transition behavior without solution leakage.
8. Stale control fails or emits deprecation warnings on target snapshot.
9. Valid control passes cleanly on target snapshot.
10. Specification SHA256 checksum bound to audit state.
Results saved in `data/semantic_audit/<tid>.json`.

### Q3: Click 02, Requests 01 与 urllib3 02 的重建与对齐结果如何？
**Answer**: Successfully rebuilt and aligned:
- **Click 02 (`trans_gold_click_02_isolated_filesystem`)**: Rebuilt from true Click PR #3704. Prior false claim that PR introduced `temp_dir` was eliminated; the true transition deprecated `CliRunner.isolated_filesystem` in favor of pytest `tmp_path`. Spec, fixture files, stale control, and modern valid control were completely rewritten. Passed 2x2 causal matrix and E2E handoff.
- **Requests 01 (`trans_gold_requests_01_tls_context_adapter`)**: Rebuilt from true Requests PR #6710. Deprecated `HTTPAdapter.get_connection` in favor of `get_connection_with_tls_context`. Because the PR did not modify repository test files, the spec was formally marked `original_test_required: false` and `generated_hidden_test_only: true`. Passed 2x2 causal matrix.
- **urllib3 02 (`trans_gold_urllib3_02_empty_allowed_methods`)**: Aligned target file (`retry_factory.py`), target symbol (`create_all_verbs_retry`), and controls (`allowed_methods=None` vs `allowed_methods=[]`). Passed 2x2 causal matrix.

### Q4: 2x2 Causal Counterfactual Matrix 结果如何？哪些失败及其原因？
**Answer**: **9 PASS, 1 FAIL**.
- **9 CAUSALITY_PASS**: `click_01`, `click_02`, `flask_02`, `requests_01`, `requests_02`, `urllib3_01`, `urllib3_02`, `werkzeug_01`, `werkzeug_02`.
- **1 TRANSITION_NOT_CAUSAL**: `trans_gold_flask_01_context_stack_removal`.
  - **Reason**: In base commit `604de4b1a4`, `_app_ctx_stack` was already deprecated with active `DeprecationWarning` emissions. Running `stale_solution` against the base snapshot failed the warning-free pytest gate (`stale_base == FAIL`). PR #4682 removed the stack, but did not originate the deprecation. In accordance with strict truthfulness, it is classified as `REBUILD` rather than forced to pass.

### Q5: TransitionVerifierV5 最终裁决分布如何？
**Answer**:
- **SEED_ACCEPT**: **9**
- **REBUILD**: **1** (`flask_01`)
- **REJECT**: **0**
Results recorded in `data/verifier_results_v5/` and `data/seed_status_v5.jsonl`.

### Q6: AST Stale Action Detector 的升级与早期误报撤回情况？
**Answer**:
- **Retraction**: The earlier claim of "AST Clean 4/4 (100%)" is formally retracted.
- **Upgrade**: `src/stale_detector_ast.py` was upgraded to inspect function call `keyword` arguments (`kw.arg`) and structured `stale_action_patterns` (e.g. `node_type: "keyword"`, `name: "method_whitelist"`). Verified by 11/11 unit tests in `tests/test_stale_detector_ast.py`.
- **Re-evaluation**: On Qwen2.5-Coder-7B raw generation for `trans_gold_urllib3_01`, the model called `Retry(method_whitelist=methods)`. The upgraded detector accurately caught this stale usage.
- **True AST Clean Rate**: **3 / 4 (75.0%)**.

### Q7: Track B 的正向 Seed 验证结果如何？
**Answer**: **2 / 2 Qualified Positive Seeds (Memory Lift = +1.00 >= 0.67)**.
Track B represents **Project-Specific Architectural Conventions / Decisions** that cannot be deduced from general pre-training priors:
1. `track_b_urllib3_custom_retry`:
   - $S_0$ (No Memory): TSR = **0 / 3 (0.00)** (Guessed default retry parameters, failed test)
   - $S_2$ (With Memory): TSR = **3 / 3 (1.00)** (Configured exact project parameters `Retry(total=5, backoff_factor=0.5, status_forcelist=[429, 503])`)
   - **Memory Lift**: $\Delta \text{TSR} = 1.00 - 0.00 = \mathbf{+1.00}$ (Qualified: $\ge 0.67$)
2. `track_b_requests_service_adapter`:
   - $S_0$ (No Memory): TSR = **0 / 3 (0.00)** (Guessed default pool parameters, failed test)
   - $S_2$ (With Memory): TSR = **3 / 3 (1.00)** (Configured exact project parameters `HTTPAdapter(pool_connections=25, pool_maxsize=50, pool_block=True)`)
   - **Memory Lift**: $\Delta \text{TSR} = 1.00 - 0.00 = \mathbf{+1.00}$ (Qualified: $\ge 0.67$)
Full execution telemetry recorded in `data/track_b_evaluation.json`.

### Q8: Oracle-Memory True E2E 与 Agent-Generated Handoff E2E 的方法学差异？
**Answer**:
- **Oracle-Memory True E2E** (`runs/true-rolemem-e2e/`): Evaluates retrieval and execution when memories are curated by human/oracle specifications. Tests artifact digest invalidation, role projection bonus, and prompt assembly. Achieved TSR = 0.50 (2/4).
- **Agent-Generated Handoff E2E** (`runs/agent-generated-handoff-e2e/`): Evaluates autonomous end-to-end memory lifecycle where Agent A reads raw git diffs and writes structured memories, and Agent B reads them to solve downstream tasks. Achieved TSR = 0.50 (2/4), AST Clean = 0.75 (3/4), Memory Write Precision = 1.0, Recall = 1.0, Attribution Accuracy = 1.0.
- **Strict Separation**: These two pipelines are kept in independent run directories and separate reports to avoid conflating memory distillation quality with memory consumption efficiency.

### Q9: 当前项目处于什么阶段？是否可以 Benchmark Freeze 或宣称 RoleMem 优越性？
**Answer**:
- **Benchmark Freeze**: **NO**. The seed benchmark currently contains 9 verified `SEED_ACCEPT` transitions and 1 `REBUILD`.
- **RoleMem Superiority Claim**: **STRICTLY NO**. No formal paper claims or baseline comparisons may be made at this stage.
- **Candidate Mining**: **YES**. Mining of 40–80 raw candidates into `data/candidates/` may proceed, but none will be promoted to Gold without passing the full 8-gate `TransitionVerifierV5`.
- **Immediate Next Step**: Rebuild `trans_gold_flask_01` (by identifying a clean pre-deprecation base commit or replacing it with an alternative clean Flask transition), then run candidate mining.
