from urllib3.util.retry import Retry

def build_custom_retry(methods: list):
    # Stale pattern: method_whitelist is deprecated in favor of allowed_methods (PR #2000)
    return Retry(method_whitelist=methods)
