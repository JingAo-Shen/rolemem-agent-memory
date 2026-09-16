def get_adapter_connection(adapter, request, verify=True):
    # Stale pattern: calls deprecated get_connection(url) (PR #6710)
    return adapter.get_connection(request.url)
