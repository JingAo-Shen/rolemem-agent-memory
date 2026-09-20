# Legacy Results and Pilot Status Declaration

## Status of Protocol V1 and Protocol V2 Results

### 1. Protocol V1 Pilot Results
- **Status**: `PILOT_EXPLORATORY_ARCHIVED`
- **Scope**: Historical pilots (v1.1 - v1.4-r4).
- **Usage**: Retained strictly for immutable provenance and developmental record. Not valid for formal claims.

### 2. Protocol V2 RoleMem Hybrid Results
- **Status**: `DEVELOPMENT_ONLY`
- **Scope**: `scripts/evaluate_symbol_validity_protocol_v2.py`
- **Reason**:
  The exploratory evaluator contained development-time keyword matching heuristics (e.g. `mapping`, `unicodefun`, `getheaders`, `pydantic`). Therefore, those results cannot serve as an unseen formal benchmark test.
- **Usage**: Protocol V2 data and scripts are preserved immutably for historical reproducibility.

### 3. Protocol V2.1 Formal Engine
- **Status**: `PRODUCTION_ENGINE_ACTIVE`
- **Scope**: `src/validity/` and `scripts/*_v2_1.py`
- **Guarantees**:
  - Zero benchmark-specific rules or symbol literals in algorithmic decision paths.
  - Strict two-phase separation: prediction on blinded inputs without access to gold labels or metadata.
  - De-leaked blind IDs (`MV21-XXXXXX`).
  - True static AST dependency analysis and machine-executed counterfactual execution.
