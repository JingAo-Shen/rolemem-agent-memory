# Table 4: Robustness & Stress-Testing Benchmark Performance ($N = 30$)

| Challenge Category | Cases | Majority Acc / F1 | Static AST Acc / F1 | Naive RAG Acc / F1 | RoleMem (Ours) Acc / F1 |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Evidence Missing ($N=10$)** | 10 | 50.0% / 33.3% | 50.0% / 33.3% | 50.0% / 33.3% | **50.0% / 33.3%** |
| **Ambiguous Evolution ($N=10$)** | 10 | 40.0% / 19.1% | 50.0% / 34.8% | 50.0% / 31.6% | **70.0% / 47.9%** |
| **Conflicting Evidence ($N=10$)** | 10 | 100.0% / 100.0% | 20.0% / 33.3% | 20.0% / 33.3% | **20.0% / 33.3%** |
| **Overall Robustness Suite** | **30** | **63.3% / 25.9%** | **40.0% / 26.4%** | **40.0% / 25.4%** | ****46.7% / 30.1%**** |