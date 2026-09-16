from urllib3.util.retry import Retry

def create_all_verbs_retry():
    # Valid pattern: allowed_methods=None
    return Retry(allowed_methods=None)
