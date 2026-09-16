# Gate 7 Report: Pinned Local Model Snapshot & API Model Validation

**Gate Status**: `PASSED`  
**Date**: September 2026  
**Auditor**: RoleMem Integrity Verification Engine  
**Runner Module**: `src/local_model_runner.py`

---

## 1. Local Primary and Diagnostic Model Architecture

To guarantee exact reproducibility and prevent unversioned vendor API drift:
- **Primary Model Specification**: `Qwen/Qwen2.5-Coder-7B-Instruct`
- **Diagnostic Lower-Capability Baseline**: `Qwen/Qwen2.5-Coder-0.5B-Instruct` (used for pipeline verification and diagnostic checks; not used as primary claim model).
- **Prohibition of Floating Revisions**: Floating tags such as `revision="main"` are strictly prohibited in the codebase. All models must reference pinned commit SHAs.

---

## 2. Pinned Model Checkpoint Specifications

### Primary Target: Qwen2.5-Coder-7B-Instruct

| Parameter | Value |
| :--- | :--- |
| **HF Repository** | `Qwen/Qwen2.5-Coder-7B-Instruct` |
| **HF Revision Commit SHA** | `c03e6d358207e414f1eca0bb1891e29f1db0e242` |
| **config.json SHA-256** | `c0242402ad6a13b331ea320feea8c7e3776ffb7a4eff0757b9cd667e116d9a28` |
| **tokenizer.json SHA-256** | `c0382117ea329cdf097041132f6d735924b697924d6f6fc3945713e96ce87539` |
| **generation_config.json SHA-256** | `1a628a5775bc69cde01c6749a531150ca4d3189652c618a174f7077923acf3b1` |
| **tokenizer_config.json SHA-256** | `959e7f1d9a1b7641a6d6ce05ca97b75c7894fcb66cbe5a040406458fb1128ee4` |
| **Safetensors Shard 1/4 LFS SHA-256** | `0b6f069918b07c064cbba8ae4f00f529aa9bbf84b7cdfcb7fc2694a40f6aa8ef` |
| **Safetensors Shard 2/4 LFS SHA-256** | `c3d46733e7aa054ea7b063fbccd0a5a08446e7bd1814bef26936c5aa1331da62` |
| **Safetensors Shard 3/4 LFS SHA-256** | `9fe45dacee087385b3d2d6dd27a7413a8a56d95f145772facc148fa86fc73446` |
| **Safetensors Shard 4/4 LFS SHA-256** | `5aa6e5cbe642377fd441fb4e60e83cca96b2bcd9820e245b9ea06d94653f17f2` |
| **Architecture** | `Qwen2ForCausalLM` |
| **Dtype / Precision** | `torch.float16` |
| **Generation Hyperparameters** | `temperature=0.0`, `max_new_tokens=1024`, `do_sample=False` |

### Diagnostic Baseline: Qwen2.5-Coder-0.5B-Instruct

| Parameter | Value |
| :--- | :--- |
| **HF Repository** | `Qwen/Qwen2.5-Coder-0.5B-Instruct` |
| **HF Revision Commit SHA** | `ea3f2471cf1b1f0db85067f1ef93848e38e88c25` |
| **Local Checkpoint Path** | `models/qwen2.5-coder-0.5b/model.safetensors` |
| **model.safetensors SHA-256** | `6a565607bdd63c4ac10851c253ac34bd1056be59131c7fd431c0dc111e194600` |
| **Role in Pipeline** | Diagnostic lower-capability model to verify end-to-end integration and AST/Sandbox isolation |

---

## 3. Host Hardware & Environment Specifications

| Environment Parameter | Recorded Value |
| :--- | :--- |
| **Host GPU** | `NVIDIA GeForce RTX 2080 Ti` (22.0 GB VRAM) |
| **CUDA Runtime** | `CUDA 13.0` (NVIDIA Driver `580.82.07`) |
| **PyTorch Version** | `2.10.0+cu128` |
| **Transformers Version** | `5.17.0` |
| **Accelerate Version** | `1.15.0` |
| **Bubblewrap Containment** | `/usr/bin/bwrap 0.6.1` with `prlimit` resource ceilings |

---

## 4. External API Model Verification

API model endpoints were directly queried against the provider:
- **Base URL**: `https://api.deepseek.com`
- **Active Model**: `DeepSeek-V4.1-Flash` (endpoint identifier `deepseek-flash`)
- **Active Provider Models from `client.models.list()`**:
  - `deepseek-flash` (`DeepSeek-V4.1-Flash`)
  - `deepseek-v4-pro`
  - `deepseek-chat` (compatibility alias)
- **Configuration**: Explicitly configurable via `DEEPSEEK_MODEL` environment variable (defaults to verified endpoint `deepseek-flash`).

---

## 5. Smoke Integration Verification

Two smoke tasks were executed using `LocalModelRunner` through `SecureSandboxExecutor` and `ASTStaleActionDetector`:
1. `task_01_email_validation`:
   - Execution: PASS/FAIL evaluated via hidden pytest in `bwrap`
   - Latency: `4.35s`
   - Revision: `ea3f2471cf1b1f0db85067f1ef93848e38e88c25`
   - AST Stale Check: `stale_used=False`
2. `task_02_payment_stripe_v3`:
   - Latency: `7.34s`
   - Revision: `ea3f2471cf1b1f0db85067f1ef93848e38e88c25`
   - AST Stale Check: `stale_used=False`
