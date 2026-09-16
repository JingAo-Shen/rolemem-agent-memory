class HTTPAdapter:
    def __init__(self, pool_connections=10, pool_maxsize=10, **kwargs):
        self._pool_connections = pool_connections
        self._pool_maxsize = pool_maxsize
        self.poolmanager = None
        self.init_poolmanager(pool_connections, pool_maxsize, **kwargs)
    def init_poolmanager(self, connections, maxsize, **kwargs):
        # Resolved in #6716: properly incorporates pool key kwargs
        self.poolmanager = {"connections": connections, "maxsize": maxsize, **kwargs}
