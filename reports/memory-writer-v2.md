# Pilot-v1.2d-r3 Memory Writer V2 Evaluation Report

**Evaluation Framework**: Bipartite One-to-One Matching & Statement-Level Attribution  
**Model**: `Qwen2.5-Coder-7B-Instruct`  
**Evaluation Seeds**: `[42, 123, 999]`  
**Evidence Source**: Automatically rendered from `runs/memory-writer-v2/multiseed_summary.json`

---

## 1. Executive Summary

In compliance with Pilot-v1.2d-r3 Section 9–12:
- **Bipartite One-to-One Matching**: Implemented maximum cardinality bipartite matching between generated claims and gold claims. No generated claim can match multiple gold claims, and no gold claim can be claimed twice.
- **Gold Claim Categorization**: Distinguishes `REQUIRED` vs `OPTIONAL_VALID` (e.g. `DEFAULT_METHOD_WHITELIST` and `DEFAULT_REDIRECT_HEADERS_BLACKLIST` in urllib3 PR #2000). Unmatched optional claims do not penalize recall (FN=0).
- **Statement-Level Attribution Validation**: Verifies artifact accuracy, symbol accuracy, change direction, replacement, and PR diff support across all statements (`SUPPORTED`, `PARTIAL`, `UNSUPPORTED`).
- **Multi-Seed Evaluation**: Runs independently across seeds [42, 123, 999], computing mean and standard deviation.

---

## 2. Multi-Seed Performance Matrix

| Seed | TP | FP | FN | Precision | Recall | F1 | Supported Attribution | Unsupported Rate | Claims / Task |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| Seed 42 | 4 | 2 | 0 | 0.6667 | 1.0000 | 0.8000 | 0.6667 | 0.3333 | 1.50 |
| Seed 123 | 4 | 2 | 0 | 0.6667 | 1.0000 | 0.8000 | 0.6667 | 0.3333 | 1.50 |
| Seed 999 | 4 | 3 | 0 | 0.5714 | 1.0000 | 0.7273 | 0.7143 | 0.2857 | 1.75 |

---

## 3. Aggregate Statistics (Mean ± Std)

- **Precision**: `0.6349 ± 0.0449`
- **Recall**: `1.0000 ± 0.0000`
- **F1 Score**: `0.7758 ± 0.0343`
- **Supported Attribution Accuracy**: `0.6825 ± 0.0224`
- **Unsupported Claim Rate**: `0.3175 ± 0.0224`
- **Claims Per Task**: `1.58 ± 0.12`

---

## 4. Key Findings & Attribution Diagnostics
1. **Zero False Negatives**: Across all 3 seeds, Recall is exactly 1.0000 on REQUIRED gold claims (`isolated_filesystem`, `get_connection`, `method_whitelist`, `invalidate_cached_property`).
2. **Attribution Reliability**: The majority of claims are fully supported by the underlying PR diffs and repository ASTs.
