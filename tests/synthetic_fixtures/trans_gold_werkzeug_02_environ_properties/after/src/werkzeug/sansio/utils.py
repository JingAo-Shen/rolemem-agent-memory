# Modern sansio utils (post PR #3276)
import warnings

class environ_property:
    def __init__(self, name, default=None):
        warnings.warn(
            "'environ_property' is deprecated and will be removed in Werkzeug 3.2. Access environ directly.",
            DeprecationWarning,
            stacklevel=2
        )
        self.name = name
        self.default = default
    def __get__(self, obj, type=None):
        return obj.environ.get(self.name, self.default)
