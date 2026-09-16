class Flask:
    def __init__(self, name):
        self.name = name
        self.ignored_errors = set()
    def should_ignore_error(self, error):
        return type(error) in self.ignored_errors
    def handle_exception(self, e):
        if self.should_ignore_error(e):
            return "IGNORED"
        raise e
