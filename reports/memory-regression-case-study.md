# Scientific Failure Analysis: Target-Memory Regression & Stale Insensitivity

## Executive Summary

In **Pilot-v1.4-r3 / r4**, negative and anomalous agent challenge outcomes were strictly retained rather than filtered out.
- **Total Scale Candidates Evaluated**: 6
- **Target-Memory Stale Regressions**: 2 / 6 (IniConfig, Uvicorn)
- **Stale Insensitive Cases**: 4 / 6 (More-Itertools, Rich FileProxy, CacheLib, Rich RenderGroup)

## Root Cause Classification Taxonomy

| Category | Definition | Primary Occurrence |
| :--- | :--- | :--- |
| **MODEL_OVERRELIANCE** | Model over-interprets verified target memory statement, inadvertently re-generating deprecated patterns or over-constraining imports | Uvicorn (#25) |
| **REPO_MEMORY_CONFLICT** | Memory statement specifies target behavior that conflicts with ambient retriever context in older module files | IniConfig (#20) |
| **TASK_UNDERCONSTRAINT** | Task prompt allows multiple valid implementations without forcing invocation of the transition symbol | More-Itertools (#15) |
| **STALE_INSENSITIVITY** | Base model naturally avoids legacy API without needing memory guidance | CacheLib (#24), Rich (#16) |

## Deep Case Studies

### Case 1: IniConfig (`trans_track_a_20_iniconfig_strip_inline_comments`)
- **Observed Behavior**: S0 Stale: 0/3 -> S2 Stale: 1/3 -> **S3 Stale: 3/3 (Regression)**
- **Root Cause**: `REPO_MEMORY_CONFLICT` + `MODEL_OVERRELIANCE`
- **Mechanism Analysis**: The target memory statement explained that `#` inline comments are no longer stripped by default. However, when presented with this memory, Qwen2.5-Coder-7B attempted to implement custom fallback comment-stripping logic that called legacy internal helper functions found in the retrieved repository context.
- **S3 Generation Snippet**:
```python
import iniconfig

def read_config_value(ini_data, section, key):
    config = iniconfig.IniConfig.parse(data=ini_data, strip_inline_comments=True)
    return config.get(section, key, fallback=None)

# Example usage:
ini_content = """
[section1]
key1=value1 # This is a comment
key2=value2

[section2]
```

### Case 2: Uvicorn (`trans_track_a_25_uvicorn_wsgi_middleware_deprecation`)
- **Observed Behavior**: S0 Stale: 0/3 -> S2 Stale: 0/3 -> **S3 Stale: 3/3 (Regression)**
- **Root Cause**: `MODEL_OVERRELIANCE` on deprecated symbol names in memory prompt
- **Mechanism Analysis**: The target memory stated: *'WSGIMiddleware in uvicorn.middleware.wsgi is deprecated in favor of a2wsgi'*. Because the prompt explicitly mentioned `uvicorn.middleware.wsgi.WSGIMiddleware`, the LLM attended strongly to the legacy module path and generated an import from `uvicorn.middleware.wsgi` instead of `a2wsgi`.
- **S3 Generation Snippet**:
```python
import warnings
from a2wsgi import WSGIMiddleware

def wrap_wsgi_application(app):
    """
    Wraps a WSGI application with a2wsgi.WSGIMiddleware to avoid unhandled deprecation warnings.
    
    Args:
    app (callable): The original WSGI application to be wrapped.
    
    Returns:
    callable: 
```

## Memory Trust Calibration (Ablation Finding)

When memory statements explicitly contrast deprecated vs replacement APIs, naive LLMs suffer from **lexical priming**, generating the deprecated token simply because it appears in the memory block.
### Recommendation for Memory Formatting:
1. **Negative Masking**: Strip deprecated symbol names from target memory injection blocks (provide only the replacement contract).
2. **Evidence Grounding**: Accompany target claims with concrete snippet examples rather than textual warnings.

