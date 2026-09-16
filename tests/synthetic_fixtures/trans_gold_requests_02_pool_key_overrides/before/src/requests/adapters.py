class HTTPAdapter:
    def __init__(self, pool_connections=10, pool_maxsize=10):
        self._pool_connections = pool_connections
        self._pool_maxsize = pool_maxsize
        self.poolmanager = None
        self.init_poolmanager(pool_connections, pool_maxsize)
    def init_poolmanager(self, connections, maxsize, **kwargs):
        # Regressed in #6655: ignored kwargs
        self.poolmanager = {"connections": connections, "maxsize": maxsize}
