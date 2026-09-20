# Human Annotation Package & Author Audit Report

> [!IMPORTANT]
> **Methodological Clarification**: This audit was conducted by a single core author and is documented strictly as `AUTHOR_AUDIT`. It does NOT claim independent third-party multi-annotator validation or inter-annotator Cohen's kappa agreement.

## 1. Audit Overview
- **Sample Size**: 30 randomly sampled blinded cases across all 4 categories
- **Concordance with Gold Ground Truth**: 30/30 (100.0%)
- **Annotation Artifacts**:
  - `data/memory_validity_v2/human_annotation_package.jsonl` (Unlabeled inputs with prompt, source context, diff hunks)
  - `data/memory_validity_v2/human_annotation_template.csv` (Blank CSV template for external third-party annotators)
  - `data/memory_validity_v2/author_audit.jsonl` (Author-annotated verification records)

## 2. Category Concordance Summary

| Category | Cases Audited | Concordance | Agreement Rate |
| :--- | :--- | :--- | :--- |
| **CAT_A_FILE_CHG_SYM_SAME_VALID** | 13 | 13/13 | 100.0% |
| **CAT_B_SYM_CHG_MEMORY_VALID** | 3 | 3/3 | 100.0% |
| **CAT_C_SYM_SAME_MEMORY_STALE** | 2 | 2/2 | 100.0% |
| **CAT_D_SYM_CHG_OR_REM_STALE** | 12 | 12/12 | 100.0% |

## 3. Guidelines for Future External Annotation
External multi-annotator studies must use `data/memory_validity_v2/human_annotation_template.csv` with $\ge 2$ independent annotators blinded to mechanism predictions and gold labels, followed by Fleiss' kappa / Cohen's kappa verification.
