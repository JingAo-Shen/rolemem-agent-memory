# Pilot-v1.2c Real Qwen2.5-Coder-7B End-to-End Evaluation Report

## Executive Summary

This report documents authentic, verified execution of `Qwen/Qwen2.5-Coder-7B-Instruct` on a dedicated GPU.
It validates the complete cycle under genuine Git repository state grounding:
`Task Specification -> Prompting -> 7B Generation -> AST Stale Analysis -> Secure Sandbox (bwrap) -> Pytest Telemetry`.

### Hardware & Model Provenance

| Specification | Value |
| :--- | :--- |
| **Model Repository** | `Qwen/Qwen2.5-Coder-7B-Instruct` |
| **Pinned Revision SHA** | `c03e6d358207e414f1eca0bb1891e29f1db0e242` |
| **Config SHA256** | `c0242402ad6a13b331ea320feea8c7e3776ffb7a4eff0757b9cd667e116d9a28` |
| **Tokenizer SHA256** | `c0382117ea329cdf097041132f6d735924b697924d6f6fc3945713e96ce87539` |
| **Safetensors Index SHA256** | `998a078123ffc97763690de7f2a677eb89168af5eaf8a5e12e6bc24d18e25bdb` |
| **Weights Prefix SHA256 (64MB)** | `7f7c6896a15384ae302b92df47d35acd22210f08c848f1116442492e20e94353` |
| **GPU Device** | `NVIDIA GeForce RTX 2080 Ti` |
| **Allocated VRAM** | `15.23 GB` (FP16 full precision) |
| **Sandbox Isolation** | Kernel namespace isolation via Bubblewrap (`bwrap` + `prlimit`) |

## Real 7B Inference Telemetry Results

| Transition ID | Track | Repo | Latency | Tokens | Sandbox Pytest | AST Stale Detected |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `trans_gold_werkzeug_01_cached_property` | A | `pallets/werkzeug` | 1.99s | 36 | FAIL | NO (Clean) |
| `trans_gold_click_01_option_parser` | A | `pallets/click` | 6.13s | 149 | FAIL | NO (Clean) |
| `trans_gold_flask_02_should_ignore_error` | B | `pallets/flask` | 6.7s | 162 | PASS | NO (Clean) |

### Details: `trans_gold_werkzeug_01_cached_property` (A)
- **Target File**: `def reset_cached_attribute(instance, att...`
- **Prompt Tokens**: `94` | **Completion Tokens**: `36`
- **Sandbox Passed**: `False`
- **AST Stale Detected**: `False`

```python
# Model Output Snippet
def reset_cached_attribute(instance, attr_name):
    if hasattr(instance, '_cache'):
        if attr_name in instance._cache:
            del instance._cache[attr_name]
```

```text
# Pytest Sandbox Execution Log
STDOUT:
============================= test session starts ==============================
platform linux -- Python 3.13.5, pytest-9.1.1, pluggy-1.6.0 -- /code/rolemem-agent-memory/.venvs/trans_gold_werkzeug_01_cached_property/bin/python
cachedir: .pytest_cache
rootdir: /tmp/rolemem_sandbox_h5dpfeza
collecting ... collected 1 item

test_hidden_verification.py::test_reset_cached_attribute FAILED          [100%]

=================================== FAILURES ===================================
______
```

### Details: `trans_gold_click_01_option_parser` (A)
- **Target File**: `from click import Context, Option, argum...`
- **Prompt Tokens**: `91` | **Completion Tokens**: `149`
- **Sandbox Passed**: `False`
- **AST Stale Detected**: `False`

```python
# Model Output Snippet
from click import Context, Option, argument, command, group, option

def parse_command_args(ctx, args):
    # Create a Click context
    ctx = Context(None)
    
    # Define options and arguments
    @group()
    @option('--verbose', is_flag=True, help='Enable verbose mode.')
    @argument('input_file', type=str, required=True)
    def cli(verbose, input_file):
        pass
    
    # Parse the arguments
    cli.main(args=args, prog_name='pallets/cli_helper.py')
    
    # Access parsed values

```

```text
# Pytest Sandbox Execution Log
STDOUT:
============================= test session starts ==============================
platform linux -- Python 3.13.5, pytest-9.1.1, pluggy-1.6.0 -- /code/rolemem-agent-memory/.venvs/trans_gold_click_01_option_parser/bin/python
cachedir: .pytest_cache
rootdir: /tmp/rolemem_sandbox_djpr2v4l
collecting ... collected 1 item

test_hidden_verification.py::test_parse_args FAILED                      [100%]

=================================== FAILURES ===================================
___________
```

### Details: `trans_gold_flask_02_should_ignore_error` (B)
- **Target File**: `from flask import Flask, request, jsonif...`
- **Prompt Tokens**: `91` | **Completion Tokens**: `162`
- **Sandbox Passed**: `True`
- **AST Stale Detected**: `False`

```python
# Model Output Snippet
from flask import Flask, request, jsonify

def configure_error_policy(app, exc_class):
    @app.teardown_request
    def handle_teardown(exception=None):
        if exception and isinstance(exception, exc_class):
            # Log or handle the exception as needed
            app.logger.error(f"Error occurred: {exception}")
            return jsonify({"error": "An error occurred"}), 500
        return None
```

```text
# Pytest Sandbox Execution Log
============================= test session starts ==============================
platform linux -- Python 3.13.5, pytest-9.1.1, pluggy-1.6.0 -- /code/rolemem-agent-memory/.venvs/trans_gold_flask_02_should_ignore_error/bin/python
cachedir: .pytest_cache
rootdir: /tmp/rolemem_sandbox_fz61tmy9
collecting ... collected 1 item

test_hidden_verification.py::test_error_policy PASSED                    [100%]

============================== 1 passed in 0.23s ===============================
```
