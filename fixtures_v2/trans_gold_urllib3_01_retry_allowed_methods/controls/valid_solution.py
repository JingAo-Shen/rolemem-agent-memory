from urllib3.util.retry import Retry

def build_custom_retry(methods: list):
    # Valid pattern: allowed_methods
    return Retry(allowed_methods=methods)
