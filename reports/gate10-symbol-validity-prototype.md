# Gate 10 Report: Fine-Grained Symbol-Level Validity Prototype

**Gate Status**: `PASSED`  
**Date**: September 2026  
**Auditor**: RoleMem Hardening Suite  
**Prototype Implementation**: `src/symbol_digest_prototype.py`

---

## 1. Problem Statement: Over-Invalidation in Coarse File Hashing
In file-level SHA-256 validation, modifying a single line in a 500-line module invalidates all memory records bound to that file URI, even if the modifications pertain to completely unrelated helper functions. This induces a high **False Invalidation Rate (FIR)**:
$$\text{False Invalidation Rate (FIR)} = \frac{|\text{Actually Valid Memories Incorrectly Pruned}|}{|\text{Total Valid Memories in Scope}|}$$

---

## 2. Technical Formulation of Symbol-Level AST Digests
We developed a prototype in `src/symbol_digest_prototype.py` utilizing Python's `ast` parser:
1. **Canonical AST Extraction**: Top-level definitions (`FunctionDef`, `AsyncFunctionDef`, `ClassDef`, `Assign`) are converted into canonical AST strings with line-number and column-offset attributes stripped.
2. **Deterministic Cryptographic Digest**: A SHA-256 digest is generated per AST symbol node:
   $$h_{\text{sym}} = \text{SHA256}(\text{ast.dump}(\text{Node}, \text{include\_attributes}=\text{False}))$$
3. **Selective Fine-Grained Matching**: When file $F$ is refactored:
   - If symbol $S \in F$ has $h_{\text{sym}}^{\text{new}} == h_{\text{sym}}^{\text{recorded}}$, memory $m_S$ remains **`ACTIVE`**.
   - Only memories targeting modified or removed symbols are transitioned to **`INVALIDATED_BY_ARTIFACT`**.

---

## 3. Empirical Verification Evidence
Evaluated in `tests/test_gate10_symbol_digest.py`:
- Test scenario: `authenticate_user` (unmodified) and `format_report` (refactored) co-located in the same file.
- Results:
  - File-Level Hash: Falsely invalidates `authenticate_user` ($\text{FIR} = 100\%$).
  - Symbol-Level AST Hash: Correctly preserves `authenticate_user` ($\text{FIR} = 0.0\%$), while cleanly invalidating `format_report` ($\text{Stale Exposure Rate} = 0.0\%$).
- Verification Run:
  ```text
  tests/test_gate10_symbol_digest.py::test_symbol_digest_extraction PASSED [ 50%]
  tests/test_gate10_symbol_digest.py::test_unrelated_symbol_modification_preserves_validity PASSED [100%]
  ============================== 2 passed in 0.02s ===============================
  ```
*(Note: As specified, this prototype serves as algorithmic pre-research and remains decoupled from the main benchmark until full multi-language evaluation).*
