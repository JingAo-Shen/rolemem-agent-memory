class OptionParser:
    def __init__(self):
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
