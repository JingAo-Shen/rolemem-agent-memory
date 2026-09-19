def create_header_property(key: str):
    # Valid: accesses environ dictionary directly
    return property(lambda self: self.environ.get(key, ""))
