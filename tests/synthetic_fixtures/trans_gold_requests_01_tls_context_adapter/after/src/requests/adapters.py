import warnings

class HTTPAdapter:
    def __init__(self):
        self.connections = {}
    def _get_connection(self, url, proxies=None):
        warnings.warn(
            "'_get_connection' is deprecated in requests 2.32.0 (PR #6710). Use 'get_connection_with_tls_context' instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return f"Conn({url})"
    def get_connection_with_tls_context(self, request, verify=True, cert=None):
        return f"ConnTLS({request.url}, verify={verify})"
    def send(self, request, verify=True, cert=None):
        conn = self.get_connection_with_tls_context(request, verify=verify, cert=cert)
        return f"Response({conn})"
