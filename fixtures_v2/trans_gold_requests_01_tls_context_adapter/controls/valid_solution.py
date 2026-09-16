def get_adapter_connection(adapter, request, verify=True):
    # Valid pattern: calls get_connection_with_tls_context(request, verify=verify)
    return adapter.get_connection_with_tls_context(request, verify=verify)
