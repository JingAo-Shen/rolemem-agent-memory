import werkzeug.utils

def create_header_property(key: str):
    # Stale: imported from werkzeug.utils
    return werkzeug.utils.environ_property(key)
