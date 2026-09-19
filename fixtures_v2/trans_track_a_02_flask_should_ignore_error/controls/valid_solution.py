from flask import Flask

class CustomApp(Flask):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        @self.teardown_request
        def handle_teardown(exc):
            pass
