from urllib3.util.retry import Retry

def create_all_verbs_retry():
    # Stale pattern: empty collection allowed_methods=[] emits warning (PR #5223)
    return Retry(allowed_methods=[])
