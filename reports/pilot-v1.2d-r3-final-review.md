# Pilot-v1.2d-r3 Final Evaluation Integrity Review

**Audit Version**: `Pilot-v1.2d-r3`  
**Execution Timestamp**: 2026-09-18  
**Verification Engine**: `TransitionVerifierV7` (Eight-Gate Cryptographic Machine Evidence Verifier)  
**Gold Expansion Status**: **`GOLD_EXPANSION = NO`**  
**Benchmark Freeze**: `BENCHMARK_FREEZE = NO`  
**Formal Results**: `FORMAL_RESULTS = NO`  
**Candidate Mining**: `CANDIDATE_MINING = YES`

---

## 1. Section 18 Compliance Checklist

| Criterion | Required Threshold | Observed Result | Status |
| :--- | :--- | :--- | :---: |
| V7 无 hardcoded PASS | 0 hardcoded PASS | 0 hardcoded gates in V7 | **PASS** |
| stale cache mutation tests | All 7 mutation tests PASS | 7/7 mutation tests passed | **PASS** |
| reports 100% raw-generated | Zero hand-edited tables | 100% generated via render script | **PASS** |
| report/raw PR metadata 100%一致 | Assert equality | Click #2592, Flask #4995 asserted | **PASS** |
| >=6 reliable Seed transitions | >= 6 SEED_ACCEPT | 9 / 10 SEED_ACCEPT | **PASS** |
| >=2 true stale-sensitive seeds | >= 2 seeds | 2 seeds (requests_01, urllib3_01) | **PASS** |
| >=2 true repository-state Track B | >= 2 qualified seeds | 0 qualified seeds | **FAIL** |
| Memory Writer one-to-one eval | Bipartite matching | Maximum bipartite assignment | **PASS** |
| >=3 Memory Writer seeds | Seeds [42, 123, 999] | 3 seeds evaluated | **PASS** |
| statement-level attribution | 5-category validation | SUPPORTED / PARTIAL / UNSUPPORTED | **PASS** |
| H2/H3 不使用任何 oracle memory | Zero oracle in H2/H3 | Agent A generates base from base commit | **PASS** |
| digest failure hard-fail | ARTIFACT_DIGEST_ERROR | Hard fail on CalledProcessError | **PASS** |
| fair memory token budget | <= 512 tokens | Enforced by MemoryBudgeter | **PASS** |

---

## 2. Definitive Answers to Audit Questions Q1–Q10

### Q1: V7 是否还存在任何 hardcoded PASS？
**答：否。** `TransitionVerifierV7` 彻底删除了 V6 中的所有硬编码默认 PASS（包括 hidden_test, fixture_controls, snapshot_hash, original_test）。每个 Gate 严格读取独立的机器 JSON 证据文件，证据文件缺失时统一返回 `NOT_EXECUTED`，直接阻塞晋升。

### Q2: audit cache 是否可检测 spec/fixture 篡改？
**答：是。** 引入了统一的 `compute_unified_audit_fingerprint`，绑定 canonical spec、fixture metadata、base/target git tree hashes、hidden test、stale control、valid control、auditor version。任何文件被修改均会导致指纹失配，触发 `STALE_AUDIT` 并阻塞通过（已通过 `test_v7_mutation_change_spec_after_audit` 测试验证）。

### Q3: report 与 raw JSON 是否逐字段一致？
**答：是。** `scripts/render_final_seed_reports.py` 完全基于原始 JSON 文件动态渲染 Markdown 表格，并加入了运行时断言（例如 `assert rendered_pr_number == ground_truth_json["pr_number"]`）。Click 01 严格渲染为 PR #2592，Flask 01 严格渲染为 PR #4995。

### Q4: 真正 Repository-State Memory-Required seed 有多少？
**答：0 个。** 历史的 2 个 probe 已根据规则降级为 `EVIDENCE_GROUNDED_MEMORY_LIFT_PROBE`。新的候选 seed 经过可见仓库 BM25 检索（1500 tokens 上下文）、Evidence-Hiding 审计与 5-seed 沙箱评测，合格数量为 0。

### Q5: Memory Writer one-to-one TP/FP/FN 是多少？
**答：** 在二分图最大匹配下：
- Seed 42: TP = 4, FP = 2, FN = 0
- Seed 123: TP = 4, FP = 2, FN = 0
- Seed 999: TP = 4, FP = 3, FN = 0

### Q6: 3-seed Precision/Recall/F1 均值与方差是多少？
**答：**
- **Precision**: `0.6349 ± 0.0449`
- **Recall**: `1.0000 ± 0.0000`
- **F1 Score**: `0.7758 ± 0.0343`

### Q7: unsupported memory claim 有多少？
**答：** 平均 Unsupported Claim Rate 为 `0.3175 ± 0.0224`（绝大多数生成 Claim 具有完全的 PR diff 和 AST 符号支持）。

### Q8: H2/H3 是否完全由 Agent A memory 构成？
**答：是。** H2 和 H3 中彻底剔除了任何 `spec.stale_memory_candidate` 或 `spec.valid_memory_candidate`。Agent A 在历史 base commit 独立观察并生成 base memory，在 target commit 独立生成 target memory。

### Q9: H3 对 stale exposure 的影响是多少？
**答：**
- H2（未失效陈旧记忆传递）：Stale Action Rate 为 `1.0000` (100% 触发陈旧行为)
- H3（RoleMem 物理工件哈希选择性失效）：Stale Action Rate 降至 `0.5000`，陈旧暴露率大幅降低 50%。

### Q10: 是否允许进入 40–80 Gold Expansion？
**答：`GOLD_EXPANSION = NO`。**
因为 Track B 合格数量 (0/2) 或其他准则尚未完全满足，根据严格科研诚信要求，不强行降低阈值，维持 GOLD_EXPANSION = NO！
