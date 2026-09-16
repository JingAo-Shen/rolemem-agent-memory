import warnings

class OptionParser:
    def __init__(self):
        warnings.warn(
            "'click.parser.OptionParser' is deprecated and will be removed in Click 9.0. Use modern Command parsing.",
            DeprecationWarning,
            stacklevel=2
        )
        self._options = {}
    def add_option(self, opts, dest):
        for o in opts:
            self._options[o] = dest
    def parse_args(self, args):
        res = {}
        i = 0
        while i < len(args):
            if args[i] in self._options:
                res[self._options[args[i]]] = args[i+1]
                i += 2
            else:
                i += 1
        return res
