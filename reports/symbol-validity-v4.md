# Symbol Validity Scientific Evaluation Report V4 (Blind Gold)

## Executive Summary

- **Total Adjudicated Cases**: 75 (60 benchmark cases + 15 adversarial stress-test cases)
- **Ground Truth Balance**: 60 VALID (80.0%) vs 15 STALE (20.0%)
- **Evaluation Basis**: Strictly evaluated against double-blind annotated and adjudicated consensus labels.

## Comparative Benchmark Performance

| Mechanism | Coverage | Accuracy | Precision | Recall | F1 | False Inval. Rate (FIR) | Stale Exposure (SER) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **File Level Baseline** | 100.0% | 33.3% | 23.1% | 100.0% | 37.5% | **83.3%** | **0.0%** |
| **Pure Symbol AST Baseline** | 100.0% | 60.0% | 32.6% | 93.3% | 48.3% | **48.3%** | **6.7%** |
| **RoleMem Hybrid No Abstain** | 100.0% | 97.3% | 93.3% | 93.3% | 93.3% | **1.7%** | **6.7%** |
| **RoleMem Hybrid With Abstain** | 96.0% | 100.0% | 100.0% | 100.0% | 100.0% | **0.0%** | **0.0%** |

## Selective Abstention Analysis (Research Insight)

- **RoleMem Hybrid (No Abstain)**: Coverage: 100.0%, Accuracy: 97.3%, FIR: 1.7%, SER: 6.7%.
- **RoleMem Hybrid (With Selective Abstention)**: Coverage: 96.0%, Accuracy: 100.0%, FIR: 0.0%, SER: 0.0%.
- **Key Finding**: In safety-critical software evolution, selectively abstaining on ambiguous protocol/subclass transitions achieves **0.0% False Invalidation** and **0.0% Stale Exposure** on decided queries at {m_ab['Coverage']*100:.1f}% coverage.

