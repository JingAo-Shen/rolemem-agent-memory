# Independent Memory Validity Scientific Evaluation Report V3

## Executive Summary

- **Benchmark Size**: 60 empirical cases across 16 distinct repositories
- **Ground Truth Balance**: 30 Valid (50.0%) vs 30 Stale (50.0%)
- **Evaluation Goal**: Rigorously test False Invalidation Rate (FIR) vs Stale Exposure Rate (SER) across 4 orthogonal categories.

## Four Category Benchmark Taxonomy

| Category | Description | Challenge Addressed | Cases |
| :--- | :--- | :--- | :---: |
| **Cat A** | File Changed / Symbol Same / Valid | File-level False Invalidation | 20 |
| **Cat B** | Symbol Changed / Memory Valid | AST Hash Over-sensitivity | 10 |
| **Cat C** | Symbol Same / Memory Stale | Upstream / Protocol Stale Escape | 10 |
| **Cat D** | Symbol Modified or Removed / Stale | True Stale Invalidation | 20 |

## Comparative Evaluation Results

| Mechanism | Accuracy | Precision | Recall | F1 Score | False Inval. Rate (FIR) | Stale Exposure (SER) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **File Level Baseline** | 33.3% | 40.0% | 66.7% | 50.0% | **100.0%** | **33.3%** |
| **Pure Symbol AST Baseline** | 66.7% | 66.7% | 66.7% | 66.7% | **33.3%** | **33.3%** |
| **RoleMem Hybrid Validity** | 100.0% | 100.0% | 100.0% | 100.0% | **0.0%** | **0.0%** |

## Category-by-Category Accuracy Breakdown

| Mechanism | Cat A (File Chg/Sym Same) | Cat B (Sym Refactor/Valid) | Cat C (Upstream Break/Stale) | Cat D (Sym Stale/Rem) |
| :--- | :---: | :---: | :---: | :---: |
| **File Level Baseline** | 0.0% | 0.0% | 0.0% | 100.0% |
| **Pure Symbol AST Baseline** | 100.0% | 0.0% | 0.0% | 100.0% |
| **RoleMem Hybrid Validity** | 100.0% | 100.0% | 100.0% | 100.0% |

## Scientific Findings

1. **File-Level Invalidation Flaw**: Naive file-level invalidation suffers from a **100% False Invalidation Rate (FIR)** on Cat A and Cat B, discarding all valid memories whenever irrelevant lines in the same file change.
2. **Pure AST Over-Sensitivity**: Pure AST hash equality fails on Cat B (100% false invalidation under internal refactorings) and Cat C (100% stale escape when external dependencies change without local AST modifications).
3. **RoleMem Hybrid Superiority**: RoleMem's multi-granularity hybrid tracking achieves optimal precision and recall by isolating symbol-level stability while verifying semantic dependency entailment.

