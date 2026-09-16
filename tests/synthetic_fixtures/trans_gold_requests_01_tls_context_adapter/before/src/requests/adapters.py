class HTTPAdapter:
    def __init__(self):
        self.connections = {}
    def _get_connection(self, url, proxies=None):
        return f"Conn({url})"
    def send(self, request):
        conn = self._get_connection(request.url)
        return f"Response({conn})"
