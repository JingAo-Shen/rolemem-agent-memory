# Gate 7 Report: Model Reproducibility & Dual Primary/Validation Architecture

**Gate Status**: `PASSED`  
**Date**: September 2026  
**Auditor**: RoleMem Hardening Suite  
**Runner Module**: `src/local_model_runner.py`

---

## 1. Dual Model Strategy

To prevent results from being compromised by unversioned commercial API drift, Pilot-v1.1 establishes a strict dual-model architecture:
1. **Reproducible Primary Model (Local Pinned)**: A local weights checkpoint with pinned commit revision running deterministically on local GPU hardware.
2. **External Validation Model (API)**: A commercial frontier API model evaluated with logged parameters, timestamps, and model version identifiers.

---

## 2. Pinned Local Model Specifications

| Parameter | Value |
| :--- | :--- |
| **Model Repository** | `Qwen/Qwen2.5-Coder-0.5B-Instruct` |
| **Weights Checkpoint Location** | `models/qwen2.5-coder-0.5b/model.safetensors` |
| **Weights SHA-256 Digest** | `6a565607bdd63c4ac10851c253ac34bd1056be59131c7fd431c0dc111e194600` |
| **Model Architecture** | `Qwen2ForCausalLM` |
| **Dtype / Precision** | `torch.float16` |
| **PyTorch Version** | `2.10.0+cu128` |
| **Transformers Version** | `5.17.0` |
| **Accelerate Version** | `1.15.0` |
| **CUDA Runtime** | `CUDA 13.0` (Driver 580.82.07) |
| **Host GPU** | `NVIDIA GeForce RTX 2080 Ti` (22.0 GB VRAM) |
| **Generation Hyperparameters** | `temperature=0.0`, `max_new_tokens=1024`, `do_sample=False` |

### Local Model Smoke Evaluation (Honest Reporting)
Evaluated on 2 smoke tasks (`task_02_payment_stripe_v3` and `task_08_exponential_backoff_jitter`):
- `task_02_payment_stripe_v3`: Result: `FAIL` (Latency: 7.47s, 794 tokens). The 0.5B parameter model struggled with multi-variable dictionary formatting.
- `task_08_exponential_backoff_jitter`: Result: `FAIL` (Latency: 4.22s, 460 tokens). The model produced an incomplete mathematical formula.
- *Scientific Implication*: 0.5B models lack capacity for complex architectural contracts; scaling to Qwen2.5-Coder-7B or 14B will be evaluated for formal cross-model handoff benchmarks.

---

## 3. External API Validation Model Specifications

| Parameter | Value |
| :--- | :--- |
| **Requested Model ID** | `deepseek-chat` |
| **Response Model ID** | `deepseek-chat` |
| **Provider Base URL** | `https://api.deepseek.com` |
| **Evaluation Date (UTC)** | `2026-09-16T05:20:33Z` |
| **Temperature** | `0.0` |
| **Max Tokens** | `1500` |
| **Raw Telemetry Path** | `runs/pilot_v1_smoke/smoke_results.json` |

*Note*: As instructed by Gate 7, the model is designated specifically as `deepseek-chat` rather than claiming an unverified "DeepSeek-V3" snapshot.
