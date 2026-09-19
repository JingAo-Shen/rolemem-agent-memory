# Pilot-v1.3-r1 — Memory Writer V4 Multi-Seed Evaluation Report

## 1. Executive Summary

Memory Writer Evaluator V4 introduces strict Symbol Normalization (handling fully qualified vs unqualified symbols), Structural Attribution Consistency (verifying exact git commit and diff hunk presence), and a Semantic Entailment Judge (direction and replacement validation).

## 2. Multi-Seed Aggregate Performance

- **Seeds Evaluated**: `[42, 123, 999]`
- **Tasks Evaluated**: `4` (trans_gold_click_02_isolated_filesystem, trans_gold_requests_01_tls_context_adapter, trans_gold_urllib3_01_retry_allowed_methods, trans_gold_werkzeug_01_cached_property)

| Metric | Mean ± Std | Seed 42 | Seed 123 | Seed 999 |
| :--- | :---: | :---: | :---: | :---: |
| **Required Recall** | 1.0000 ± 0.0000 | 1.0000 | 1.0000 | 1.0000 |
| **Valid Prediction Precision** | 0.9524 ± 0.0673 | 1.0000 | 1.0000 | 0.8571 |
| **F1 Score** | 0.9744 ± 0.0363 | 1.0000 | 1.0000 | 0.9231 |
| **Optional Valid Discovery Rate** | 1.0000 ± 0.0000 | 1.0000 | 1.0000 | 1.0000 |
| **Supported Attribution Accuracy** | 1.0000 ± 0.0000 | 1.0000 | 1.0000 | 1.0000 |
| **Unsupported Claim Rate** | 0.0000 ± 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| **Average Claims per Task** | 1.5833 ± 0.1179 | 1.5000 | 1.5000 | 1.7500 |

## 3. Key Methodological Improvements in V4
1. **Symbol Normalization**: Canonical resolution for symbols (e.g. `click.testing.isolated_filesystem` and `isolated_filesystem` match symmetrically).
2. **Structural Attribution**: Explicit git diff inspection ensures claims cannot cite non-existent files or phantom commits.
3. **Semantic Entailment**: Statements are verified to entail the change direction (deprecation, replacement) rather than simply regurgitating tokens.
4. **Zero Fallback Toleration**: Missing commit fields or ungrounded assertions are flagged as `MISSING_COMMIT_ATTRIBUTION` or `UNSUPPORTED`.
