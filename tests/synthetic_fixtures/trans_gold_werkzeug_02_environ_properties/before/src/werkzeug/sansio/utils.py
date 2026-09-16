# Legacy sansio utils
class environ_property:
    def __init__(self, name, default=None):
        self.name = name
        self.default = default
    def __get__(self, obj, type=None):
        if obj is None:
            return self
        return obj.environ.get(self.name, self.default)
