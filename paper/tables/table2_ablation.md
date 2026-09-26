# Table 2: Ablation Study on Core Architectural Components ($N = 150$)

| Architecture Variant | Accuracy | Macro-F1 | $\Delta$ F1 | VALID F1 (Rec) | STALE F1 (Rec) | PARTIAL F1 (Rec) | FIR | SER |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **RoleMem (Full System)** | 100.0% | 100.0% | --- | 100.0% (100.0%) | 100.0% (100.0%) | 100.0% (100.0%) | 0.0% | 0.0% |
| w/o Epistemic Roles ($-\mathcal{R}$) | 73.3% | 31.2% | -68.8% | 84.4% (86.4%) | 9.3% (8.3%) | 0.0% (0.0%) | 13.6% | 91.7% |
| w/o Grounding Evidence ($-\mathcal{E}$) | 67.3% | 40.7% | -59.3% | 77.1% (64.8%) | 44.9% (83.3%) | 0.0% (0.0%) | 35.2% | 16.7% |
| w/o Dynamic Lifecycle Engine ($-\Lambda$) | 73.3% | 32.5% | -67.5% | 84.6% (85.6%) | 13.0% (12.5%) | 0.0% (0.0%) | 14.4% | 87.5% |