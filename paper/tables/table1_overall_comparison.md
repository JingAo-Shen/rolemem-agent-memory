# Table 1: Overall Performance Comparison on RoleMem Benchmark ($N = 150$)

| Method | 3-Class Acc | Macro-F1 | Track A (Strict) Acc / F1 | Track B (Compat) Acc / F1 | FIR (False Inval) | SER (Stale Escape) | Avg Actions | Time / Case |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| Baseline-1: Majority | 83.3% | 30.3% | 83.3% / 45.5% | 84.0% / 45.6% | 0.0% | 100.0% | 0.0 | 0.0000s |
| Baseline-2: Static AST Checker | 72.7% | 31.0% | 72.7% / 46.4% | 73.3% / 46.7% | 14.4% | 91.7% | 1.0 | 0.0059s |
| Baseline-3: Naive RAG | 54.7% | 28.7% | 55.3% / 44.2% | 54.7% / 42.9% | 40.0% | 70.8% | 2.0 | 0.0039s |
| **RoleMem (Ours)** | 100.0% | 100.0% | 100.0% / 100.0% | 100.0% / 100.0% | 0.0% | 0.0% | 0.1 | 0.0226s |