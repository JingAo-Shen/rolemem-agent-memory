# Memory Writer V3 Evaluation Report

## 1. Overview & Methodological Reform

In Pilot-v1.3, the evaluation of the Memory Writer (Qwen2.5-Coder-7B) has been overhauled to eliminate false positives and metric inflation:
1. **Required Recall Formulation**: Computed strictly as $\text{matched REQUIRED} / \text{total REQUIRED}$. Optional claims are excluded from recall denominator and numerator.
2. **Valid Prediction Precision**: Computed as $(\text{matched REQUIRED} + \text{matched OPTIONAL\_VALID}) / \text{all generated claims}$.
3. **Optional Valid Discovery Rate**: Separately reported as $\text{matched OPTIONAL\_VALID} / \text{total OPTIONAL\_VALID}$.
4. **Statement-Level Attribution**: Verified against actual `pr_diff` extracted from local Git mirrors.
5. **Strict Commit Binding**: Claims lacking explicit `evidence_commit` are marked `MISSING_COMMIT_ATTRIBUTION` rather than defaulting to target commit.
6. **Tightened SUPPORTED Status**: A replacement/deprecation claim requires `artifact_correct AND symbol_correct AND direction_correct AND replacement_correct AND statement_entails_diff`; otherwise it is downgraded to `PARTIAL`.

## 2. Multi-Seed Performance Metrics (Seeds: [42, 123, 999])

| Metric | Mean | Std | Seed 42 | Seed 123 | Seed 999 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Required Recall** | **1.0000** | 0.0000 | 1.0000 | 1.0000 | 1.0000 |
| **Valid Prediction Precision** | **0.6349** | 0.0449 | 0.6667 | 0.6667 | 0.5714 |
| **F1 Score** | **0.7758** | 0.0343 | 0.8000 | 0.8000 | 0.7273 |
| **Optional Valid Discovery Rate** | **0.0000** | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| **Supported Attribution Accuracy** | **1.0000** | 0.0000 | 1.0000 | 1.0000 | 1.0000 |
| **Unsupported Claim Rate** | **0.0000** | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| **Claims Per Task** | **1.58** | 0.12 | 1.50 | 1.50 | 1.75 |

## 3. Attribution Breakdown

Detailed counts of statement-level attribution across the evaluation:
- **SUPPORTED**: 6 (Seed 42), 6 (Seed 123), 7 (Seed 999)
- **PARTIAL**: 0 (Seed 42), 0 (Seed 123), 0 (Seed 999)
- **UNSUPPORTED**: 0 (Seed 42), 0 (Seed 123), 0 (Seed 999)
- **MISSING_COMMIT_ATTRIBUTION**: 0 across all seeds (claims were bound to real git target commit).
