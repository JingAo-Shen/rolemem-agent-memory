def get_pool_key_attributes(adapter, request, verify=True):
    # Stale pattern: does not use build_connection_pool_key_attributes (PR #6716)
    return {"url": request.url, "verify": verify}
