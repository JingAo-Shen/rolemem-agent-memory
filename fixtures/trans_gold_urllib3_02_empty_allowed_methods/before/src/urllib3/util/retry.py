class Retry:
    def __init__(self, allowed_methods=None):
        if allowed_methods is not None and len(allowed_methods) == 0:
            self.allowed_methods = False  # Retry all verbs
        else:
            self.allowed_methods = allowed_methods
