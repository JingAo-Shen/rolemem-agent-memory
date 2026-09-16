def get_pool_key_attributes(adapter, request, verify=True):
    # Valid pattern: uses build_connection_pool_key_attributes
    return adapter.build_connection_pool_key_attributes(request, verify=verify)
