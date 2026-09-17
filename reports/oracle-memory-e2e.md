# Oracle-Memory True E2E Evaluation Report (Pilot-v1.2d-r1)

> **Status**: COMPLETED  
> **Model**: `Qwen/Qwen2.5-Coder-7B-Instruct` (Local PyTorch FP16, RTX 2080 Ti)  
> **Pipeline**: Oracle Memory Verification + Generation + Bubblewrap Sandbox Pytest  
> **Raw Telemetry**: `runs/true-rolemem-e2e/true_rolemem_e2e_summary.json`  
> **Timestamp**: 2026-09-17  

---

## 1. Experimental Protocol

The Oracle-Memory True E2E pipeline evaluates whether an agent provided with golden (oracle-extracted) repository memories can:
1. Trigger automatic artifact-level stale memory invalidation upon observing repository state transitions.
2. Invalidate obsolete memories via SHA256 artifact digest mismatch or explicit causal supersession.
3. Successfully generate code on the target repository state that passes hidden sandbox pytest execution without human intervention.

### Pipeline Flow:
$$\text{Oracle Memory Store} \xrightarrow{\text{Artifact Hash Check}} \text{RoleMem Invalidator} \xrightarrow{\text{Active Context}} \text{Qwen-7B Model} \xrightarrow{\text{Sandbox Pytest}} \text{TSR}$$

---

## 2. Quantitative Evaluation Results (4 Tasks)

| Task ID | Target File | Retrieved Memory Status | Generated AST Status | Sandbox Pytest | Latency (s) |
| :--- | :--- | :---: | :---: | :---: | :---: |
| `trans_gold_werkzeug_01_cached_property` | `property_helper.py` | Stale Invalidated; Valid Active | CLEAN | **PASS** | 4.82s |
| `trans_gold_flask_02_should_ignore_error` | `error_handler.py` | Stale Invalidated; Valid Active | CLEAN | **PASS** | 5.14s |
| `trans_gold_click_01_option_parser` | `custom_parser.py` | Stale Invalidated; Valid Active | CLEAN | **FAIL** | 7.32s |
| `trans_gold_urllib3_01_retry_allowed_methods` | `custom_retry.py` | Stale Invalidated; Valid Active | STALE USE | **FAIL** | 8.10s |

**Summary Metrics**:
- **Total Evaluated**: 4
- **Pytest Passed**: 2
- **Task Success Rate (TSR)**: **2 / 4 (50.0%)**
- **Artifact-Level Invalidation Accuracy**: **4 / 4 (100.0%)**
- **Stale Memory Denial Rate**: **4 / 4 (100.0%)** (Zero stale memories survived invalidation into prompt)

---

## 3. Detailed Task Case Studies

### 3.1 Passing Task: `trans_gold_werkzeug_01_cached_property`
- **Transition**: `werkzeug.utils.invalidate_cached_property` was deprecated in favor of standard Python `delattr(instance, prop)`.
- **RoleMem Invalidation**: Memory store contained both `mem_stale_1` (source commit `25ca9cd9`) and `mem_valid_1` (target commit `f50fbf56`). RoleMem detected digest change on `src/werkzeug/utils.py`, actively marking `mem_stale_1` as `INVALIDATED`.
- **Model Output**: The Qwen-7B model correctly generated `delattr(instance, attr_name)`.
- **Sandbox Result**: 1/1 passed pytest in 0.08s.

### 3.2 Passing Task: `trans_gold_flask_02_should_ignore_error`
- **Transition**: Handled exception ignore logic refactoring.
- **Sandbox Result**: 1/1 passed pytest in 0.11s.

### 3.3 Failing Task: `trans_gold_click_01_option_parser`
- **Root Cause**: The model correctly avoided deprecated parser methods, but hallucinated an extra constructor parameter in Click OptionParser that was rejected by Click's parser constructor.

### 3.4 Failing Task: `trans_gold_urllib3_01_retry_allowed_methods`
- **Root Cause**: Even though stale memory was denied, the base pre-training prior of Qwen-7B biased the model to generate `Retry(method_whitelist=methods)`. This was caught by our upgraded AST detector.

---

## 4. Methodological Distinction
This experiment relies on **Oracle Memory** (curated transition facts). It tests **retrieval, invalidation, and execution fidelity**, but does not test whether an AI agent can autonomously write high-quality memories from raw git diffs. That complementary capability is evaluated separately in `reports/agent-generated-handoff-e2e.md`.
